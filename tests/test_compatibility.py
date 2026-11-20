import unittest
from unified_system.compatibility import validate_response
from unified_system.contracts import ContractError
from unified_system.status_api import ReadOnlyControlPlaneApp
import json

class CompatibilityTests(unittest.TestCase):
    def payload(self,name,status="UNAVAILABLE"):
        return {"api_version":{"major":1,"minor":0},"producer":{"market_data":"market_data","terminan":"terminan","unified_system":"unified_system"}[name],"read_only":True,"status":status,"trading_authorized":False,"physical_acceptance":"NOT_RUN"}
    def test_terminan(self):
        self.assertFalse(validate_response("terminan","health",503,self.payload("terminan"))["production_ready"])
    def test_grid(self):
        self.assertFalse(validate_response("market_data","health",200,self.payload("market_data"))["production_ready"])
    def test_false_ready(self):
        with self.assertRaises(ContractError):validate_response("market_data","health",200,self.payload("market_data","AVAILABLE"))
    def test_producer_mismatch(self):
        with self.assertRaises(ContractError):validate_response("market_data","health",503,self.payload("terminan"))
    def test_bool_major(self):
        x=self.payload("market_data");x["api_version"]["major"]=True
        with self.assertRaises(ContractError):validate_response("market_data","health",503,x)
    def test_supervisor_authority(self):
        x=self.payload("unified_system");x["trading_authorized"]=True
        with self.assertRaises(ContractError):validate_response("unified_system","health",503,x)
    def test_supervisor_wsgi(self):
        app=ReadOnlyControlPlaneApp()
        captured=[]
        result=b"".join(app({"REQUEST_METHOD":"GET","PATH_INFO":"/internal/v1/health","QUERY_STRING":""},lambda s,h:captured.append(s)))
        self.assertFalse(validate_response("unified_system","health",503,json.loads(result))["production_ready"])
if __name__=="__main__":unittest.main()
