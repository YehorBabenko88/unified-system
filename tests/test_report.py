import json
import unittest
from unified_system.report import build_report,report_bytes
from unified_system.contracts import ContractError

class ReportTests(unittest.TestCase):
    def fixture(self,name,status="READY"):
        return {"source":name,"status":status,"timestamp_ms":1700000000000,"items":[],"synthetic":True}
    def test_complete(self):
        r=build_report(strattester=self.fixture("strattester"),grid=self.fixture("grid"))
        self.assertEqual(r["overall"],"SYNTHETIC_READY")
        self.assertEqual(json.loads(report_bytes(strattester=self.fixture("strattester"),grid=self.fixture("grid")))["mode"],"READ_ONLY_SYNTHETIC")
    def test_missing_grid(self):
        self.assertEqual(build_report(strattester=self.fixture("strattester"))["overall"],"DEGRADED")
    def test_stale(self):
        self.assertEqual(build_report(strattester=self.fixture("strattester","STALE"),grid=self.fixture("grid"))["overall"],"DEGRADED")
    def test_invalid(self):
        with self.assertRaises(ContractError):report_bytes(grid={"source":"grid"})
if __name__=="__main__":unittest.main()
