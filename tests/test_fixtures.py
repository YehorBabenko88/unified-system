import unittest
from unified_system.fixtures import inspect_source_envelope,PINNED
from unified_system.contracts import ContractError

class PinnedFixtureTests(unittest.TestCase):
    def fixture(self,name):
        return {"api_version":{"major":1,"minor":0},
                "producer":"strattester" if name=="strattester" else "bybit-cluster-grid",
                "read_only":True,"status":"UNAVAILABLE"}
    def test_strattester(self):
        self.assertFalse(inspect_source_envelope("strattester",self.fixture("strattester"),source_sha=PINNED["strattester"])["production_ready"])
    def test_grid(self):
        self.assertEqual(inspect_source_envelope("grid",self.fixture("grid"),source_sha=PINNED["grid"])["source_provenance"],"UNVERIFIED")
    def test_wrong_sha(self):
        with self.assertRaises(ContractError):
            inspect_source_envelope("grid",self.fixture("grid"),source_sha="0"*40)
    def test_false_ready(self):
        x=self.fixture("grid");x["status"]="AVAILABLE"
        with self.assertRaises(ContractError):
            inspect_source_envelope("grid",x,source_sha=PINNED["grid"])
if __name__=="__main__":unittest.main()
