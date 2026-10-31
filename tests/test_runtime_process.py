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
