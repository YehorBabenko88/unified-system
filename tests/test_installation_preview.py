import json,socket,tempfile,time,unittest,io,threading,os
from contextlib import redirect_stdout,redirect_stderr
from unittest.mock import patch
from pathlib import Path
from unified_system.installation_progress import InstallationProgress
from unified_system.installation_preview import InstallationPreview, preview_plan, main

class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.progress=InstallationProgress.create(Path(self.temp.name)/'preview.db','preview','node','a'*64)
    def request(self,host,payload):
        with socket.create_connection(host.address,timeout=2) as client:
            client.settimeout(3);client.sendall(payload);result=b''
            while True:
                chunk=client.recv(65536)
                if not chunk:break
                result+=chunk
            return result
    def get(self,host,path='/api/v1/installation',extra=b''):
        return self.request(host,b'GET '+path.encode()+b' HTTP/1.1\r\nHost: '+host.authority.encode()+b'\r\n'+extra+b'\r\n')
    def rebind_probe(self,address):
        # POSIX TIME_WAIT survives listener close. Match the production server's
        # reuse policy; on Windows keep the exclusive raw bind probe unchanged.
        with socket.socket() as check:
            if os.name!='nt':check.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            check.bind(address)
    def test_probe_rejects_live_listener_and_accepts_closed_listener(self):
        with InstallationPreview(self.progress) as host:
            self.get(host)
            with self.assertRaises(OSError):self.rebind_probe(host.address)
        self.assertEqual(host._server.socket.fileno(),-1)
        self.rebind_probe(host.address)
    def test_explicit_start_actual_source_and_cleanup(self):
        host=InstallationPreview(self.progress);self.assertIsNone(host.address)
        with host:
            port=host.address[1];response=self.get(host)
            self.assertTrue(response.startswith(b'HTTP/1.0 200'));self.assertIn(b'NOT_PROVEN',response)
        self.assertFalse(host.running)
        self.assertEqual(host._server.socket.fileno(),-1)
        self.rebind_probe(('127.0.0.1',port))
    def test_rejections_and_no_second_pipelined_response(self):
        with InstallationPreview(self.progress) as host:
            for extra in (b'Origin: http://evil\r\n',b'Transfer-Encoding: chunked\r\n',b'Content-Length: 2\r\n',b'Host: evil\r\n',b'Content-Length: 0\r\nContent-Length: 0\r\n'):
                with self.subTest(extra=extra):self.assertIn(b' 400 ',self.get(host,extra=extra).split(b'\r\n')[0])
            self.assertIn(b' 400 ',self.request(host,b'GET / HTTP/1.1\r\nHost: evil.invalid\r\n\r\n').split(b'\r\n')[0])
            self.assertIn(b' 400 ',self.get(host,'/?secret=yes').split(b'\r\n')[0])
            self.assertIn(b' 405 ',self.request(host,b'POST / HTTP/1.0\r\nHost: '+host.authority.encode()+b'\r\n\r\n').split(b'\r\n')[0])
            request=b'GET / HTTP/1.1\r\nHost: '+host.authority.encode()+b'\r\n\r\n'
            response=self.request(host,request+request)
            self.assertEqual(response.count(b'HTTP/1.0 '),1)
    def test_unframed_body_discarded_and_bounded_headers(self):
        with InstallationPreview(self.progress) as host:
            response=self.get(host)+b''
            self.assertIn(b' 200 ',response.split(b'\r\n')[0])
            payload=b'GET / HTTP/1.1\r\nHost: '+host.authority.encode()+b'\r\n\r\nSECRET GET /execute HTTP/1.1\r\n\r\n'
            response=self.request(host,payload);self.assertEqual(response.count(b'HTTP/1.0 '),1);self.assertNotIn(b'SECRET',response)
            self.assertIn(b' 431 ',self.get(host,extra=b'X-Test: '+b'a'*9000+b'\r\n').split(b'\r\n')[0])
    def test_slow_request_and_lifetime_cleanup(self):
        host=InstallationPreview(self.progress,duration=0.3,request_timeout=0.1)
        with host:
            with socket.create_connection(host.address,timeout=2) as client:
                client.sendall(b'GET / HTTP/1.1\r\n');client.settimeout(1)
                self.assertEqual(client.recv(1024),b'')
            time.sleep(0.45);self.assertFalse(host.running)
    def test_default_cli_is_plan_only_and_request_logs_are_silent(self):
        output=io.StringIO()
        with patch('unified_system.installation_preview._Server',side_effect=AssertionError('must not bind')),redirect_stdout(output):
            result=main(['--journal',str(self.progress.path),'--installation-id','preview','--node-id','node','--release-manifest-sha256','a'*64])
        self.assertEqual(result,0);self.assertFalse(json.loads(output.getvalue())['listener_started'])
        errors=io.StringIO()
        with redirect_stderr(errors),InstallationPreview(self.progress) as host:
            self.get(host,'/?PRIVATE=SECRET')
        self.assertEqual(errors.getvalue(),'')
    def test_partial_headers_cannot_outlive_whole_preview(self):
        host=InstallationPreview(self.progress,duration=0.15,request_timeout=1)
        with host:
            with socket.create_connection(host.address,timeout=2) as client:
                client.sendall(b'GET / HTTP/1.1\r\n');client.settimeout(1)
                self.assertEqual(client.recv(1024),b'')
            time.sleep(0.1);self.assertFalse(host.running)
    def test_byte_trickle_single_line_cannot_extend_network_deadline(self):
        host=InstallationPreview(self.progress,duration=0.15,request_timeout=0.1).start()
        client=socket.create_connection(host.address,timeout=2)
        stopped=threading.Event()
        def trickle():
            try:
                client.sendall(b'GET / HTTP/1.1\r\nX-Slow: ')
                while not stopped.wait(0.02):client.sendall(b'x')
            except OSError:pass
        sender=threading.Thread(target=trickle);sender.start()
        try:
            time.sleep(0.32)
            self.assertFalse(host.running,'single-line trickle escaped whole preview deadline')
            self.rebind_probe(host.address)
        finally:
            stopped.set()
            try:client.shutdown(socket.SHUT_RDWR)
            except OSError:pass
            client.close();sender.join(1);host.close()

    def test_close_interrupts_owned_partial_request_and_joins_watchdogs(self):
        host=InstallationPreview(self.progress,duration=5,request_timeout=2).start()
        with socket.create_connection(host.address,timeout=2) as client:
            client.sendall(b'GET / HTTP/1.1\r\nX-Slow: ')
            limit=time.monotonic()+1
            while host._active is None and time.monotonic()<limit:time.sleep(0.005)
            self.assertIsNotNone(host._active)
            started=time.monotonic();host.close()
            self.assertLess(time.monotonic()-started,0.7)
        self.assertFalse(host.running);self.assertFalse(host._lifetime_timer.is_alive());self.assertIsNone(host._request_timer)
    def test_close_does_not_depend_on_shutdown_waking_a_buffered_read(self):
        host=InstallationPreview(self.progress,duration=5,request_timeout=2).start()
        try:
            with socket.create_connection(host.address,timeout=2) as client:
                client.sendall(b'GET / HTTP/1.1\r\nX-Slow: ')
                limit=time.monotonic()+1
                while host._active is None and time.monotonic()<limit:time.sleep(0.005)
                self.assertIsNotNone(host._active)
                with patch.object(InstallationPreview,'_shutdown',return_value=None):
                    started=time.monotonic();host.close()
                    self.assertLess(time.monotonic()-started,0.7)
        finally:host.close()

    def test_lifetime_closes_listener_even_during_source_computation(self):
        host=InstallationPreview(self.progress,duration=0.15,request_timeout=1).start()
        entered=threading.Event();release=threading.Event();original=InstallationProgress.snapshot
        def slow(progress):
            entered.set();release.wait(2);return original(progress)
        client=socket.create_connection(host.address,timeout=2)
        try:
            with patch.object(InstallationProgress,'snapshot',slow):
                client.sendall(b'GET /api/v1/installation HTTP/1.1\r\nHost: '+host.authority.encode()+b'\r\n\r\n')
                self.assertTrue(entered.wait(1));time.sleep(0.25)
                self.assertEqual(host._server.socket.fileno(),-1)
                self.rebind_probe(host.address)
                release.set();host.close()
        finally:release.set();client.close();host.close()
        self.assertFalse(host.running)

    def test_limits_and_plan_are_inert(self):
        for changes in ({'port':True},{'port':-1},{'duration':301},{'request_timeout':0},{'request_timeout':10}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):InstallationPreview(self.progress,**changes)
        plan=preview_plan(self.progress,port=0,duration=60)
        self.assertEqual(plan['mode'],'PLAN_ONLY');self.assertFalse(plan['listener_started']);self.assertIn('shutdown',plan['rollback'].lower())
        self.assertFalse(plan['installation_authority']);self.assertEqual(plan['journal'],str(self.progress.path))

if __name__=='__main__':unittest.main()
