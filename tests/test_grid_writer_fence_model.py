"""Pure fail-closed writer-fence transition cases. No PG, files or sockets."""
from dataclasses import replace
import concurrent.futures
import threading
import unittest
import uuid

from unified_system.grid_writer_fence_model import (
    ModelFenceState, ResourceFenceBlocked, WriterLeaseIdentity, SCHEMA,
    claim_model, native_writer_admission, stop_model, write_matches_model,
)


def identity(token=100, *, instance=None, session=None, source="a" * 64,
             schema="b" * 64):
    return WriterLeaseIdentity("root-controller", session or str(uuid.uuid4()),
                               token, instance or str(uuid.uuid4()), source,
                               schema)


class GridWriterFenceModelTests(unittest.TestCase):
    def test_initial_claim_only_with_explicit_model_quiescence(self):
        first = identity()
        with self.assertRaisesRegex(ResourceFenceBlocked, "FENCE_LEGACY_WRITER_UNVERIFIED"):
            claim_model(None, first, legacy_quiescent=False)
        with self.assertRaises(ResourceFenceBlocked):
            claim_model(None, first, legacy_quiescent=None)
        state = claim_model(None, first, legacy_quiescent=True)
        self.assertEqual((state.schema, state.generation, state.active), (SCHEMA, 1, True))
        self.assertTrue(write_matches_model(state, first, 1))

    def test_same_or_lower_consul_token_is_never_reacquired(self):
        first = identity(20)
        stopped = stop_model(claim_model(None, first, legacy_quiescent=True), first)
        for token in (1, 19, 20):
            with self.subTest(token=token):
                with self.assertRaisesRegex(ResourceFenceBlocked, "FENCE_STALE_TOKEN"):
                    claim_model(stopped, identity(token), legacy_quiescent=True)

    def test_crash_restart_requires_explicit_stop_and_higher_token(self):
        first = identity(9)
        state = claim_model(None, first, legacy_quiescent=True)
        successor = identity(10)
        with self.assertRaisesRegex(ResourceFenceBlocked, "FENCE_PREVIOUS_WRITER_ACTIVE"):
            claim_model(state, successor, legacy_quiescent=True)
        state = stop_model(state, first)
        latest = claim_model(state, successor, legacy_quiescent=True)
        self.assertEqual(latest.generation, 2)
        self.assertFalse(write_matches_model(latest, first, 1))
        self.assertFalse(write_matches_model(latest, first, 2))
        self.assertTrue(write_matches_model(latest, successor, 2))

    def test_wrong_instance_session_source_or_schema_is_not_current(self):
        original = identity(5)
        active = claim_model(None, original, legacy_quiescent=True)
        different = (replace(original, instance_id=str(uuid.uuid4())),
                     replace(original, session_id=str(uuid.uuid4())),
                     replace(original, source_sha256="f" * 64),
                     replace(original, schema_sha256="e" * 64),
                     replace(original, owner="another-controller"))
        for candidate in different:
            with self.subTest(candidate=candidate):
                self.assertFalse(write_matches_model(active, candidate, 1))
                with self.assertRaisesRegex(ResourceFenceBlocked, "FENCE_STALE_WRITER"):
                    stop_model(active, candidate)

    def test_release_prevents_old_writes_and_cannot_repeat(self):
        original = identity()
        state = claim_model(None, original, legacy_quiescent=True)
        stopped = stop_model(state, original)
        self.assertFalse(write_matches_model(stopped, original, 1))
        with self.assertRaisesRegex(ResourceFenceBlocked, "FENCE_STALE_WRITER"):
            stop_model(stopped, original)

    def test_token_bool_zero_negative_overflow_and_invalid_identity_rejected(self):
        for token in (True, False, 0, -1, 1 << 63, 1.0, "12", None):
            with self.subTest(token=token):
                with self.assertRaises(ResourceFenceBlocked):
                    identity(token)
        for bad in ("", "ABC", "0" * 63, "g" * 64, None):
            with self.subTest(digest=bad):
                with self.assertRaises(ResourceFenceBlocked):
                    identity(source=bad)

    def test_invalid_uuid_and_owner_bounded(self):
        for bad in ("", "not-uuid", str(uuid.uuid1()), str(uuid.uuid4()).upper()):
            with self.subTest(uuid=bad):
                with self.assertRaises(ResourceFenceBlocked):
                    identity(session=bad)
        with self.assertRaises(ResourceFenceBlocked):
            replace(identity(), owner="private/invalid/owner")

    def test_forged_or_mutable_state_rejected(self):
        original = identity(7)
        active = claim_model(None, original, legacy_quiescent=True)
        for change in (dict(schema="unknown"), dict(scope="PRODUCTION"),
                       dict(generation=True), dict(active=1),
                       dict(identity="raw-json")):
            with self.subTest(change=change):
                with self.assertRaises(ResourceFenceBlocked):
                    replace(active, **change)

    def test_generation_is_exact_not_bool_and_must_match(self):
        who = identity()
        state = claim_model(None, who, legacy_quiescent=True)
        for generation in (True, 0, 2, "1", 1.0, None):
            self.assertFalse(write_matches_model(state, who, generation))
        self.assertTrue(write_matches_model(state, who, 1))

    def test_monotone_model_progression_without_token_reuse(self):
        first = identity(1)
        state = claim_model(None, first, legacy_quiescent=True)
        for token in range(2, 102):
            state = stop_model(state, state.identity)
            candidate = identity(token)
            state = claim_model(state, candidate, legacy_quiescent=True)
            self.assertEqual(state.generation, token)
            self.assertTrue(write_matches_model(state, candidate, token))
        self.assertEqual(state.identity.token, 101)

    def test_atomic_db_adapter_contract_race_one_winner_model_only(self):
        # Illustrates required PostgreSQL serialization; it is NOT DB evidence.
        class FakeAtomicStore:
            def __init__(self):
                self.lock = threading.Lock()
                self.current = None
            def try_claim(self, candidate):
                with self.lock:
                    try:
                        self.current = claim_model(self.current, candidate,
                                                   legacy_quiescent=True)
                        return True
                    except ResourceFenceBlocked:
                        return False
        store = FakeAtomicStore()
        contenders = [identity(7) for _ in range(32)]
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            winners = list(pool.map(store.try_claim, contenders))
        self.assertEqual(winners.count(True), 1)
        self.assertEqual(winners.count(False), 31)
        self.assertEqual(store.current.identity.token, 7)

    def test_native_admission_unavailable_even_with_good_model(self):
        who = identity()
        state = claim_model(None, who, legacy_quiescent=True)
        for args in ((), (state,), (state, who)):
            with self.assertRaisesRegex(ResourceFenceBlocked,
                                        "NATIVE_DB_FENCE_NOT_ADMITTED"):
                native_writer_admission(*args)


if __name__ == "__main__":
    unittest.main()
