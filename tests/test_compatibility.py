import unittest
from unified_system.compatibility import validate_response
from unified_system.contracts import ContractError
from unified_system.status_api import ReadOnlySupervisorApp
import json

class CompatibilityTests(unittest.TestCase):
    def payload(self,name,status="UNAVAILABLE"):
        return {"api_version":{"major":1,"minor":0},"producer":{"grid":"bybit-cluster-grid","strattester":"strattester","supervisor":"unified-system"}[name],"read_only":True,"status":status,"trading_authorized":False,"physical_acceptance":"NOT_RUN"}
    def test_strattester(self):
        self.assertFalse(validate_response("strattester","health",503,self.payload("strattester"))["production_ready"])
    def test_grid(self):
        self.assertFalse(validate_response("grid","health",200,self.payload("grid"))["production_ready"])
    def test_false_ready(self):
        with self.assertRaises(ContractError):validate_response("grid","health",200,self.payload("grid","AVAILABLE"))
    def test_producer_mismatch(self):
        with self.assertRaises(ContractError):validate_response("grid","health",503,self.payload("strattester"))
    def test_bool_major(self):
        x=self.payload("grid");x["api_version"]["major"]=True
        with self.assertRaises(ContractError):validate_response("grid","health",503,x)
    def test_supervisor_authority(self):
        x=self.payload("supervisor");x["trading_authorized"]=True
        with self.assertRaises(ContractError):validate_response("supervisor","health",503,x)
    def test_supervisor_wsgi(self):
        app=ReadOnlySupervisorApp()
        captured=[]
        result=b"".join(app({"REQUEST_METHOD":"GET","PATH_INFO":"/internal/v1/health","QUERY_STRING":""},lambda s,h:captured.append(s)))
        self.assertFalse(validate_response("supervisor","health",503,json.loads(result))["production_ready"])
if __name__=="__main__":unittest.main()
