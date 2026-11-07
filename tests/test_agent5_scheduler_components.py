import dataclasses
from datetime import datetime
import unittest
import tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import sqlite3
import subprocess
import sys
from contextlib import closing

from scheduler_components.placement import Resources, Candidate, Policy, place
from scheduler_components.schedules import active_at, worker_mode
from scheduler_components.authority_boundary import ClosedAuthorityBoundary, MUTATIONS
from scheduler_components.durable import PreparationJournal, IntentConflict, ReconciliationRequired


class DurablePreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'preparation.sqlite'
        self.store = PreparationJournal(self.path)
        self.addCleanup(self.store.close)
        self.scope = dict(cluster_id='cluster', cluster_generation='generation', job_id='job1',
                          dataset_id='dataset', source_id='source', partition_id='partition')
        self.request = Resources(60, 60, 60, 60, 60)
        self.node = Candidate('node-a', 'process-a', 'process-a', 90, 'bench-v1',
                              Resources(100, 100, 100, 100, 100), Resources(0, 0, 0, 0, 0))
        self.policy = Policy(10, 800000, 1, 1)

    def scope2(self):
        return dict(self.scope, job_id='job2')

    def prepare(self, scope=None, nodes=None, **options):
        return self.store.prepare(scope or self.scope, nodes or [self.node], 100, self.policy,
                                  quorum_available=options.get('quorum_available', True),
                                  schedule_active=options.get('schedule_active', True))

    def enqueue(self, scope=None):
        return self.store.enqueue(scope or self.scope, self.request, 'bench-v1')

    def test_registry_survives_restart_without_execution_permission(self):
        self.enqueue()
        self.store.close()
        self.store = PreparationJournal(self.path)
        self.addCleanup(self.store.close)
        self.assertEqual('QUEUED', self.store.view(self.scope).get('state'))
        self.assertIs(False, self.store.view(self.scope).get('execution_authorized'))

    def test_job_spec_is_immutable_and_enqueue_idempotent(self):
        self.enqueue()
        self.enqueue()
        self.assertEqual(1, len(self.store.events()))
        with self.assertRaises(IntentConflict):
            self.store.enqueue(self.scope, Resources(1, 1, 1, 1, 1), 'bench-v1')

    def test_local_holds_prevent_overbooking(self):
        self.enqueue()
        self.enqueue(self.scope2())
        self.assertEqual('PREPARED', self.prepare().get('state'))
        self.assertEqual('QUEUED', self.prepare(self.scope2()).get('state'))

    def test_preparation_retry_preserves_original_intent(self):
        self.enqueue()
        first = self.prepare()
        self.assertIsNotNone(first.get('request_id'))
        self.assertEqual(first, self.prepare())

    def test_unknown_survives_restart_and_never_releases_or_rekeys(self):
        self.enqueue()
        first = self.prepare()
        self.store.record_handoff(self.scope)
        self.store.record_unknown(self.scope)
        self.store.close()
        self.store = PreparationJournal(self.path)
        self.addCleanup(self.store.close)
        result = self.store.view(self.scope)
        self.assertEqual('UNKNOWN', result.get('state'))
        self.assertEqual(first.get('request_id'), result.get('request_id'))
        with self.assertRaises(ReconciliationRequired):
            self.store.cancel(self.scope)
        self.enqueue(self.scope2())
        new_process = dataclasses.replace(self.node, incarnation='new', observation_incarnation='new')
        self.assertEqual('QUEUED', self.prepare(self.scope2(), [new_process]).get('state'))
        self.assertIs(False, result.get('execution_authorized'))

    def test_unknown_cpu_hold_blocks_incompatible_benchmark_after_restart(self):
        self.enqueue()
        self.prepare()
        self.store.record_handoff(self.scope)
        self.store.record_unknown(self.scope)
        self.store.close()
        self.store = PreparationJournal(self.path)
        self.addCleanup(self.store.close)
        self.store.enqueue(self.scope2(), Resources(900, 10, 10, 10, 10), 'bench-v2')
        changed_scale = dataclasses.replace(self.node, benchmark_id='bench-v2',
                                            capacity=Resources(1000, 100, 100, 100, 100))
        self.assertEqual('QUEUED', self.prepare(self.scope2(), [changed_scale]).get('state'))

    def test_only_never_handed_off_hold_can_be_cancelled(self):
        self.enqueue()
        self.prepare()
        self.assertEqual('CANCELLED', self.store.cancel(self.scope).get('state'))
        self.enqueue(self.scope2())
        self.assertEqual('PREPARED', self.prepare(self.scope2()).get('state'))
        self.store.record_handoff(self.scope2())
        with self.assertRaises(ReconciliationRequired):
            self.store.cancel(self.scope2())

    def test_no_quorum_or_standby_never_creates_new_preparation(self):
        self.enqueue()
        self.assertEqual('AUTHORITY_UNAVAILABLE', self.prepare(quorum_available=False).get('reason'))
        self.assertEqual('SCHEDULE_STANDBY', self.prepare(schedule_active=False).get('reason'))
        self.assertIsNone(self.store.view(self.scope).get('request_id'))

    def test_stale_capacity_and_pressure_remain_queued(self):
        self.enqueue()
        stale = dataclasses.replace(self.node, observed_ms=89)
        self.assertEqual('QUEUED', self.prepare(nodes=[stale]).get('state'))
        pressure = dataclasses.replace(self.node, pressure_ppm=900000)
        self.assertEqual('QUEUED', self.prepare(nodes=[pressure]).get('state'))
        self.assertIsNone(self.store.view(self.scope).get('local_hold_id'))

    def test_invalid_raw_reservation_cannot_be_masked_by_local_hold(self):
        self.enqueue()
        self.prepare()
        self.enqueue(self.scope2())
        malformed = dataclasses.replace(self.node, reserved=Resources(-1, 0, 0, 0, 0))
        with self.assertRaises(ValueError):
            self.prepare(self.scope2(), [malformed])

    def test_transaction_failure_rolls_back_preparation_and_hold(self):
        self.enqueue()
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("CREATE TRIGGER stop_event BEFORE INSERT ON events WHEN NEW.kind='PREPARED' BEGIN SELECT RAISE(ABORT,'injected'); END")
            db.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.prepare()
        self.assertEqual('QUEUED', self.store.view(self.scope).get('state'))
        self.assertIsNone(self.store.view(self.scope).get('local_hold_id'))
        self.assertEqual(1, len(self.store.events()))

    def test_process_crash_before_event_commit_recovers_without_partial_hold(self):
        self.enqueue()
        code = """
import json, os, sys
from scheduler_components.durable import PreparationJournal
from scheduler_components.placement import Candidate, Resources, Policy
store = PreparationJournal(sys.argv[1])
scope = json.loads(sys.argv[2])
store._event = lambda *args: os._exit(23)
node = Candidate('node-a','process-a','process-a',90,'bench-v1',Resources(100,100,100,100,100),Resources(0,0,0,0,0))
store.prepare(scope,[node],100,Policy(10,800000,1,1),quorum_available=True,schedule_active=True)
"""
        import json
        crashed = subprocess.run([sys.executable, '-c', code, str(self.path), json.dumps(self.scope)],
                                  cwd=Path(__file__).resolve().parents[1], capture_output=True, timeout=20)
        self.assertEqual(23, crashed.returncode, crashed.stderr.decode(errors='replace'))
        self.assertEqual('QUEUED', self.store.view(self.scope).get('state'))
        self.assertIsNone(self.store.view(self.scope).get('request_id'))
        self.assertEqual('PREPARED', self.prepare().get('state'))

    def test_two_connections_cannot_spend_same_local_capacity(self):
        self.enqueue()
        self.enqueue(self.scope2())
        barrier = Barrier(2)
        def attempt(scope):
            store = PreparationJournal(self.path)
            try:
                barrier.wait(timeout=10)
                return store.prepare(scope, [self.node], 100, self.policy,
                                     quorum_available=True, schedule_active=True).get('state')
            finally:
                store.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(attempt, [self.scope, self.scope2()]))
        self.assertEqual(['PREPARED', 'QUEUED'], sorted(outcomes))

    def test_invalid_resource_input_cannot_mutate_registry(self):
        with self.assertRaises(ValueError):
            self.store.enqueue(self.scope, Resources(-1, 0, 0, 0, 0), 'bench-v1')
        self.assertEqual([], self.store.events())

    def test_local_event_sequence_is_durable_and_not_authority_epoch(self):
        self.enqueue()
        self.prepare()
        before = self.store.events()
        self.assertEqual([1, 2], [e['sequence'] for e in before])
        self.store.close()
        self.store = PreparationJournal(self.path)
        self.addCleanup(self.store.close)
        self.store.record_handoff(self.scope)
        self.assertEqual([1, 2, 3], [e['sequence'] for e in self.store.events()])

