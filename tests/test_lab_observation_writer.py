"""Disposable files and synthetic inputs; never physical/runtime acceptance."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest

from unified_system.lab_observation_writer import assemble, SnapshotWriter, ObservationRejected


def unavailable_validator(value, now):
    # Independent unit seam; actual Term contract is exercised separately below.
    assert value['trading_authorized'] is False
    assert value['authority'] == 'REPORTED_UNATTESTED'
    for section in value['sections'].values():
        if section['state'] != 'UNAVAILABLE':
            assert section['payload'] == []
    return value


class ProducerTests(unittest.TestCase):
    def snapshot(self, **sources):
        return assemble(release_id='release', run_id='run', sequence=1,
                        generated_at_ms=1500, validate=unavailable_validator,
                        sources=sources)

    def test_missing_sources_are_unavailable_not_empty_success(self):
        value = self.snapshot()
        self.assertTrue(all(s == dict(state='UNAVAILABLE', error_code='SOURCE_NOT_CONFIGURED', payload=None)
                            for s in value['sections'].values()))

    def test_available_payload_is_copied_and_failures_do_not_leak(self):
        source = []
        def fail(): raise RuntimeError('private-password/path')
        value = self.snapshot(market=lambda: source, paper=fail)
        source.append('changed')
        self.assertEqual(value['sections']['market']['payload'], [])
        self.assertEqual(value['sections']['paper']['error_code'], 'SOURCE_UNAVAILABLE')
        self.assertNotIn('private', json.dumps(value))

    def test_invalid_payload_has_closed_failure(self):
        value = self.snapshot(market=lambda: {'private': 'secret'})
        self.assertEqual(value['sections']['market'], dict(state='UNAVAILABLE', error_code='VALIDATION_FAILED', payload=None))

    def test_missing_validator_and_unknown_source_fail_closed(self):
        with self.assertRaises(ObservationRejected):
            assemble(release_id='release', run_id='run', sequence=1, generated_at_ms=1500, validate=None, sources={})
        with self.assertRaises(ObservationRejected): self.snapshot(orders=lambda: [])

    def test_nan_cycles_and_oversized_source_rejected_without_mutation(self):
        cycle = []; cycle.append(cycle)
        for payload in ([float('nan')], cycle, ['x'*2100000]):
            self.assertEqual(self.snapshot(market=lambda: payload)['sections']['market']['error_code'], 'VALIDATION_FAILED')

    def test_real_term_validator_roundtrip_when_explicitly_supplied(self):
        root = os.environ.get('UNIFIED_TEST_TERMINAN_ROOT')
        pin = os.environ.get('UNIFIED_TEST_TERMINAN_LAB_SHA256')
        if not root or not pin: self.skipTest('explicit admitted Term checkout and raw source pin not configured')
        path = Path(root)/'terminan'/'lab_view.py'
        raw = path.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), pin)
        # Compile the verified raw bytes, never an ambient cached .pyc.
        import types
        module = types.ModuleType('_admitted_term_lab_test')
        exec(compile(raw, str(path), 'exec'), module.__dict__)
        value = assemble(release_id='release', run_id='run', sequence=1, generated_at_ms=1500,
                         validate=module.validate_v2, sources={'market': lambda: []})
        self.assertEqual(module.validate_v2(value, 1500), value)

    def test_validator_cannot_mutate_reported_values(self):
        def mutating(value, now):
            value['authority'] = 'TRUST_ME'
            value['sections']['market']['payload'].append('injected')
        value = assemble(release_id='release', run_id='run', sequence=1, generated_at_ms=1500,
                         validate=mutating, sources={'market': lambda: []})
        self.assertEqual(value['authority'], 'REPORTED_UNATTESTED')
        self.assertEqual(value['sections']['market']['payload'], [])


class WriterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)/'owned'
        self.writer = SnapshotWriter.create(self.root, release_id='release', run_id='run',
                                            validate=unavailable_validator, require_current=lambda: True)
        self.addCleanup(self.writer.close)

    def publish(self, expected=0):
        return self.writer.publish(expected_sequence=expected, generated_at_ms=1500, sources={})

    def test_atomic_snapshot_cas_and_exact_serialized_reader_input(self):
        first = self.publish(); raw = self.writer.path.read_bytes()
        self.assertEqual(json.loads(raw), first)
        with self.assertRaises(ObservationRejected): self.publish()
        second = self.publish(1); self.assertEqual(second['sequence'], 2)

    def test_concurrent_same_sequence_has_one_winner(self):
        results = []
        barrier = threading.Barrier(3)
        def publish():
            barrier.wait()
            try: self.publish(); results.append('published')
            except ObservationRejected: results.append('rejected')
        threads = [threading.Thread(target=publish) for _ in range(2)]
        for thread in threads: thread.start()
        barrier.wait()
        for thread in threads: thread.join(5); self.assertFalse(thread.is_alive())
        self.assertCountEqual(results, ['published', 'rejected'])

    def test_output_not_visible_while_source_is_running(self):
        entered = threading.Event(); release = threading.Event(); result = []
        def source(): entered.set(); release.wait(5); return []
        thread = threading.Thread(target=lambda: result.append(self.writer.publish(
            expected_sequence=0, generated_at_ms=1500, sources={'market': source})))
        thread.start(); self.assertTrue(entered.wait(5))
        self.assertFalse(self.writer.path.exists())
        release.set(); thread.join(5); self.assertFalse(thread.is_alive())
        self.assertEqual(json.loads(self.writer.path.read_bytes()), result[0])

    def test_revocation_during_export_prevents_publication(self):
        def source(): self.writer.require_current = lambda: False; return []
        with self.assertRaises(ObservationRejected):
            self.writer.publish(expected_sequence=0, generated_at_ms=1500, sources={'market': source})
        self.assertFalse(self.writer.path.exists())

    def test_replaced_lock_file_is_preserved(self):
        lock = self.root/'.writer.lock'
        # Windows may deny removing the owned open handle; refusal is safe too.
        try: lock.unlink()
        except PermissionError: return
        lock.write_text('foreign')
        with self.assertRaises(ObservationRejected): self.publish()
        self.assertEqual(lock.read_text(), 'foreign')

    def test_existing_namespace_never_adopted(self):
        with self.assertRaises(ObservationRejected):
            SnapshotWriter.create(self.root, release_id='release', run_id='run', validate=unavailable_validator, require_current=lambda: True)

    def test_foreign_replacement_preserved_and_writer_blocked(self):
        self.publish(); self.writer.path.unlink(); self.writer.path.write_text('foreign')
        with self.assertRaises(ObservationRejected): self.publish(1)
        self.assertEqual(self.writer.path.read_text(), 'foreign')

    def test_in_place_tamper_and_hardlinks_rejected(self):
        self.publish(); original = self.writer.path.read_bytes()
        self.writer.path.write_bytes(original+b' ')
        with self.assertRaises(ObservationRejected): self.publish(1)

    def test_hardlink_prevents_update(self):
        self.publish(); other = Path(self.temp.name)/'link'
        os.link(self.writer.path, other)
        with self.assertRaises(ObservationRejected): self.publish(1)

    def test_revoked_and_closed_writer_have_no_new_side_effects(self):
        self.writer.require_current = lambda: False
        before = set(self.root.iterdir())
        with self.assertRaises(ObservationRejected): self.publish()
        self.assertEqual(set(self.root.iterdir()), before)
        self.writer.close()
        with self.assertRaises(ObservationRejected): self.publish()

    def test_symlink_parent_rejected_before_directory_creation(self):
        link = Path(self.temp.name)/'redirect'
        try: link.symlink_to(self.root, target_is_directory=True)
        except OSError: self.skipTest('symlink privilege unavailable')
        with self.assertRaises(ObservationRejected):
            SnapshotWriter.create(link/'new', release_id='release', run_id='run', validate=unavailable_validator, require_current=lambda: True)
        self.assertFalse((self.root/'new').exists())


if __name__ == '__main__': unittest.main()
