import hashlib
import json
from pathlib import Path
import socket
import sys
import tempfile
import time
import unittest

from unified_system.runtime import ModuleSpec
from unified_system.runtime_process import ProcessDriver


WORKER = '''import json,os
from http.server import BaseHTTPRequestHandler,HTTPServer
class H(BaseHTTPRequestHandler):
 def do_GET(self):
  b=json.dumps(dict(module_id=os.environ['UNIFIED_MODULE_ID'],version=os.environ['UNIFIED_MODULE_VERSION'],release_id=os.environ['UNIFIED_RELEASE_ID'],instance_token=os.environ['UNIFIED_INSTANCE_TOKEN'],ready=True)).encode()
  self.send_response(200);self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
 def log_message(self,*a):pass
HTTPServer(('127.0.0.1',int(os.environ['PORT'])),H).serve_forever()
'''


class ProcessTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.worker=self.root/'worker.py';self.worker.write_text(WORKER)
        with socket.socket() as s:s.bind(('127.0.0.1',0));self.port=s.getsockname()[1]
        self.program=dict(argv=[str(Path(sys.executable).resolve()),str(self.worker)],cwd=str(self.root),
            executable_sha256=hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
            file_pins={'worker.py':hashlib.sha256(self.worker.read_bytes()).hexdigest()},
            health_url=f'http://127.0.0.1:{self.port}/health',env={'PORT':str(self.port)})
    def driver(self,authorized=True):
        return ProcessDriver(self.root/'private',{'math':self.program},authorize=lambda action,module:authorized)
    def test_real_owned_child_functional_health_idempotence_and_stop(self):
        d=self.driver();spec=ModuleSpec('math','1.0.0');op='a'*32
        self.assertEqual(d.start(spec,'release-1',op),op);self.addCleanup(lambda:d.stop(op))
        for _ in range(40):
            if d.ready(spec,op,'release-1').get('ready'):break
            time.sleep(.025)
        self.assertTrue(d.ready(spec,op,'release-1')['ready'])
        self.assertEqual(d.start(spec,'release-1',op),op)
        second=self.driver();self.assertTrue(second.alive(op))
        self.assertFalse(second.ready(spec,op,'wrong-release')['ready'])
        second.stop(op);self.assertFalse(d.alive(op))
        self.assertTrue(d.children[op].stdin.closed)
    def test_health_header_trickle_has_absolute_deadline(self):
        # A real child keeps every socket read below the inactivity timeout.
        worker = WORKER.replace("  b=json.dumps", "  import time\n  self.wfile.write(b'HTTP/1.0 200 OK\\r\\nX-Slow: ');self.wfile.flush()\n  for _ in range(30):\n   self.wfile.write(b'x');self.wfile.flush();time.sleep(.05)\n  return\n  b=json.dumps")
        self.worker.write_text(worker)
        self.program['file_pins']['worker.py']=hashlib.sha256(self.worker.read_bytes()).hexdigest()
        d=self.driver();spec=ModuleSpec('math','1.0.0');op='e'*32
        d.start(spec,'release-1',op);self.addCleanup(lambda:d.stop(op))
        # Wait for the actual listener, without making a health request.
        for _ in range(100):
            try:
                with socket.create_connection(('127.0.0.1',self.port),timeout=.05):break
            except OSError:time.sleep(.01)
        started=time.monotonic()
        self.assertFalse(d.ready(spec,op,'release-1')['ready'])
        self.assertLess(time.monotonic()-started,1.1,'health headers need an absolute deadline')

    def test_health_body_trickle_has_absolute_deadline(self):
        worker = WORKER.replace("  b=json.dumps", "  import time\n  self.send_response(200);self.send_header('Content-Length','30');self.end_headers()\n  for _ in range(30):\n   self.wfile.write(b'x');self.wfile.flush();time.sleep(.05)\n  return\n  b=json.dumps")
        self.worker.write_text(worker)
        self.program['file_pins']['worker.py']=hashlib.sha256(self.worker.read_bytes()).hexdigest()
        d=self.driver();spec=ModuleSpec('math','1.0.0');op='f'*32
        d.start(spec,'release-1',op);self.addCleanup(lambda:d.stop(op))
        for _ in range(100):
            try:
                with socket.create_connection(('127.0.0.1',self.port),timeout=.05):break
            except OSError:time.sleep(.01)
        started=time.monotonic()
        self.assertFalse(d.ready(spec,op,'release-1')['ready'])
        self.assertLess(time.monotonic()-started,1.1,'health body needs an absolute deadline')

    def test_seeded_timestamp_valid_dependency_cache_cannot_override_pinned_source(self):
        import os,py_compile,subprocess
        from unittest.mock import patch
        helper=self.root/'helper.py';helper.write_text("VALUE='honest'\n")
        poison=self.root/'poison.py';poison.write_text("VALUE='poison'\n")
        cache=self.root/'seeded-cache';cache.mkdir()
        code="import importlib.util,sys;sys.pycache_prefix=sys.argv[1];print(importlib.util.cache_from_source(sys.argv[2]))"
        cached=Path(subprocess.check_output([sys.executable,'-c',code,str(cache),str(helper)],text=True).strip())
        # Compile malicious bytes with honest source timestamp AND size metadata.
        self.assertEqual(len(helper.read_bytes()),len(poison.read_bytes()))
        os.utime(poison,ns=(helper.stat().st_atime_ns,helper.stat().st_mtime_ns))
        cached.parent.mkdir(parents=True);py_compile.compile(str(poison),cfile=str(cached),doraise=True)
        marker=self.root/'marker.txt'
        self.worker.write_text("import helper\nfrom pathlib import Path\nPath("+repr(str(marker))+").write_text(helper.VALUE)\n"+WORKER)
        self.program['file_pins']={name:hashlib.sha256((self.root/name).read_bytes()).hexdigest() for name in ('worker.py','helper.py')}
        self.program['env']['PYTHONPYCACHEPREFIX']=str(cache)
        d=self.driver();op='1'*32
        with patch.dict(os.environ,{'PYTHONPYCACHEPREFIX':str(cache)}):d.start(ModuleSpec('math','1.0.0'),'r',op)
        self.addCleanup(lambda:d.stop(op))
        for _ in range(100):
            if marker.exists():break
            time.sleep(.01)
        self.assertEqual(marker.read_text(),'honest')

    def test_default_denied_and_tampered_program_not_executed(self):
        with self.assertRaises(ValueError):self.driver(False).start(ModuleSpec('math','1.0.0'),'r','b'*32)
        self.worker.write_text('raise RuntimeError("tampered")')
        with self.assertRaises(ValueError):self.driver().start(ModuleSpec('math','1.0.0'),'r','c'*32)
    def test_unknown_or_reused_pid_is_never_killed(self):
        d=self.driver();op='d'*32
        (d.root/(op+'.json')).write_text(json.dumps(dict(pid=1,created=-1,module_id='math',token='x',release_id='r',version='1.0.0')))
        self.assertFalse(d.alive(op))
        with self.assertRaises(ValueError):d.stop(op)
    def test_non_loopback_health_and_shell_commands_rejected(self):
        self.program['health_url']='http://example.com/health'
        with self.assertRaises(ValueError):self.driver()
        self.program['health_url']=f'http://127.0.0.1:{self.port}/health';self.program['argv']=[sys.executable,'-c','print(1)']
        with self.assertRaises(ValueError):self.driver()


