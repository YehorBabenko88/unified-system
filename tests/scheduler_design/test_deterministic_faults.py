"""Hand-authored counterexamples for a trace oracle, not live authority acceptance."""
import copy
from datetime import datetime
import unittest
from tests.scheduler_design.trace_audit import audit, active_at, admission

def event(**changes):
    e = dict(op='publish', time=50, quorum=True, state='ACTIVE',
             assignment_revision=2, current_revision=2, epoch=8, current_epoch=8,
             incarnation='process-b', current_incarnation='process-b',
             generation='g2', current_generation='g2',
             grant_revision=1, current_grant_revision=1,
             lease_expiry=100, reservation_expiry=90,
             budget_revision=3, current_budget_revision=3,
             segment='segment1', digest='digest1', request_id='request1',
             bytes=10, remaining_bytes=100, checkpoint=1, next_checkpoint=2,
             effect=True)
    e.update(changes)
    return e

class FaultTraceTests(unittest.TestCase):
    def rejects(self, reason, **changes):
        self.assertIn(reason, audit([event(**changes)]))

    def test_stale_worker(self):
        self.rejects('STALE_ASSIGNMENT', assignment_revision=1)
        self.assertEqual([], audit([event(assignment_revision=1, effect=False)]))

    def test_lease_expiry_half_open(self):
        self.rejects('LEASE_EXPIRED', time=100)
        self.assertEqual([], audit([event(time=89)]))

    def test_reservation_expiry_half_open(self):
        self.rejects('RESERVATION_EXPIRED', time=90)

    def test_incarnation_change(self):
        self.rejects('INCARNATION_MISMATCH', incarnation='process-a')

    def test_no_quorum_for_mutations(self):
        for op in ('grant', 'renew', 'supersede', 'cancel', 'publish'):
            with self.subTest(op=op):
                self.rejects('NO_QUORUM', op=op, quorum=False)

    def test_budget_and_resource_exhaustion(self):
        self.rejects('STORAGE_BUDGET_CHANGED', budget_revision=2)
        self.rejects('RESERVATION_EXHAUSTED', bytes=101)

    def test_terminal_and_renewed_grant(self):
        self.rejects('TERMINAL_ASSIGNMENT', state='COMPLETED')
        self.rejects('STALE_GRANT', current_grant_revision=2)

    def test_draining_blocks_new_batches_and_excess_bytes(self):
        self.rejects('BATCH_NOT_PERMITTED', state='DRAINING', batch_id='new', permitted_batches=['old'], drain_remaining=20)
        self.rejects('DRAIN_EXHAUSTED', state='DRAINING', batch_id='old', permitted_batches=['old'], drain_remaining=9)
        self.assertEqual([], audit([event(state='DRAINING', batch_id='old', permitted_batches=['old'], drain_remaining=10)]))

    def test_both_serial_orders(self):
        # Snapshot taken inside the actual commit boundary: valid old publication
        # before supersession, and stale old publication after it.
        self.assertEqual([], audit([event(current_revision=2), event(
            op='supersede', assignment_revision=3, current_revision=2, epoch=9)]))
        self.assertEqual([], audit([event(op='supersede', assignment_revision=3,
            current_revision=2, epoch=9), event(current_revision=3, effect=False)]))
        self.assertIn('STALE_ASSIGNMENT', audit([event(op='supersede',
            assignment_revision=3, current_revision=2, epoch=9), event(current_revision=3)]))

    def test_monotonicity_survives_restart(self):
        first = event(op='grant', assignment_revision=3, current_revision=2, epoch=9)
        restarted = event(op='grant', assignment_revision=2, current_revision=1, epoch=8)
        self.assertIn('REVISION_REUSED', audit([first, dict(op='restart'), restarted]))

    def test_checkpoint_recovery(self):
        self.assertEqual([], audit([event(), dict(op='resume', checkpoint=2, verified=True)]))
        self.assertIn('UNCOMMITTED_CHECKPOINT', audit([event(),
            dict(op='resume', checkpoint=3, verified=True)]))
        self.assertIn('UNVERIFIED_CHECKPOINT', audit([event(),
            dict(op='resume', checkpoint=2, verified=False)]))

    def test_duplicate_segment_never_double_debits(self):
        self.assertIn('DUPLICATE_EFFECT', audit([event(), event(request_id='request2')]))
        self.assertEqual([], audit([event(), event(effect=False)]))

    def test_generation_and_suspended_precheck(self):
        self.rejects('GENERATION_MISMATCH', generation='g1')
        # time is authority time at linearization, not an earlier successful precheck.
        self.rejects('LEASE_EXPIRED', precheck_time=50, time=101)

class IndependentPolicyTests(unittest.TestCase):
    def test_capacity_staleness_and_exhaustion(self):
        self.assertEqual('CAPACITY_STALE', admission(100, 89, 10, 100, 0, 1))
        self.assertEqual('CAPACITY_FUTURE', admission(100, 101, 10, 100, 0, 1))
        self.assertEqual('QUEUED_RESOURCES', admission(100, 90, 10, 100, 90, 11))
        self.assertEqual('ADMIT_CANDIDATE', admission(100, 90, 10, 100, 90, 10))
        self.assertEqual('UNHEALTHY', admission(100, 90, 10, 100, 0, 1, healthy=False))

    def test_cross_midnight_schedule_start_day(self):
        # Monday window through Tuesday morning, Berlin standard time.
        for stamp, expected in [('2026-11-02T13:59:59+00:00', False),
                                ('2026-11-02T14:00:00+00:00', True),
                                ('2026-11-03T04:59:59+00:00', True),
                                ('2026-11-03T05:00:00+00:00', False),
                                ('2026-11-02T04:00:00+00:00', False)]:
            with self.subTest(stamp=stamp):
                self.assertEqual(expected, active_at(datetime.fromisoformat(stamp), 900, 360, {0}))

    def test_dst_skip_and_repeat(self):
        for stamp, expected in [('2026-03-29T00:59:59+00:00', False),
                                ('2026-03-29T01:00:00+00:00', False),
                                ('2026-10-25T00:30:00+00:00', True),
                                ('2026-10-25T01:30:00+00:00', True)]:
            with self.subTest(stamp=stamp):
                self.assertEqual(expected, active_at(datetime.fromisoformat(stamp), 120, 180, {6}))

    def test_naive_time_and_invalid_resources_fail_closed(self):
        with self.assertRaises(ValueError):
            active_at(datetime(2026, 1, 1), 900, 360, {0})
        with self.assertRaises(ValueError):
            admission(100, 90, 10, 100, -1, 1)
