import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock

from unified_system.module_catalog import MODULE_IDS
from unified_system.runtime import ModuleSpec, RuntimeSupervisor
from unified_system.runtime_cli import SnapshotView, status_server, write_snapshot
from unified_system.runtime_builtin import BuiltinRuntimeDriver,PUBLICATION_MAX_AGE


class BuiltinTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.view=SnapshotView()
        self.server=status_server(self.view,port=0)
        self.thread=threading.Thread(target=self.server.serve_forever);self.thread.start()
        self.addCleanup(self.close_server)
        self.delegate=Mock();self.delegate.alive.return_value=False
        self.driver=self.new_driver()
        self.runtime=RuntimeSupervisor(self.root/'runtime.sqlite',self.driver,
            [ModuleSpec(n,'1.0.0') for n in MODULE_IDS],release_id='r1',release_sha256='a'*64,node_id='cloud')
        self.addCleanup(lambda:self.runtime.stop(administrative=True))
    def close_server(self):
        self.server.shutdown();self.server.server_close();self.thread.join(3)
    def new_driver(self):
        return BuiltinRuntimeDriver(self.delegate,journal_path=self.root/'runtime.sqlite',
            snapshot_path=self.root/'snapshot.json',http_port=self.server.server_address[1],
            node_id='cloud',release_id='r1',release_sha256='a'*64,authorize=lambda a,m:a=='start' and m=='unified-system')
    def publish(self):
        snapshot=self.runtime.snapshot();self.view.set(snapshot)
        write_snapshot(self.root/'snapshot.json',snapshot);self.driver.published(snapshot)
        return snapshot
    def start(self):
        self.runtime.start_module('unified-system');self.runtime.tick()
        self.assertFalse(self.runtime.snapshot()['modules']['unified-system']['ready'])
        self.publish();self.runtime.tick()
    def test_actual_journal_file_and_http_ready_without_global_readiness(self):
        self.start();snapshot=self.runtime.snapshot()
        self.assertTrue(snapshot['modules']['unified-system']['ready']);self.assertFalse(snapshot['ready'])
        self.assertTrue(all(snapshot['modules'][n]['state']=='STOPPED' for n in MODULE_IDS-{'unified-system'}))
        self.delegate.start.assert_not_called();self.delegate.ready.assert_not_called()
    def test_missing_publication_and_wrong_http_fail_closed(self):
        self.runtime.start_module('unified-system');self.runtime.tick();self.runtime.tick()
        self.assertFalse(self.runtime.snapshot()['modules']['unified-system']['ready'])
        self.publish();wrong=self.view.get();wrong['release_id']='other';self.view.set(wrong)
        self.runtime.tick();self.assertFalse(self.runtime.snapshot()['modules']['unified-system']['ready'])
        self.publish()
        import socket
        with socket.socket() as unused:
            unused.bind(('127.0.0.1',0));port=unused.getsockname()[1]
        original=self.driver.port;self.driver.port=port
        self.runtime.tick();self.assertFalse(self.runtime.snapshot()['modules']['unified-system']['ready'])
        self.driver.port=original
    def test_modified_snapshot_and_stale_publication_fail_closed(self):
        self.start();self.publish()
        (self.root/'snapshot.json').write_text('{}');self.runtime.tick()
        self.assertFalse(self.runtime.snapshot()['modules']['unified-system']['ready'])
        import os
        if hasattr(os,'mkfifo'):
            (self.root/'snapshot.json').unlink();os.mkfifo(self.root/'snapshot.json')
            self.runtime.tick();self.assertFalse(self.runtime.snapshot()['modules']['unified-system']['ready'])
            (self.root/'snapshot.json').unlink()
        self.publish()
        from unittest.mock import patch
        expired=self.driver.publication[2]+PUBLICATION_MAX_AGE+.01
        with patch('unified_system.runtime_builtin.time.monotonic',return_value=expired):self.runtime.tick()
        self.assertFalse(self.runtime.snapshot()['modules']['unified-system']['ready'])
    def test_operation_identity_stop_and_previous_instance_are_not_process_ownership(self):
        self.start();op=next(iter(self.driver.operations));spec=ModuleSpec('unified-system','1.0.0')
        self.assertEqual(self.driver.start(spec,'r1',op),op)
        with self.assertRaises(ValueError):self.driver.start(spec,'other',op)
        generation=self.driver.generation;self.driver.generation='different-instance'
        self.assertFalse(self.driver.alive(op));self.driver.generation=generation
        other=self.new_driver();self.assertFalse(other.alive(op));other.stop(op)
        self.delegate.stop.assert_not_called()
        self.driver.stop(op);self.driver.stop(op);self.assertFalse(self.driver.alive(op))
        with self.assertRaises(ValueError):self.driver.start(spec,'r1',op)
    def test_wrong_journal_identity_and_forged_publication_are_rejected(self):
        self.runtime.start_module('unified-system');self.runtime.tick()
        snapshot=self.runtime.snapshot();snapshot['revision']+=1
        with self.assertRaises(ValueError):self.driver.published(snapshot)
        self.publish()
        import sqlite3
        with sqlite3.connect(self.root/'runtime.sqlite') as db:
            identity=json.loads(db.execute('SELECT body FROM identity').fetchone()[0]);identity['node_id']='wrong'
            db.execute('UPDATE identity SET body=?',(json.dumps(identity),))
        op=next(iter(self.driver.operations))
        self.assertFalse(self.driver.ready(ModuleSpec('unified-system','1.0.0'),op,'r1')['ready'])
    def test_delegate_methods_remain_exact_and_builtin_authorization_required(self):
        spec=ModuleSpec('math','1.0.0');self.delegate.start.return_value='child'
        self.assertEqual(self.driver.start(spec,'r1','child'),'child')
        self.driver.alive('child');self.driver.ready(spec,'child','r1');self.driver.stop('child')
        self.delegate.start.assert_called_once_with(spec,'r1','child')
        self.delegate.stop.assert_called_once_with('child')
        self.driver.authorize=lambda *_:False
        self.runtime.start_module('unified-system');self.runtime.tick()
        self.assertFalse(any(x['active'] for x in self.driver.operations.values()))

    def test_five_healthy_delegates_inside_their_deadlines_allow_builtin_ready(self):
        import time
        self.delegate.start.side_effect=lambda spec,release,operation:operation
        self.delegate.alive.return_value=True
        def healthy(spec,handle,release):
            time.sleep(.43)
            return dict(module_id=spec.module_id,version=spec.version,release_id=release,ready=True)
        self.delegate.ready.side_effect=healthy
        self.runtime.start();self.runtime.tick();self.publish();self.runtime.tick()
        snapshot=self.runtime.snapshot()
        self.assertTrue(all(snapshot['modules'][n]['ready'] for n in MODULE_IDS-{'unified-system'}))
        self.assertTrue(snapshot['modules']['unified-system']['ready'])
        self.assertTrue(snapshot['ready'])

    def test_publication_expiring_during_real_http_probe_is_not_ready(self):
        from unittest.mock import patch
        self.start();self.publish();handle=next(iter(self.driver.operations))
        stamp=self.driver.publication[2];clock=[stamp+PUBLICATION_MAX_AGE-.05]
        original=self.driver._http_bytes
        def crossing():
            raw=original();clock[0]=stamp+PUBLICATION_MAX_AGE+.01;return raw
        with patch('unified_system.runtime_builtin.time.monotonic',side_effect=lambda:clock[0]),patch.object(self.driver,'_http_bytes',side_effect=crossing):
            self.assertFalse(self.driver.ready(ModuleSpec('unified-system','1.0.0'),handle,'r1')['ready'])

    def test_registered_extension_keeps_valid_builtin_and_bounded_freshness(self):
        from unittest.mock import patch
        self.runtime.register(ModuleSpec('extension','1.0.0'))
        self.start();self.publish()
        snapshot=self.runtime.snapshot()
        self.assertEqual(snapshot['modules']['extension']['state'],'STOPPED')
        self.assertFalse(snapshot['ready'])
        handle=next(iter(self.driver.operations));stamp=self.driver.publication[2]
        with patch('unified_system.runtime_builtin.time.monotonic',return_value=stamp+PUBLICATION_MAX_AGE+.2):
            self.assertTrue(self.driver.ready(ModuleSpec('unified-system','1.0.0'),handle,'r1')['ready'])
        with patch('unified_system.runtime_builtin.time.monotonic',return_value=stamp+PUBLICATION_MAX_AGE+.51):
            self.assertFalse(self.driver.ready(ModuleSpec('unified-system','1.0.0'),handle,'r1')['ready'])
