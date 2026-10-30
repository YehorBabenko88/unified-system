"""Regression: infrastructure APIs are non-authorizing by default."""
import unittest
from unified_system.fleet_policy import plan_placement
from unified_system.sequence_plan import describe_progress

class WorkstreamOwnership(unittest.TestCase):
    def test_never_authorize_without_quorum(self):
        self.assertFalse(plan_placement([],[],1800000000000)["execution_authorized"])
    def test_sequence_excludes_trading_authority(self):
        result=describe_progress({"INFRA_PREFLIGHT":"COMPLETE"})
        self.assertFalse(result["execution_authorized"])
        self.assertFalse(result["trading_authorized"])
        self.assertFalse(result["paper_trading_authorized"])

if __name__=="__main__":
    unittest.main()
