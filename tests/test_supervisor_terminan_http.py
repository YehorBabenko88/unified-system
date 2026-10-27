"""Disposable real HTTP Supervisor-to-Terminan-style consumer test."""
import http.client
import json
import threading
import unittest
from wsgiref.simple_server import make_server,WSGIRequestHandler
from unified_system.status_api import ReadOnlySupervisorApp
from unified_system.compatibility import validate_response

class Quiet(WSGIRequestHandler):
    def log_message(self,*args):pass

class SupervisorConsumerHTTP(unittest.TestCase):
    def test_actual_loopback_health(self):
        app=ReadOnlySupervisorApp(lambda:{"state":"BLOCKED"})
        server=make_server("127.0.0.1",0,app,handler_class=Quiet)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            connection=http.client.HTTPConnection("127.0.0.1",server.server_port,timeout=2)
            connection.request("GET","/internal/v1/health",headers={"Accept":"application/json"})
            response=connection.getresponse()
            self.assertEqual(response.status,200)
            data=json.loads(response.read())
            connection.close()
            result=validate_response("supervisor","health",200,data)
            self.assertEqual(result["contract"],"V1_SHAPE_VALID")
            self.assertEqual(data["state"],"BLOCKED")
            self.assertFalse(data["trading_authorized"])
            self.assertEqual(data["provenance"],"UNVERIFIED")
        finally:
            server.shutdown();server.server_close();thread.join(timeout=3)
            self.assertFalse(thread.is_alive())

if __name__=="__main__":unittest.main()
