import dataclasses
from datetime import datetime
import unittest

from scheduler_components.placement import Resources, Candidate, Policy, place
from scheduler_components.schedules import active_at, worker_mode
from scheduler_components.authority_boundary import ClosedAuthorityBoundary, MUTATIONS

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
