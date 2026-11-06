from dataclasses import replace
import unittest

from unified_system.storage.contracts import StorageBlocked
from unified_system.storage.retention import ReplicaClaim, RetentionFacts, plan_retention
from unified_system.storage.segments import verify_segment_bytes
from .test_segments import ROW, claim


def facts(**changes):
    checked = verify_segment_bytes(ROW, claim())
    replicas = tuple(ReplicaClaim(f"r{n}", f"node{n}", f"volume{n}", checked, True) for n in range(3))
    values = dict(object_sha256=claim().sha256, target_replica_id="r0", replicas=replicas,
                  min_survivors=2, age_eligible=True, closure_complete=True,
                  research_pins=(), dependency_pins=(), unresolved_gaps=(), active_upload=False)
    values.update(changes)
    return RetentionFacts(**values)


class RetentionTests(unittest.TestCase):
    def test_candidate_is_never_an_executable_delete_permission(self):
        result = plan_retention(facts())
        self.assertEqual(result.decision, "QUARANTINE_CANDIDATE")
        self.assertEqual(result.byte_matched_survivor_claims, 2)
        self.assertFalse(result.executable)
        self.assertIn("ACTUAL_AUTHORITY_PROOF_UNAVAILABLE", result.reasons)

    def test_last_copy_and_missing_verified_survivors_are_retained(self):
        base = facts()
        for remaining in (base.replicas[:1], base.replicas[:2]):
            with self.subTest(count=len(remaining)):
                result = plan_retention(replace(base, replicas=remaining))
                self.assertEqual(result.decision, "KEEP")
                self.assertIn("LAST_COPY_OR_POLICY_PROTECTED", result.reasons)

    def test_pins_and_unknown_closure_cannot_be_waived_by_age(self):
        for changes, reason in (({"research_pins": ("research-active",)}, "ACTIVE_RESEARCH_PIN"),
                                ({"dependency_pins": ("derived-input",)}, "DEPENDENCY_PIN"),
                                ({"closure_complete": False}, "CLOSURE_UNKNOWN"),
                                ({"unresolved_gaps": ("source-gap",)}, "UNRESOLVED_GAPS"),
                                ({"active_upload": True}, "ACTIVE_UPLOAD"),
                                ({"age_eligible": False}, "RETENTION_NOT_ELAPSED")):
            with self.subTest(changes=changes):
                result = plan_retention(facts(**changes))
                self.assertEqual(result.decision, "KEEP")
                self.assertIn(reason, result.reasons)

    def test_file_exists_or_unavailable_or_wrong_hash_does_not_count(self):
        base = facts()
        other = verify_segment_bytes(ROW.replace(b'BTCUSDT', b'ETHUSDT'), claim(ROW.replace(b'BTCUSDT', b'ETHUSDT'), instrument={"exchange":"bybit","category":"linear","symbol":"ETHUSDT","instrument_version":"1"}))
        for survivor in (replace(base.replicas[2], byte_check=None),
                         replace(base.replicas[2], available=False),
                         replace(base.replicas[2], byte_check=other)):
            with self.subTest(survivor=survivor):
                self.assertEqual(plan_retention(replace(base, replicas=base.replicas[:2]+(survivor,))).decision, "KEEP")

    def test_same_node_or_volume_cannot_supply_independent_survivors(self):
        base = facts()
        for alias in (replace(base.replicas[2], node_id="node1"), replace(base.replicas[2], volume_id="volume1")):
            result = plan_retention(replace(base, replicas=base.replicas[:2]+(alias,)))
            self.assertEqual(result.decision, "KEEP")

    def test_duplicate_identity_and_bool_budget_and_mutable_pin_inputs_reject(self):
        base = facts()
        for changes in ({"replicas": base.replicas+(base.replicas[1],)}, {"min_survivors": True},
                        {"research_pins": ["mutable"]}, {"closure_complete": "true"}):
            with self.subTest(changes=changes), self.assertRaises(StorageBlocked):
                plan_retention(facts(**changes))

    def test_unknown_target_never_becomes_candidate(self):
        result = plan_retention(facts(target_replica_id="absent"))
        self.assertEqual(result.decision, "KEEP")
        self.assertIn("TARGET_UNKNOWN", result.reasons)
