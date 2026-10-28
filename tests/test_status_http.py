"""Disposable loopback-only WSGI transport regression, no persistent service."""
import http.client
import json
import threading
import unittest
from wsgiref.simple_server import make_server,WSGIRequestHandler
from unified_system.status_api import ReadOnlySupervisorApp

class Quiet(WSGIRequestHandler):
    def log_message(self,*args):pass

class StatusHTTPTests(unittest.TestCase):
    def test_loopback_get_and_post(self):
        server=make_server("127.0.0.1",0,ReadOnlySupervisorApp(),handler_class=Quiet)
        worker=threading.Thread(target=server.serve_forever,daemon=True)
        worker.start()
        try:
            conn=http.client.HTTPConnection("127.0.0.1",server.server_port,timeout=2)
            conn.request("GET","/internal/v1/capabilities")
            response=conn.getresponse()
            self.assertEqual(response.status,200)
            body=json.loads(response.read())
            self.assertFalse(body["trading_authorized"])
            self.assertFalse(body["capabilities"]["trading"])
            conn.close()
            conn=http.client.HTTPConnection("127.0.0.1",server.server_port,timeout=2)
            conn.request("POST","/internal/v1/status")
            response=conn.getresponse()
            self.assertEqual(response.status,405)
            self.assertEqual(response.getheader("Allow"),"GET")
            response.read();conn.close()
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=3)
            self.assertFalse(worker.is_alive())

if __name__=="__main__":unittest.main()