if __name__=='__main__':unittest.main()

class PathPolicyTests(unittest.TestCase):
    def test_linked_ancestor_rejected_before_descendant_metadata(self):
        from unittest.mock import patch
        from unified_system.runtime_process import _safe_path
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);target=root/'target';target.mkdir();(target/'child').write_text('outside namespace')
            link=root/'link'
            try:link.symlink_to(target,target_is_directory=True)
            except OSError:self.skipTest('symlink privilege unavailable')
            seen=[];original=Path.lstat
            def record(path):seen.append(path);return original(path)
            with patch.object(Path,'lstat',record),self.assertRaises(ValueError):_safe_path(link/'child')
            self.assertNotIn(link/'child',seen)
    def test_dangling_links_are_not_valid_future_paths(self):
        from unified_system.runtime_process import _safe_path
        with tempfile.TemporaryDirectory() as temp:
            link=Path(temp)/'link'
            try:link.symlink_to(Path(temp)/'missing',target_is_directory=True)
            except OSError:self.skipTest('symlink privilege unavailable')
            with self.assertRaises(ValueError):_safe_path(link)


class OwnedPythonTests(unittest.TestCase):
    def test_isolated_raw_bootstrap_runs_honest_source_and_preserves_owned_identity(self):
        import os,py_compile,subprocess
        bootstrap=Path(__file__).resolve().parents[1]/'unified_system/owned_python.py'
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();cache=root/'private';cache.mkdir(mode=0o700)
            package=root/'src'/'demo';package.mkdir(parents=True);(package/'__init__.py').write_text('')
            helper=package/'helper.py';helper.write_text("VALUE='honest'\n")
            poison=root/'poison.py';poison.write_text("VALUE='poison'\n")
            os.utime(poison,ns=(helper.stat().st_atime_ns,helper.stat().st_mtime_ns))
            cached=Path(__import__('importlib.util',fromlist=['cache_from_source']).cache_from_source(str(helper)))
            cached.parent.mkdir();py_compile.compile(str(poison),cfile=str(cached),doraise=True)
            (package/'app.py').write_text("from .helper import VALUE\nimport json,os,sys\nprint(json.dumps(dict(value=VALUE,pid=os.getpid(),token=os.environ['UNIFIED_INSTANCE_TOKEN'],cache=sys.pycache_prefix,isolated=sys.flags.isolated,no_site=sys.flags.no_site,no_write=sys.dont_write_bytecode)))\n")
            dependency=root/'dependency';dependency.mkdir();marker=root/'UNWANTED'
            (dependency/'sitecustomize.py').write_text('raise RuntimeError("must not run")')
            (dependency/'evil.pth').write_text('import pathlib;pathlib.Path('+repr(str(marker))+').touch()')
            env=dict(os.environ,UNIFIED_MODULE_ID='meta_analyse',UNIFIED_MODULE_VERSION='1.0.0',UNIFIED_RELEASE_ID='r',UNIFIED_INSTANCE_TOKEN='a'*64,UNIFIED_PRIVATE_CACHE_ROOT=str(cache),PYTHONPYCACHEPREFIX=str(cached.parent))
            command=[sys.executable,'-I','-S','-B',str(bootstrap),'--source-root',str(root),'--module','demo.app','--dependency-root',str(dependency)]
            child=subprocess.Popen(command,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            stdout,stderr=child.communicate(timeout=10);self.assertEqual(child.returncode,0,stderr)
            result=json.loads(stdout);self.assertEqual(result['value'],'honest');self.assertEqual(result['pid'],child.pid)
            self.assertEqual(result['token'],'a'*64);self.assertEqual((result['isolated'],result['no_site'],result['no_write']),(1,1,True))
            self.assertTrue(Path(result['cache']).is_relative_to(cache));self.assertFalse(marker.exists())
            bad_commands=[command[:1]+command[2:],command[:2]+command[3:],command[:3]+command[4:],
                          command[:],command[:],command[:]]
            bad_commands[3][bad_commands[3].index('--source-root')+1]='relative'
            bad_commands[4][bad_commands[4].index('--module')+1]='..outside'
            bad_commands[5][bad_commands[5].index('--module')+1]='missing.app'
            for bad in bad_commands:
                with self.subTest(command=bad):self.assertNotEqual(subprocess.run(bad,env=env,capture_output=True,timeout=10).returncode,0)
            outside=dependency/'outside.py';outside.write_text('raise RuntimeError(\"outside source must not run\")')
            outside_command=command.copy();outside_command[outside_command.index('--module')+1]='outside'
            outside_result=subprocess.run(outside_command,env=env,capture_output=True,text=True,timeout=10)
            self.assertNotEqual(outside_result.returncode,0);self.assertNotIn('outside source must not run',outside_result.stderr)
            no_identity=dict(env,UNIFIED_INSTANCE_TOKEN='')
            self.assertNotEqual(subprocess.run(command,env=no_identity,capture_output=True,timeout=10).returncode,0)


class OwnedNamespaceTests(unittest.TestCase):
    def test_network_namespace_denied_without_path_metadata(self):
        from unittest.mock import patch
        from unified_system.owned_python import reject_external_namespace
        with patch.object(Path,'lstat',side_effect=AssertionError('metadata must not run')):
            for path in ('//server/share/file',r'\\server\share\file',r'\\?\C:\file'):
                with self.subTest(path=path),self.assertRaises(ValueError):reject_external_namespace(path)
            with self.assertRaises(ValueError):reject_external_namespace('Z:/file',platform='nt',drive_type=lambda _:4)
            with self.assertRaises(ValueError):reject_external_namespace('relative',platform='nt',drive_type=lambda _:3)
            reject_external_namespace('C:/file',platform='nt',drive_type=lambda _:3)
