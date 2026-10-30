import unittest
from unified_system.sequence_plan import describe_progress
from unified_system.contracts import ContractError

class SequencePlanTests(unittest.TestCase):
    def test_initial(self):
        result=describe_progress({})
        self.assertEqual(result["stages"][0]["status"],"NOT_STARTED")
        self.assertFalse(result["paper_trading_authorized"])
    def test_research_then_grid(self):
        x=describe_progress({"INFRA_PREFLIGHT":"COMPLETE","INFRA_READY":"COMPLETE",
            "STRAT_PREPARE":"COMPLETE","STRAT_HISTORY_SYNC":"COMPLETE",
            "STRAT_RESEARCH":"COMPLETE","STRAT_RESULT_SEALED":"COMPLETE",
            "HANDOFF_VERIFY":"COMPLETE","GRID_MARKET_READY":"RUNNING"})
        self.assertEqual(x["stages"][7]["status"],"RUNNING")
    def test_block(self):
        with self.assertRaises(ContractError):
            describe_progress({"STRAT_RESEARCH":"BLOCKED","GRID_MARKET_READY":"RUNNING"})
    def test_terminan_remains_available_when_research_blocked(self):
        x=describe_progress({"INFRA_PREFLIGHT":"COMPLETE","INFRA_READY":"COMPLETE",
            "STRAT_RESEARCH":"BLOCKED","TERMINAN_OBSERVING":"RUNNING"})
        self.assertEqual(x["stages"][8]["status"],"RUNNING")
        self.assertFalse(x["execution_authorized"])
    def test_terminan_cannot_start_if_infrastructure_blocked(self):
        with self.assertRaises(ContractError):
            describe_progress({"INFRA_READY":"BLOCKED","TERMINAN_OBSERVING":"RUNNING"})
    def test_grid_requires_unblocked_handoff(self):
        with self.assertRaises(ContractError):
            describe_progress({"HANDOFF_VERIFY":"BLOCKED","GRID_MARKET_READY":"RUNNING"})
    def test_unknown(self):
        with self.assertRaises(ContractError):describe_progress({"LIVE_ORDERS":"RUNNING"})
if __name__=="__main__":unittest.main()
