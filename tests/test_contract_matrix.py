import unittest
from unified_system.contract_matrix import evaluate

def health(producer):
    return {"api_version":{"major":1,"minor":0},"producer":producer,"read_only":True,
            "status":"UNAVAILABLE","trading_authorized":False,"physical_acceptance":"NOT_RUN"}

class MatrixTests(unittest.TestCase):
    def test_all_absent(self):
        result=evaluate(terminan_health=health("terminan"),
                        market_data_health=health("market_data"),
                        unified_system_health=health("unified_system"))
        self.assertFalse(result["production_ready"])
        self.assertEqual(result["research"]["status"],"UNAVAILABLE")
    def test_malformed_peer(self):
        result=evaluate(terminan_health={},market_data_health=health("market_data"),
                        unified_system_health=health("unified_system"))
        self.assertEqual(result["sources"]["terminan"]["contract"],"INVALID")
    def test_untrusted_grid_available(self):
        result=evaluate(terminan_health=health("terminan"),
                        market_data_health=health("market_data"),
                        unified_system_health=health("unified_system"),
                        market_data_snapshot={"api_version":{"major":1,"minor":1},
                                       "producer":"market_data","status":"AVAILABLE"})
        self.assertEqual(result["market_data_snapshot"]["status"],"UNAVAILABLE")
        self.assertFalse(result["trading_authorized"])
if __name__=="__main__":unittest.main()