class PlacementTests(unittest.TestCase):
    def setUp(self):
        self.request = Resources(10, 10, 10, 10, 10)
        self.node = Candidate('node-a', 'process-a', 'process-a', 90, 'bench-v1',
                              Resources(100, 100, 100, 100, 100), Resources(0, 0, 0, 0, 0))
        self.policy = Policy(10, 800000, 1, 1)

    def run_place(self, *nodes, **changes):
        return place(changes.get('request', self.request), 'bench-v1', frozenset({'dataset-a'}),
                     nodes or (self.node,), 100, changes.get('policy', self.policy))

    def test_eligible_is_advisory_candidate(self):
        self.assertEqual('node-a', self.run_place().candidate)

    def test_each_resource_can_exhaust(self):
        for dimension in ('cpu', 'ram', 'scratch', 'disk_bps', 'network_bps'):
            with self.subTest(dimension=dimension):
                reserved = dataclasses.replace(self.node.reserved, **{dimension: 91})
                result = self.run_place(dataclasses.replace(self.node, reserved=reserved))
                self.assertIsNone(result.candidate)
                self.assertIn(('node-a', 'INSUFFICIENT_' + dimension.upper()), result.rejections)

    def test_stale_future_or_previous_incarnation_denied(self):
        for changes, reason in [({'observed_ms': 89}, 'CAPACITY_STALE'),
                                ({'observed_ms': 101}, 'CAPACITY_FUTURE'),
                                ({'observation_incarnation': 'old'}, 'INCARNATION_MISMATCH')]:
            with self.subTest(reason=reason):
                self.assertIn(('node-a', reason), self.run_place(dataclasses.replace(self.node, **changes)).rejections)

    def test_health_pressure_roles_schedule_and_benchmark(self):
        for changes, reason in [({'healthy': False}, 'UNHEALTHY'),
                                ({'pressure_ppm': 800001}, 'MEMORY_PRESSURE'),
                                ({'worker_role': False}, 'NO_WORKER_ROLE'),
                                ({'mode': 'STANDBY'}, 'NODE_STANDBY'),
                                ({'mode': 'DRAINING'}, 'NODE_DRAINING'),
                                ({'mode': 'MAINTENANCE'}, 'NODE_MAINTENANCE'),
                                ({'benchmark_id': 'unknown'}, 'BENCHMARK_MISMATCH')]:
            with self.subTest(reason=reason):
                self.assertIn(('node-a', reason), self.run_place(dataclasses.replace(self.node, **changes)).rejections)

    def test_cpu_benchmark_capacity_and_locality_affect_ranking(self):
        fast = dataclasses.replace(self.node, node_id='fast', capacity=Resources(200, 100, 100, 100, 100))
        self.assertEqual('fast', self.run_place(self.node, fast).candidate)
        local = dataclasses.replace(self.node, node_id='local', data=frozenset({'dataset-a'}))
        self.assertEqual('local', self.run_place(self.node, local).candidate)

    def test_exact_capacity_and_pressure_boundaries(self):
        reserved = Resources(90, 90, 90, 90, 90)
        self.assertEqual('node-a', self.run_place(dataclasses.replace(self.node, reserved=reserved, pressure_ppm=800000)).candidate)

    def test_queue_and_order_independent_tie_break(self):
        self.assertIsNone(place(self.request, 'bench-v1', frozenset(), [], 100, self.policy).candidate)
        other = dataclasses.replace(self.node, node_id='node-b')
        self.assertEqual('node-a', self.run_place(other, self.node).candidate)
        self.assertEqual('node-a', self.run_place(self.node, other).candidate)

    def test_malformed_inputs_fail_closed(self):
        for invalid in (-1, True, float('nan')):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    self.run_place(request=dataclasses.replace(self.request, ram=invalid))
        with self.assertRaises(ValueError):
            self.run_place(self.node, self.node)
        with self.assertRaises(ValueError):
            self.run_place(policy=dataclasses.replace(self.policy, max_age_ms=0))

