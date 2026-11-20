import unittest
from unified_system.adapters import compose_dashboard,normalize_source
from unified_system.contracts import ContractError

class AdapterTests(unittest.TestCase):
    def fixture(self,name):
        return {"source":name,"status":"READY","timestamp_ms":1700000000000,"items":[{"value":1}],"synthetic":True}
    def test_both(self):
        r=compose_dashboard(self.fixture("terminan"),self.fixture("market_data"))
        self.assertEqual(r["sources"]["market_data"]["count"],1)
        self.assertFalse(r["trading_authorized"])
    def test_missing(self):
        self.assertEqual(compose_dashboard()["sources"]["market_data"]["status"],"UNAVAILABLE")
    def test_cross_source(self):
        with self.assertRaises(ContractError):normalize_source("market_data",self.fixture("terminan"))
    def test_fake_real(self):
        x=self.fixture("market_data");x["synthetic"]=False
        with self.assertRaises(ContractError):normalize_source("market_data",x)
    def test_timestamp_bool(self):
        x=self.fixture("market_data");x["timestamp_ms"]=True
        with self.assertRaises(ContractError):normalize_source("market_data",x)
    def test_unavailable_payload(self):
        x=self.fixture("market_data");x["status"]="UNAVAILABLE"
        with self.assertRaises(ContractError):normalize_source("market_data",x)
    def test_bounded(self):
        x=self.fixture("market_data");x["items"]=[{}]*101
        with self.assertRaises(ContractError):normalize_source("market_data",x)
if __name__=="__main__":unittest.main()
