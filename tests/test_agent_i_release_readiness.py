"""Agent I release readiness contract checks — stdlib only and no native effects.

Run: python -m unittest discover -s tests -p test_agent_i_release_readiness.py -v
Do not interpret model validation as native release acceptance.
"""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "release" / "agent-i" / "round26" / "readiness.json"
AUDIT = ROOT / "docs" / "operations" / "AGENT_I_ROUND26_DEPLOYMENT_AUDIT.md"
CHECKLIST = ROOT / "docs" / "operations" / "AGENT_I_REAL_PC_ACCEPTANCE.md"

class DeploymentReadinessContract(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_no_go_remains_explicit(self):
        self.assertEqual(self.payload["status"], {"code": "NO_GO", "production": "NO_GO"})
        self.assertEqual(self.payload["scope"], "READ_ONLY_SOURCE_AUDIT_AND_PLAN")

    def test_no_physical_action_claims(self):
        self.assertTrue(self.payload["execution"])
        self.assertTrue(all(v == "NOT_RUN" for v in self.payload["execution"].values()))

    def test_required_safety_invariants(self):
        self.assertTrue({
            "no_second_supervisor", "no_second_postgresql_owner", "no_pg_5432",
            "no_user_data_purge", "no_main_merge", "no_pr_166_modification",
            "no_auto_authority_promotion", "no_untrusted_latest_release",
        }.issubset(set(self.payload["invariants"])))

    def test_owner_interfaces_remain_external(self):
        self.assertEqual(self.payload["owners"], {
            "windows": "A", "postgresql": "C", "consul": "E",
            "audit": "F", "retirement": "G", "release": "J",
        })

    def test_checklist_has_all_gates_and_no_pass_bypass(self):
        text = CHECKLIST.read_text(encoding="utf-8")
        for i in range(1, 23):
            self.assertIn(f"I-{i:02d}", text)
        self.assertIn("NOT_RUN", text)
        self.assertIn("UNKNOWN", text)

    def test_audit_identifies_existing_non_actuating_surfaces(self):
        text = AUDIT.read_text(encoding="utf-8")
        for name in (
            "installation_transaction.py", "installation_uninstall.py",
            "node_supervisor_v2.py", "service_postgres.py",
            "UnifiedOwnedServiceRemoval.psm1",
        ):
            self.assertIn(name, text)

if __name__ == "__main__":
    unittest.main()
