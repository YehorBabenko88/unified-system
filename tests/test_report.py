import json
import unittest
from unified_system.report import build_report,report_bytes
from unified_system.contracts import ContractError

class ReportTests(unittest.TestCase):
    def fixture(self,name,status="READY"):
        return {"source":name,"status":status,"timestamp_ms":1700000000000,"items":[],"synthetic":True}
    def test_complete(self):
        r=build_report(terminan=self.fixture("terminan"),market_data=self.fixture("market_data"))
        self.assertEqual(r["overall"],"SYNTHETIC_READY")
        self.assertEqual(json.loads(report_bytes(terminan=self.fixture("terminan"),market_data=self.fixture("market_data")))["mode"],"READ_ONLY_SYNTHETIC")
    def test_missing_grid(self):
        self.assertEqual(build_report(terminan=self.fixture("terminan"))["overall"],"DEGRADED")
    def test_stale(self):
        self.assertEqual(build_report(terminan=self.fixture("terminan","STALE"),market_data=self.fixture("market_data"))["overall"],"DEGRADED")
    def test_invalid(self):
        with self.assertRaises(ContractError):report_bytes(market_data={"source":"market_data"})
if __name__=="__main__":unittest.main()
