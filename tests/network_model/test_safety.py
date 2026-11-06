"""Independent MODEL_ONLY invariants. No production transport is imported."""
import json
import tempfile
import unittest
from pathlib import Path

from model import Bucket, Packet, Simulator, QuotaLedger


class BandwidthModelTests(unittest.TestCase):
    def test_exact_token_boundary_and_no_backward_clock(self):
        b = Bucket(100, 20)
        self.assertTrue(b.take(0, 20))
        self.assertFalse(b.take(99, 10))
        self.assertTrue(b.take(100, 10))
        with self.assertRaises(ValueError):
            b.take(99, 1)

    def test_class_denial_does_not_debit_node_or_cluster(self):
        s = Simulator()
        # Bulk burst is 300 of the 1000-byte node burst.
        s.enqueue(Packet('b', 'PC1', 'bulk', 301, 'I0'))
        s.step(0)
        self.assertEqual(s.attempts, [])
        s.enqueue(Packet('c', 'PC1', 'control', 200, 'I0'))
        s.step(0)
        self.assertEqual([x['packet_id'] for x in s.attempts], ['c'])
        self.assertEqual(s.nodes['PC1'].bucket.available(0), 800)
        self.assertEqual(s.cluster.available(0), 5800)

    def test_control_precedes_bulk_and_queue_backpressure_is_explicit(self):
        s = Simulator(max_queue_bytes=300, max_queue_packets=3)
        for ident, cls in [('b', 'bulk'), ('l', 'live'), ('c', 'control')]:
            self.assertTrue(s.enqueue(Packet(ident, 'PC1', cls, 100, 'I0')))
        self.assertFalse(s.enqueue(Packet('overflow', 'PC1', 'live', 1, 'I0')))
        s.step(0)
        self.assertEqual([x['packet_id'] for x in s.attempts], ['c'])
        self.assertEqual(s.rejected, 1)
        self.assertLessEqual(s.nodes['PC1'].queued_bytes, 300)

    def test_loss_charges_attempt_and_retry_is_not_automatic(self):
        s = Simulator(loss_every=1, latency_ms=20)
        s.enqueue(Packet('p', 'PC1', 'live', 100, 'I0'))
        s.step(0)
        self.assertEqual(s.cluster.available(0), 5900)
        self.assertEqual(s.nodes['PC1'].bucket.available(0), 900)
        s.step(100)
        self.assertEqual(len(s.attempts), 1)
        self.assertEqual(len(s.lost), 1)
        self.assertEqual(s.delivered, [])
        self.assertEqual(s.cluster.available(0 + 100), 6000)
        self.assertEqual(s.attempts[0]['size'], 100)

    def test_ls5_loss_keeps_static_allocations_and_restart_starts_empty(self):
        s = Simulator()
        s.fail_node('LS5')
        self.assertEqual([s.nodes[n].ceiling for n in ('PC1', 'PC2', 'PC3', 'PC4', 'LS7')], [1000] * 5)
        s.restart_node('LS5', 0)
        self.assertEqual(s.nodes['LS5'].bucket.available(0), 0)
        self.assertEqual(s.nodes['LS5'].bucket.rate, 100)
        s.recover('LS5', 100)
        self.assertEqual(s.nodes['LS5'].bucket.rate, 200)
        s.recover('LS5', 100)
        self.assertEqual(s.nodes['LS5'].bucket.rate, 200)
        s.recover('LS5', 10000)
        self.assertEqual(s.nodes['LS5'].bucket.rate, 1000)

    def test_recovery_does_not_retroactively_refill_at_new_rate(self):
        s = Simulator()
        s.restart_node('LS5', 0)
        s.recover('LS5', 100)
        self.assertEqual(s.nodes['LS5'].bucket.available(100), 10)

    def test_surviving_nodes_keep_progress_in_all_three_classes(self):
        s = Simulator()
        s.fail_node('LS5')
        for i in range(10):
            for cls in ('control', 'live', 'bulk'):
                s.enqueue(Packet(f'{i}:{cls}', 'PC1', cls, 100, 'I0'))
        # 1000 control bytes need 200 burst + 4s * 200 bytes/s.
        for tick in range(0, 4001, 10):
            s.step(tick)
        self.assertEqual({x['traffic_class'] for x in s.attempts}, {'control', 'live', 'bulk'})
        self.assertEqual(len(s.attempts), 30)

    def test_invalid_boolean_sizes_and_duplicate_ids_do_not_grow_queue(self):
        s = Simulator()
        with self.assertRaises(ValueError):
            s.enqueue(Packet('bad', 'PC1', 'live', True, 'I0'))
        self.assertTrue(s.enqueue(Packet('same', 'PC1', 'live', 100, 'I0')))
        self.assertFalse(s.enqueue(Packet('same', 'PC1', 'live', 100, 'I0')))
        self.assertEqual(s.nodes['PC1'].queued_bytes, 100)

    def test_six_nodes_ten_instruments_interval_oracle_and_bounded_loss(self):
        s = Simulator(seed=41, latency_ms=30, jitter_ms=10, loss_every=7)
        for tick in range(0, 2001, 10):
            if tick % 100 == 0:
                for node in s.nodes:
                    for instrument in range(10):
                        cls = 'control' if instrument == 0 else ('live' if instrument % 2 else 'bulk')
                        s.enqueue(Packet(f'{tick}:{node}:{instrument}', node, cls, 100, f'I{instrument}'))
            if tick == 500:
                s.fail_node('LS5')
            s.step(tick)
        for node in s.nodes:
            a = [x for x in s.attempts if x['node'] == node]
            for start in range(0, 2001, 100):
                for end in range(start, 2001, 100):
                    spent = sum(x['size'] for x in a if start <= x['at_ms'] <= end)
                    self.assertLessEqual(spent, 1000 + (end - start))
        for start in range(0, 2001, 100):
            spent = sum(x['size'] for x in s.attempts if start <= x['at_ms'] <= 2000)
            self.assertLessEqual(spent, 6000 + 6 * (2000 - start))
        self.assertTrue(s.delivered)
        self.assertTrue(s.lost)
        self.assertTrue(s.rejected)
        self.assertFalse(any(x['node'] == 'LS5' and x['at_ms'] >= 500 for x in s.attempts))
        self.assertLessEqual(max(s.peak_queue_bytes.values()), s.max_queue_bytes)
        self.assertTrue(all(30 <= x['delivered_at_ms'] - x['at_ms'] <= 40 for x in s.delivered))
        self.assertEqual({x['instrument'] for x in s.attempts}, {f'I{i}' for i in range(10)})


