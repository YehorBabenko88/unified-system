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
    def test_unknown(self):
        with self.assertRaises(ContractError):describe_progress({"LIVE_ORDERS":"RUNNING"})
if __name__=="__main__":unittest.main()
