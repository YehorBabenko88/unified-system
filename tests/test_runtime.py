import tempfile
import unittest
from pathlib import Path

from unified_system.runtime import ModuleSpec, RuntimeSupervisor


CORE = ('unified-system','grid','math','strattester','meta_analyse','terminan')


class Driver:
    def __init__(self):
        self.running = {}; self.calls = []; self.unready = set(); self.crashed = set()
    def start(self, spec, release_id, operation_id):
        self.calls.append(('start',spec.module_id))
        self.running.setdefault(operation_id,spec.module_id)
        return operation_id
    def stop(self, handle):
        self.calls.append(('stop',self.running.get(handle)))
        self.running.pop(handle,None)
    def alive(self, handle):
        return handle in self.running and self.running[handle] not in self.crashed
    def ready(self, spec, handle, release_id):
        return dict(module_id=spec.module_id,version=spec.version,release_id=release_id,
                    ready=self.alive(handle) and spec.module_id not in self.unready)


def specs():
    return [ModuleSpec(name,'1.0.0',dependencies=('math',) if name=='strattester' else ()) for name in CORE]


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'runtime.db';self.driver=Driver();self.now=100.
    def runtime(self, **kw):
        return RuntimeSupervisor(self.path,self.driver,specs(),release_id='candidate-1',
                                 release_sha256='a'*64,node_id='cloud-test',clock=lambda:self.now,**kw)
    def test_six_real_driver_states_and_dependency_order(self):
        r=self.runtime();r.start();r.tick()
        self.assertTrue(r.health_release('candidate-1')['ready'])
        order=[name for op,name in self.driver.calls if op=='start']
        self.assertLess(order.index('math'),order.index('strattester'))
        self.assertEqual(len(self.driver.running),6)
        r.start();r.tick();self.assertEqual(len(self.driver.running),6)
        self.assertEqual(r.snapshot()['schema'],'unified.runtime.v2')
        self.assertFalse(r.snapshot()['physical_deployment_allowed'])
    def test_port_or_pid_without_functional_identity_never_ready(self):
        self.driver.unready.add('math');r=self.runtime();r.start();r.tick()
        self.assertFalse(r.health_release('candidate-1')['ready'])
        self.assertNotIn(('start','strattester'),self.driver.calls)
        self.assertEqual(r.snapshot()['modules']['math']['state'],'STARTING')
    def test_admin_stop_survives_recreation_and_start_requires_explicit_resume(self):
        r=self.runtime();r.start();r.tick();r.stop()
        again=self.runtime();again.start();again.tick()
        self.assertEqual(self.driver.running,{})
        again.resume();again.tick();self.assertEqual(len(self.driver.running),6)
    def test_crash_recovery_backoff_and_stale_dependents(self):
        r=self.runtime();r.start();r.tick();self.driver.crashed.add('math');r.tick()
        self.assertFalse(r.health_release('candidate-1')['ready'])
        self.assertNotEqual(r.snapshot()['modules']['strattester']['state'],'READY')
        self.driver.crashed.clear();self.now+=10;r.tick();r.tick()
        self.assertTrue(r.health_release('candidate-1')['ready'])
    def test_stop_reverse_dependencies_and_hot_extension_without_global_restart(self):
        r=self.runtime();r.start();r.tick();before=len(self.driver.calls)
        r.register(ModuleSpec('research-extra','1.0.0',dependencies=('math',)))
        r.start_module('research-extra');r.tick()
        self.assertEqual(self.driver.calls[before:],[('start','research-extra')])
        with self.assertRaises(ValueError):r.unregister('math')
        with self.assertRaises(ValueError):r.stop_module('math')
        r.stop_module('research-extra');r.unregister('research-extra')
        r.stop();stops=[n for op,n in self.driver.calls if op=='stop']
        self.assertLess(stops.index('strattester'),stops.index('math'))
    def test_bad_versions_cycles_and_missing_dependencies_before_side_effects(self):
        for bad in (ModuleSpec('bad','1.0.0',dependencies=('missing',)),
                    ModuleSpec('bad','1.0.0',api_major=True),ModuleSpec('bad','invalid')):
            with self.assertRaises(ValueError):self.runtime().register(bad)
        self.assertEqual(self.driver.calls,[])
    def test_wrong_release_and_driver_errors_never_leak_private_values(self):
        r=self.runtime();r.start();r.tick()
        self.assertFalse(r.health_release('other')['ready'])
        self.driver.ready=lambda *a: (_ for _ in ()).throw(RuntimeError('PRIVATE_SECRET'))
        r.tick();self.assertNotIn('PRIVATE_SECRET',str(r.snapshot()))


if __name__=='__main__':unittest.main()

class RuntimeConcurrencyTests(RuntimeTests):
    def test_two_supervisors_do_not_interleave_external_effects(self):
        import threading
        first=self.runtime();second=self.runtime();first.start()
        entered=threading.Event();release=threading.Event();seen=[];errors=[]
        original=self.driver.start
        def slow(*args):
            if not entered.is_set():entered.set();release.wait(3)
            return original(*args)
        self.driver.start=slow
        def run(fn):
            try:fn()
            except Exception as exc:errors.append(exc)
        a=threading.Thread(target=lambda:run(first.tick));a.start()
        self.assertTrue(entered.wait(1))
        b=threading.Thread(target=lambda:run(lambda:seen.append(second.snapshot())));b.start()
        b.join(.1)
        try:self.assertTrue(b.is_alive(),'second supervisor observed an in-flight process side effect')
        finally:release.set();a.join(4);b.join(4)
        self.assertFalse(errors);self.assertTrue(seen[0]['ready'])
        self.assertEqual(len(self.driver.running),6)
    def test_failed_stop_is_quarantined_until_explicit_cleanup(self):
        r=self.runtime();r.start();r.tick()
        self.driver.ready=lambda *args: (_ for _ in ()).throw(RuntimeError('lost health'))
        original=self.driver.stop
        self.driver.stop=lambda *args: (_ for _ in ()).throw(RuntimeError('cannot stop'))
        r.tick()
        self.driver.ready=lambda spec,handle,release_id:dict(module_id=spec.module_id,version=spec.version,release_id=release_id,ready=True)
        r.tick()
        self.assertFalse(r.snapshot()['ready'])
        with self.assertRaises(ValueError):r.resume()
        self.driver.stop=original;r.stop();r.resume();r.tick()
        self.assertTrue(r.snapshot()['ready'])