class PersistentQuotaModelTests(unittest.TestCase):
    def test_shared_nat_limit_not_full_budget_per_node(self):
        q = QuotaLedger(limit=10)
        for i in range(10):
            self.assertEqual(q.reserve(f'a{i}', f'node{i % 6}', 'nat1', 0), 'RESERVED')
        self.assertEqual(q.reserve('extra', 'LS7', 'nat1', 0), 'DENIED')
        self.assertEqual(q.reserve('a0', 'node0', 'nat1', 0), 'RESERVED')
        self.assertEqual(len(q.attempts), 10)

    def test_unknown_freezes_future_windows_restart_and_failover(self):
        q = QuotaLedger(limit=10)
        q.reserve('a', 'PC1', 'nat1', 0)
        self.assertEqual(q.consume('a', 0), 'CHARGED')
        q.mark_unknown('a')
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'model-state.json'
            q.save(p)
            restored = QuotaLedger.load(p)
            restored.failover()
            self.assertEqual(restored.reserve('b', 'PC2', 'nat1', 100000), 'DENIED')
            self.assertEqual(restored.consume('a', 100000), 'UNKNOWN')
            self.assertEqual(len(restored.attempts), 1)
            self.assertIn('nat1', restored.frozen)

    def test_cooldown_survives_restart_and_clock_rollback_denies(self):
        q = QuotaLedger(limit=10)
        q.cooldown('nat1', 1000)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'state.json'
            q.save(p)
            q = QuotaLedger.load(p)
            self.assertEqual(q.reserve('a', 'PC1', 'nat1', 999), 'DENIED')
            self.assertEqual(q.reserve('b', 'PC1', 'nat1', 1000), 'RESERVED')
            self.assertEqual(q.reserve('c', 'PC1', 'nat1', 999), 'DENIED')
            self.assertTrue(q.blocked)

    def test_closed_gate_or_no_quorum_unknown_egress_cannot_grant(self):
        for field in ('quorum', 'gate_open'):
            q = QuotaLedger(limit=10)
            setattr(q, field, False)
            self.assertEqual(q.reserve('a', 'PC1', 'nat1', 0), 'DENIED')
        self.assertEqual(QuotaLedger(limit=10).reserve('a', 'PC1', 'unknown', 0), 'DENIED')

    def test_unknown_never_refunded_or_second_send_permission(self):
        q = QuotaLedger(limit=1)
        q.reserve('a', 'PC1', 'nat1', 0)
        self.assertEqual(q.consume('a', 0), 'CHARGED')
        self.assertEqual(q.consume('a', 0), 'HISTORICAL')
        q.mark_unknown('a')
        self.assertFalse(q.cancel('a'))
        self.assertEqual(q.reserve('retry', 'PC1', 'nat1', 2000), 'DENIED')

    def test_corrupt_state_denies_instead_of_empty_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'state.json'
            p.write_text('{"unexpected":true}', encoding='utf-8')
            q = QuotaLedger.load(p)
            self.assertTrue(q.blocked)
            self.assertEqual(q.reserve('a', 'PC1', 'nat1', 0), 'DENIED')

    def test_validly_hashed_malformed_checkpoint_still_denies(self):
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'state.json'
            q = QuotaLedger()
            q.save(p)
            envelope = json.loads(p.read_text())
            envelope['body']['frozen'] = {'not': 'a list'}
            raw = json.dumps(envelope['body'], sort_keys=True, separators=(',', ':')).encode('ascii')
            envelope['sha256'] = hashlib.sha256(raw).hexdigest()
            p.write_text(json.dumps(envelope), encoding='ascii')
            self.assertTrue(QuotaLedger.load(p).blocked)

    def test_cancelled_attempt_cannot_become_historical_acquire_success(self):
        q = QuotaLedger(limit=1)
        q.reserve('a', 'PC1', 'nat1', 0)
        self.assertTrue(q.cancel('a'))
        self.assertEqual(q.reserve('a', 'PC1', 'nat1', 0), 'DENIED')
        self.assertEqual(q.reserve('new', 'PC2', 'nat1', 0), 'RESERVED')

    def test_closed_gate_blocks_refund_of_unconsumed_reservation(self):
        q = QuotaLedger(limit=1)
        q.reserve('a', 'PC1', 'nat1', 0)
        q.gate_open = False
        self.assertFalse(q.cancel('a'))
        self.assertEqual(q.attempts['a']['state'], 'RESERVED')

    def test_deep_checkpoint_parser_failure_returns_blocked_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'state.json'
            p.write_text('[' * 100000 + '0' + ']' * 100000, encoding='ascii')
            self.assertTrue(QuotaLedger.load(p).blocked)

    def test_frozen_scope_container_must_be_a_list_not_a_dict(self):
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'state.json'
            QuotaLedger().save(p)
            e = json.loads(p.read_text())
            e['body']['frozen'] = {'nat1': False}
            raw = json.dumps(e['body'], sort_keys=True, separators=(',', ':')).encode('ascii')
            e['sha256'] = hashlib.sha256(raw).hexdigest()
            p.write_text(json.dumps(e), encoding='ascii')
            self.assertTrue(QuotaLedger.load(p).blocked)

    def test_unfrozen_reserved_and_charged_debt_survives_windows_restart_failover(self):
        for consume in (False, True):
            with self.subTest(consume=consume), tempfile.TemporaryDirectory() as tmp:
                q = QuotaLedger(limit=1)
                q.reserve('old', 'PC1', 'nat1', 0)
                if consume:
                    q.consume('old', 0)
                p = Path(tmp) / 'state.json'
                q.save(p)
                q = QuotaLedger.load(p)
                self.assertFalse(q.frozen)
                q.failover()
                self.assertEqual(q.reserve('new', 'PC2', 'nat1', 100000), 'DENIED')


if __name__ == '__main__':
    unittest.main()
