import unittest
from unified_system.adapters import compose_dashboard,normalize_source
from unified_system.contracts import ContractError

class AdapterTests(unittest.TestCase):
    def fixture(self,name):
        return {"source":name,"status":"READY","timestamp_ms":1700000000000,"items":[{"value":1}],"synthetic":True}
    def test_both(self):
        r=compose_dashboard(self.fixture("strattester"),self.fixture("grid"))
        self.assertEqual(r["sources"]["grid"]["count"],1)
        self.assertFalse(r["trading_authorized"])
    def test_missing(self):
        self.assertEqual(compose_dashboard()["sources"]["grid"]["status"],"UNAVAILABLE")
    def test_cross_source(self):
        with self.assertRaises(ContractError):normalize_source("grid",self.fixture("strattester"))
    def test_fake_real(self):
        x=self.fixture("grid");x["synthetic"]=False
        with self.assertRaises(ContractError):normalize_source("grid",x)
    def test_timestamp_bool(self):
        x=self.fixture("grid");x["timestamp_ms"]=True
        with self.assertRaises(ContractError):normalize_source("grid",x)
    def test_unavailable_payload(self):
        x=self.fixture("grid");x["status"]="UNAVAILABLE"
        with self.assertRaises(ContractError):normalize_source("grid",x)
    def test_bounded(self):
        x=self.fixture("grid");x["items"]=[{}]*101
        with self.assertRaises(ContractError):normalize_source("grid",x)
if __name__=="__main__":unittest.main()
