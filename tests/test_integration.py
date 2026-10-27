import tempfile
import unittest
from pathlib import Path
from unified_system.integration import synthetic_pipeline
from unified_system.contracts import ContractError

class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/"journal.db"
    def test_full_offline(self):
        result=synthetic_pipeline(self.path)
        self.assertEqual(result["lifecycle"]["state"],"OBSERVING")
        self.assertEqual(result["dashboard"]["overall"],"SYNTHETIC_READY")
        self.assertFalse(result["terminan_connected"])
    def test_missing_grid(self):
        result=synthetic_pipeline(self.path,modules=("strattester","terminan"))
        self.assertEqual(result["lifecycle"]["state"],"DEGRADED")
        self.assertEqual(result["dashboard"]["overall"],"DEGRADED")
    def test_restart_blocked(self):
        synthetic_pipeline(self.path)
        with self.assertRaises(ContractError):synthetic_pipeline(self.path)
if __name__=="__main__":unittest.main()
