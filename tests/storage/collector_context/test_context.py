"""Actual bounded private-state component tests; no network/PG/service/loop."""
import dataclasses
import importlib
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from unified_system.journal import Journal
from unified_system.storage.raw_capture import RawCaptureProfile, RawCaptureAdapter


def complete(coro):
    try:
        try: coro.send(None)
        except StopIteration as done: return done.value
        raise AssertionError('unexpected suspension')
    finally: coro.close()


class CollectorContextTests(unittest.TestCase):
    def setUp(self):
        try: self.api = importlib.import_module('unified_system.storage.collector_context')
        except ModuleNotFoundError: self.fail('collector context is missing')
        self.parent = Path(os.environ['A4_CONTEXT_TEST_SCRATCH']) / self._testMethodName
        self.parent.mkdir(exist_ok=False)
        self.root = self.parent / 'context'
        self.profile = self.api.CollectorContextProfile(
            raw_profile=RawCaptureProfile(sqlite_headroom_bytes=262144, inventory_file_limit=128),
            lifecycle_headroom_bytes=65536)
        self.kw = dict(context_id='1'*32, store_id='96dce424-a40b-4f25-8500-26738dd278e5',
                       binding_sha256='a'*64, profile=self.profile)
        self.ctx = self.api.CollectorContext.create(self.root, **self.kw)

    def tearDown(self):
        if hasattr(self, 'ctx'): self.ctx.close()

    def store(self, obs=b'observation', payload=b'raw'):
        return complete(self.ctx.store_capture(observation_bytes=obs, payload_bytes=payload))

    def reopen(self):
        self.ctx = self.api.CollectorContext.open(self.root, **self.kw)
        return self.ctx

    def test_actual_capture_checkpoint_and_readback(self):
        facts = self.store()
        checkpoint = complete(self.ctx.checkpoint())
        self.assertEqual(checkpoint.observation_sha256, facts.observation_sha256)
        self.assertEqual(checkpoint.raw_journal_digest, facts.journal_record_digest)
        self.assertEqual(checkpoint.native_outcome, 'UNKNOWN')
        self.assertEqual(complete(self.ctx.read_capture(facts.observation_sha256)), facts)
        self.assertFalse(checkpoint.publication_confirmed)

    def test_gap_observation_bytes_survive_without_completeness_claim(self):
        raw = b'{"kind":"gap_observation","reason":"frame_invalid"}'
        self.store(raw, None)
        history = complete(self.ctx.read_history())
        self.assertEqual(history[0].observation_bytes, raw)
        self.assertIsNone(history[0].payload_bytes)
        self.assertEqual(self.ctx.status().provider_continuity, 'UNKNOWN')

    def test_old_idempotent_replay_does_not_rewind_checkpoint(self):
        first = self.store(b'first', b'a')
        self.store(b'second', b'b')
        before = complete(self.ctx.checkpoint())
        rows_before = Journal(self.root/'lifecycle.sqlite').read()
        self.assertEqual(self.store(b'first', b'a'), first)
        self.assertEqual(complete(self.ctx.checkpoint()), before)
        self.assertEqual(Journal(self.root/'lifecycle.sqlite').read(), rows_before)

    def test_second_writer_is_refused_by_owned_file_lock(self):
        with self.assertRaisesRegex(self.api.CollectorBlocked, 'COLLECTOR_WRITER_BUSY'):
            self.api.CollectorContext.open(self.root, **self.kw)
        self.ctx.require_ready()
        self.store()

    def test_conflicting_replay_persists_unknown(self):
        first = self.store(b'first', b'a')
        checkpoint = complete(self.ctx.checkpoint())
        with self.assertRaises(Exception): self.store(b'first', b'b')
        self.assertEqual(self.ctx.status().state, 'UNKNOWN')
        with self.assertRaises(self.api.CollectorBlocked): self.store(b'new', None)
        self.ctx.close()
        self.assertEqual(self.reopen().status().state, 'UNKNOWN')
        self.assertEqual(complete(self.ctx.checkpoint()), checkpoint)
        self.assertEqual(complete(self.ctx.read_history()), (first,))

    def test_exhausted_clean_journal_reopens_read_only(self):
        # Valid capacity-edge journal fixture bypasses normal admission reserve.
        for _ in range(63):
            self.ctx._event('STOPPED', reason='fixture_cycle')
            self.ctx._event('OPEN')
        complete(self.ctx.stop()); self.ctx.close()
        self.assertEqual(len(Journal(self.root/'lifecycle.sqlite').read()), 128)
        self.assertEqual(self.reopen().status().state, 'UNKNOWN')
        self.assertEqual(complete(self.ctx.read_history()), ())
        with self.assertRaises(self.api.CollectorBlocked): self.ctx.require_ready()
        self.ctx.close()
        self.assertEqual(self.reopen().status().state, 'UNKNOWN')

    def test_clean_stop_close_and_reopen_preserves_counters(self):
        facts = self.store()
        checkpoint = complete(self.ctx.checkpoint())
        self.assertEqual(complete(self.ctx.stop()).state, 'STOPPED')
        self.ctx.close()
        self.reopen().require_ready()
        self.assertEqual(complete(self.ctx.checkpoint()), checkpoint)
        self.assertEqual(complete(self.ctx.read_history()), (facts,))
        self.store(b'new', None)
        self.assertEqual(len(complete(self.ctx.read_history())), 2)

    def test_dirty_close_is_persistent_unknown_not_new_writable_pool(self):
        facts = self.store()
        self.ctx.close()
        self.assertEqual(self.reopen().status().state, 'UNKNOWN')
        with self.assertRaises(self.api.CollectorBlocked): self.store(b'new', None)
        self.assertEqual(complete(self.ctx.read_capture(facts.observation_sha256)), facts)

    def test_terminal_state_survives_new_instance(self):
        self.store()
        complete(self.ctx.mark_terminal('source_failed'))
        self.ctx.close()
        self.assertEqual(self.reopen().status().state, 'TERMINAL')
        with self.assertRaises(self.api.CollectorBlocked): self.ctx.require_ready()

    def test_raw_error_persists_unknown_with_last_checkpoint_retained(self):
        self.store()
        checkpoint = complete(self.ctx.checkpoint())
        async def failed(*_a, **_k): raise OSError('synthetic pre-store error')
        with patch.object(RawCaptureAdapter, 'store_capture', failed):
            with self.assertRaises(OSError): self.store(b'uncertain', b'next')
        self.ctx.close()
        self.assertEqual(self.reopen().status().state, 'UNKNOWN')
        self.assertEqual(complete(self.ctx.checkpoint()), checkpoint)
        self.assertEqual(len(complete(self.ctx.read_history())), 1)

    def test_lifecycle_response_loss_keeps_unknown_after_raw_link(self):
        original = Journal.append
        def response_lost(journal, state, receipt=None, **kwargs):
            result = original(journal, state, receipt, **kwargs)
            if journal.path == self.root/'lifecycle.sqlite' and receipt['event'] == 'CHECKPOINT':
                raise OSError('synthetic lifecycle response loss')
            return result
        with patch.object(Journal, 'append', response_lost):
            with self.assertRaises(OSError): self.store()
        self.ctx.close()
        self.assertEqual(self.reopen().status().state, 'UNKNOWN')
        self.assertEqual(len(complete(self.ctx.read_history())), 1)

    def test_profile_and_binding_cannot_change_on_reopen(self):
        complete(self.ctx.stop()); self.ctx.close()
        changed = dict(self.kw, binding_sha256='b'*64)
        with self.assertRaises(self.api.CollectorBlocked):
            self.api.CollectorContext.open(self.root, **changed)
        changed = dict(self.kw, profile=dataclasses.replace(self.profile, max_lifecycle_records=64))
        with self.assertRaises(self.api.CollectorBlocked):
            self.api.CollectorContext.open(self.root, **changed)
        self.reopen().require_ready()

    def test_stop_response_loss_and_unknown_append_failure_cannot_resume(self):
        facts = self.store()
        original = Journal.append
        def uncertain(journal, state, receipt=None, **kwargs):
            if journal.path == self.root/'lifecycle.sqlite':
                if receipt['event'] == 'UNKNOWN':
                    raise OSError('synthetic unknown append unavailable')
                result = original(journal, state, receipt, **kwargs)
                if receipt['event'] == 'STOPPED':
                    raise OSError('synthetic stop response lost')
                return result
            return original(journal, state, receipt, **kwargs)
        with patch.object(Journal, 'append', uncertain):
            with self.assertRaises(BaseExceptionGroup): complete(self.ctx.stop())
        self.ctx.close()
        self.assertEqual(self.reopen().status().state, 'UNKNOWN')
        with self.assertRaises(self.api.CollectorBlocked): self.ctx.require_ready()
        self.assertEqual(complete(self.ctx.read_history()), (facts,))

    def test_explicit_headroom_required_before_root_creation(self):
        target = self.parent/'invalid'
        changed = dict(self.kw, profile=dataclasses.replace(self.profile, lifecycle_headroom_bytes=True))
        with self.assertRaises(self.api.CollectorBlocked): self.api.CollectorContext.create(target, **changed)
        self.assertFalse(target.exists())

    def test_close_refuses_inflight_and_keeps_writer_owned(self):
        self.ctx._busy.acquire()
        try:
            with self.assertRaisesRegex(self.api.CollectorBlocked, 'COLLECTOR_IO_INFLIGHT'): self.ctx.close()
            with self.assertRaises(self.api.CollectorBlocked): self.api.CollectorContext.open(self.root, **self.kw)
        finally: self.ctx._busy.release()

    def test_unknown_context_file_refuses_new_capture(self):
        (self.root/'unaccounted').write_bytes(b'own-extra-fixture')
        with self.assertRaises(self.api.CollectorBlocked): self.ctx.require_ready()

    def test_context_id_is_exact_32_lower_hex_without_alias_conversion(self):
        changed = dict(self.kw, context_id=self.kw['store_id'])
        with self.assertRaises(self.api.CollectorBlocked):
            self.api.CollectorContext.create(self.parent/'wrong-id', **changed)


if __name__ == '__main__': unittest.main(verbosity=2)
