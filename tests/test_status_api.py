import json
import unittest
from unified_system.status_api import ReadOnlySupervisorApp

def call(app,path,method="GET",query=""):
    seen={}
    def start(status,headers):
        seen["code"]=int(status.split()[0])
        seen["headers"]=dict(headers)
    result=b"".join(app({"REQUEST_METHOD":method,"PATH_INFO":path,"QUERY_STRING":query},start))
    return seen["code"],json.loads(result),seen["headers"]

class StatusAPITests(unittest.TestCase):
    def test_capabilities(self):
        code,body,headers=call(ReadOnlySupervisorApp(),"/internal/v1/capabilities")
        self.assertEqual(code,200)
        self.assertIs(body["trading_authorized"],False)
        self.assertIs(body["capabilities"]["trading"],False)
        self.assertEqual(headers["Cache-Control"],"no-store")
    def test_absent(self):
        code,body,_=call(ReadOnlySupervisorApp(),"/internal/v1/health")
        self.assertEqual(code,503)
        self.assertEqual(body["status"],"UNAVAILABLE")
    def test_snapshot(self):
        code,body,_=call(ReadOnlySupervisorApp(lambda:{"state":"BLOCKED","secret":"must-not-leak"}),"/internal/v1/status")
        self.assertEqual(code,200)
        self.assertEqual(body["state"],"BLOCKED")
        self.assertNotIn("secret",body)
    def test_invalid_state(self):
        code,body,_=call(ReadOnlySupervisorApp(lambda:{"state":"TRADING"}),"/internal/v1/status")
        self.assertEqual(code,503)
    def test_405(self):
        code,body,headers=call(ReadOnlySupervisorApp(),"/internal/v1/status","POST")
        self.assertEqual(code,405)
        self.assertEqual(headers["Allow"],"GET")
    def test_queries_fail(self):
        self.assertEqual(call(ReadOnlySupervisorApp(),"/internal/v1/capabilities",query="secret=yes")[0],400)
    def test_no_route(self):
        self.assertEqual(call(ReadOnlySupervisorApp(),"/internal/v1/orders")[0],404)
    def test_provider_error(self):
        def fail():raise RuntimeError("sensitive diagnostic")
        # Unexpected provider exceptions intentionally bubble to the host,
        # never transform into a false health PASS.
        with self.assertRaises(RuntimeError):call(ReadOnlySupervisorApp(fail),"/internal/v1/health")
if __name__=="__main__":unittest.main()