class ScheduleTests(unittest.TestCase):
    def test_weekday_iterator_not_consumed_by_validation(self):
        instant = datetime.fromisoformat('2026-11-02T14:00:00+00:00')
        self.assertTrue(active_at(instant, 900, 360, iter([0])))

    def test_cross_midnight_and_start_weekday(self):
        for stamp, expected in [('2026-11-02T13:59:59+00:00', False),
                                ('2026-11-02T14:00:00+00:00', True),
                                ('2026-11-03T04:59:59+00:00', True),
                                ('2026-11-03T05:00:00+00:00', False),
                                ('2026-11-02T04:00:00+00:00', False)]:
            with self.subTest(stamp=stamp):
                self.assertEqual(expected, active_at(datetime.fromisoformat(stamp), 900, 360, {0}))

    def test_dst_skip_and_both_repeated_hours(self):
        for stamp, expected in [('2026-03-29T00:59:59+00:00', False),
                                ('2026-03-29T01:00:00+00:00', False),
                                ('2026-10-25T00:30:00+00:00', True),
                                ('2026-10-25T01:30:00+00:00', True)]:
            with self.subTest(stamp=stamp):
                self.assertEqual(expected, active_at(datetime.fromisoformat(stamp), 120, 180, {6}))

    def test_drain_is_separate_from_coordinator_policy(self):
        self.assertEqual('ACTIVE', worker_mode(True, 0))
        self.assertEqual('DRAINING', worker_mode(False, 1))
        self.assertEqual('STANDBY', worker_mode(False, 0))
        # These functions return worker policy only; no coordinator role input exists.

    def test_invalid_schedule(self):
        with self.assertRaises(ValueError):
            active_at(datetime(2026, 1, 1), 900, 360, {0})
        with self.assertRaises(ValueError):
            active_at(datetime.fromisoformat('2026-01-01T00:00:00+00:00'), 360, 360, {0})
        with self.assertRaises(ValueError):
            worker_mode(False, -1)

class AuthorityBoundaryTests(unittest.TestCase):
    def test_every_proposed_mutation_is_closed(self):
        for operation in sorted(MUTATIONS):
            with self.subTest(operation=operation):
                self.assertEqual('SAFETY_GATE_CLOSED', ClosedAuthorityBoundary().execute(
                    operation, {'quorum': True, 'gates_open': True, 'token': 'caller-assertion'}))

    def test_reads_do_not_invent_receipts_or_mutate(self):
        self.assertEqual('UNKNOWN', ClosedAuthorityBoundary().execute('ReadReceipt'))
        self.assertEqual('RECONCILIATION_REQUIRED', ClosedAuthorityBoundary().execute('Rejoin'))
        self.assertEqual('UNSUPPORTED_OPERATION', ClosedAuthorityBoundary().execute('FutureOperation'))

if __name__ == '__main__':
    unittest.main()
