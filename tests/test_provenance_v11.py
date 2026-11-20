import unittest
from unified_system.provenance_v11 import qualify_historical,inspect_market_data_snapshot,_digest

class ProvenanceV11Tests(unittest.TestCase):
    def record(self):
        r={"api_version":{"major":1,"minor":1},"producer":"terminan","mode":"HISTORICAL",
           "execution_authority":False,"source_revision":"a"*40,"producer_identity":"test-producer",
           "run_id":"r1","dataset":{"fingerprint":"b"*64,"coverage":"COMPLETE","missing_data":[]}}
        r["completion_receipt"]=_digest(r)
        return r
    def test_no_trust(self):
        self.assertEqual(qualify_historical(self.record())["reason"],"OWNER_RECEIPT_NOT_ADMITTED")
    def test_admitted_still_not_qualified(self):
        r=self.record(); pin=(r["producer_identity"],r["source_revision"],r["run_id"],r["completion_receipt"])
        self.assertEqual(qualify_historical(r,(pin,))["reason"],"SOURCE_ORACLE_NOT_INDEPENDENTLY_VERIFIED")
    def test_corrupt(self):
        r=self.record();r["dataset"]["coverage"]="PARTIAL"
        self.assertEqual(qualify_historical(r)["reason"],"GAP")
    def test_receipt_tamper(self):
        r=self.record();r["producer_identity"]="changed"
        self.assertEqual(qualify_historical(r)["reason"],"RECEIPT_INTEGRITY_FAILED")
    def test_grid_partial(self):
        r=inspect_market_data_snapshot({"api_version":{"major":1,"minor":1},"producer":"market_data","status":"PARTIAL","reason":"EXCHANGE_COMPLETENESS_UNATTESTED"})
        self.assertEqual(r["status"],"PARTIAL")
        self.assertFalse(r["trading_authorized"])
    def test_grid_false_available(self):
        self.assertEqual(inspect_market_data_snapshot({"api_version":{"major":1,"minor":1},"producer":"market_data","status":"AVAILABLE"})["status"],"UNAVAILABLE")
if __name__=="__main__":unittest.main()
