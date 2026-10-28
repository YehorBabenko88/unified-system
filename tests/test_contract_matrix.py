import unittest
from unified_system.contract_matrix import evaluate

def health(producer):
    return {"api_version":{"major":1,"minor":0},"producer":producer,"read_only":True,
            "status":"UNAVAILABLE","trading_authorized":False,"physical_acceptance":"NOT_RUN"}

class MatrixTests(unittest.TestCase):
    def test_all_absent(self):
        result=evaluate(strattester_health=health("strattester"),
                        grid_health=health("bybit-cluster-grid"),
                        supervisor_health=health("unified-system"))
        self.assertFalse(result["production_ready"])
        self.assertEqual(result["research"]["status"],"UNAVAILABLE")
    def test_malformed_peer(self):
        result=evaluate(strattester_health={},grid_health=health("bybit-cluster-grid"),
                        supervisor_health=health("unified-system"))
        self.assertEqual(result["sources"]["strattester"]["contract"],"INVALID")
    def test_untrusted_grid_available(self):
        result=evaluate(strattester_health=health("strattester"),
                        grid_health=health("bybit-cluster-grid"),
                        supervisor_health=health("unified-system"),
                        grid_snapshot={"api_version":{"major":1,"minor":1},
                                       "producer":"bybit-cluster-grid","status":"AVAILABLE"})
        self.assertEqual(result["grid_snapshot"]["status"],"UNAVAILABLE")
        self.assertFalse(result["trading_authorized"])
if __name__=="__main__":unittest.main()
