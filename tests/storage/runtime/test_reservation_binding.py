"""RED design fixtures ONLY; proposed local adapter model, not a native wire.

Run with repository on PYTHONPATH after the exact owned module is allocated.
These tests intentionally do not supply a fake successful authority provider.
No current A2 producer/API or schema compatibility is asserted.
"""
from copy import deepcopy
import unittest

from unified_system.storage.budgets import validate_reservation_binding
from unified_system.storage.contracts import StorageBlocked


class ReservationBindingProposal(unittest.TestCase):
    def facts(self):
        return dict(
            issuance=dict(reservation_id="00000000-0000-4000-8000-000000000001",
                          scope_sha256="a"*64, grant_sha256="b"*64,
                          issuance_budget_revision="17", policy_revision="23", granted_bytes="1024"),
            current=dict(reservation_revision="3", state="RESERVED", remaining_bytes="512",
                         issuance_sha256="c"*64, delegation_sha256="d"*64),
            accounting=dict(usage_revision="9", used_bytes="100", reserved_bytes="512", limit_bytes="4096"),
            requested_bytes="128")

    def test_local_binding_observation_never_grants_publication(self):
        result = validate_reservation_binding(self.facts())
        self.assertFalse(result.publication_authorized)
        self.assertFalse(result.native_proof_verified)

    def test_unrelated_accounting_churn_does_not_rewrite_issuance(self):
        facts = self.facts()
        before = deepcopy(facts)
        validate_reservation_binding(facts)
        facts["accounting"]["usage_revision"] = "10"
        facts["accounting"]["used_bytes"] = "200"
        validate_reservation_binding(facts)
        self.assertEqual(facts["issuance"], before["issuance"])

    def test_own_revocation_or_exhaustion_denies(self):
        for change in ({"state": "REVOKED"}, {"remaining_bytes": "0"}):
            facts = self.facts()
            facts["current"].update(change)
            with self.subTest(change=change), self.assertRaises(StorageBlocked):
                validate_reservation_binding(facts)

    def test_counter_domains_remain_distinct_and_no_numeric_coercion(self):
        for value in (True, 17, "017", "9223372036854775808"):
            facts = self.facts()
            facts["issuance"]["issuance_budget_revision"] = value
            with self.subTest(value=value), self.assertRaises(StorageBlocked):
                validate_reservation_binding(facts)


if __name__ == "__main__":
    unittest.main(verbosity=2)
