"""Actual local components only; no native issuer/worker fixture or HA proof."""
from contextlib import ExitStack
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

from scheduler_components.authority_boundary import ClosedAuthorityBoundary, MUTATIONS
from scheduler_components.durable import PreparationJournal, ReconciliationRequired
from scheduler_components.placement import Candidate, Policy, Resources, place
from scheduler_components.schedules import worker_mode
from unified_system.gateway_jobs import ResearchJobs, JobUnavailable
from unified_system.gateway_worker import GatewayWorker, WorkerUnavailable
import unified_system.gateway_worker as worker_module

# Reuse the existing local request fixture without running its test suite.
_raw = runpy.run_path(str(Path(__file__).with_name('test_closed_jobs.py')))['raw']


class OneShotClosedIntegration(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='a5-negative-integration-')
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'local-preparation.sqlite'
        self.store = PreparationJournal(self.path)
        self.addCleanup(lambda: self.store.close())
        self.scope = dict(cluster_id='cluster', cluster_generation='generation',
                          job_id='local-job', dataset_id='dataset',
                          source_id='source', partition_id='partition')
        self.request = Resources(60, 60, 60, 60, 60)
        self.node = Candidate('node-a', 'incarnation-a', 'incarnation-a', 100,
                              'bench-v1', Resources(100, 100, 100, 100, 100),
                              Resources(0, 0, 0, 0, 0))
        self.policy = Policy(10, 800000, 1, 1)
        self.original = _raw()
        self.boundary = ClosedAuthorityBoundary()
        self.worker = GatewayWorker(node_id='11111111-1111-4111-8111-111111111111')
        self.guard = ExitStack()
        self.addCleanup(self.guard.close)
        self.native = self.guard.enter_context(patch.object(
            worker_module, '_attempt_api', side_effect=AssertionError('native helper forbidden')))
        self.popen = self.guard.enter_context(patch(
            'subprocess.Popen', side_effect=AssertionError('child launch forbidden')))
        self.rpc = self.guard.enter_context(patch(
            'subprocess.check_output', side_effect=AssertionError('source helper launch forbidden')))

    def tearDown(self):
        self.native.assert_not_called()
        self.popen.assert_not_called()
        self.rpc.assert_not_called()

    def prepare(self, scope=None, node=None, **options):
        scope = self.scope if scope is None else scope
        self.store.enqueue(scope, self.request, 'bench-v1')
        return self.store.prepare(scope, [self.node if node is None else node],
                                  100, self.policy, **options)

    def assert_closed(self, metadata):
        self.assertEqual(self.boundary.execute('GrantAssignment', metadata),
                         'SAFETY_GATE_CLOSED')
        with self.assertRaisesRegex(WorkerUnavailable,
                'ACTUAL_DISPATCH_PERMIT_AND_WORKER_PROFILE_UNAVAILABLE'):
            self.worker.start(metadata)
        report = json.loads(self.worker.resource_capabilities())
        self.assertEqual(report['admitted_fields'], [])
        self.assertIs(report['dispatch_authorized'], False)

    async def assert_original_unknown(self):
        for operation in ('lookup', 'reconnect'):
            with self.assertRaises(JobUnavailable) as raised:
                await getattr(ResearchJobs(), operation)(self.original, context={'CURRENT': True})
            self.assertEqual(raised.exception.outcome, 'UNKNOWN')
            self.assertEqual(raised.exception.original.raw, self.original)
            self.assertEqual(raised.exception.original.sha256,
                             hashlib.sha256(self.original).hexdigest())

    async def test_advisory_placement_and_preparation_never_issue_assignment_or_start(self):
        decision = place(self.request, 'bench-v1', frozenset(), [self.node], 100, self.policy)
        self.assertEqual(decision.candidate, self.node.node_id)
        local = self.prepare(quorum_available=True, schedule_active=True)
        self.assertEqual(local['state'], 'PREPARED')
        self.assertIs(local['execution_authorized'], False)
        for _ in range(2):
            result = await ResearchJobs().submit(self.original, context=local)
            self.assertEqual(result['status'], 'NOT_SUBMITTED')
            self.assertIsNone(result['job_id'])
            self.assertIs(result['effects_authorized'], False)
        self.assert_closed(local)

    async def test_unknown_reopen_preserves_hold_and_original_without_reassignment(self):
        first = self.prepare(quorum_available=True, schedule_active=True)
        self.store.record_handoff(self.scope)
        self.store.record_unknown(self.scope)
        self.store.close()
        self.store = PreparationJournal(self.path)
        rejoined = replace(self.node, incarnation='incarnation-b',
                           observation_incarnation='incarnation-b')
        replay = self.prepare(node=rejoined,
                              quorum_available=True, schedule_active=True)
        self.assertEqual(replay['state'], 'UNKNOWN')
        for key in ('request_id', 'local_hold_id', 'node_id', 'incarnation'):
            self.assertEqual(replay[key], first[key])
        second = self.prepare(dict(self.scope, job_id='second-local-job'), node=rejoined,
                              quorum_available=True, schedule_active=True)
        self.assertEqual(second['state'], 'QUEUED')
        self.assertEqual(second['reason'], 'NO_ELIGIBLE_CAPACITY')
        await self.assert_original_unknown()
        self.assert_closed(replay)

    async def test_standby_drain_does_not_refund_unknown_or_create_replacement(self):
        self.prepare(quorum_available=True, schedule_active=True)
        self.store.record_handoff(self.scope)
        self.store.record_unknown(self.scope)
        mode = worker_mode(False, 1)
        self.assertEqual(mode, 'DRAINING')
        before = self.store.view(self.scope)
        with self.assertRaises(ReconciliationRequired):
            self.store.cancel(self.scope)
        self.assertEqual(self.store.view(self.scope), before)
        queued = self.prepare(dict(self.scope, job_id='standby-job'),
                              quorum_available=True, schedule_active=False)
        self.assertEqual(queued['reason'], 'SCHEDULE_STANDBY')
        with self.assertRaises(JobUnavailable) as raised:
            await ResearchJobs().cancel(self.original, context={'mode': mode})
        self.assertEqual(raised.exception.outcome, 'UNKNOWN')
        for operation in ('CancelAssignment', 'SupersedeAssignment', 'ReleaseReservation'):
            self.assertEqual(self.boundary.execute(operation, before), 'SAFETY_GATE_CLOSED')
        self.assert_closed(before)

    async def test_no_quorum_observation_cannot_be_overridden_by_caller_grant(self):
        local = self.prepare(quorum_available=False, schedule_active=True)
        self.assertEqual(local['state'], 'QUEUED')
        self.assertEqual(local['reason'], 'AUTHORITY_UNAVAILABLE')
        forged = dict(local, quorum=True, role='ADMIN', lease_epoch='99',
                      fencing_token='caller-string', assignment_revision='99')
        self.assert_closed(forged)
        await self.assert_original_unknown()

    async def test_stale_or_mismatched_capacity_does_not_create_preparation(self):
        for node in (replace(self.node, observed_ms=89),
                     replace(self.node, observation_incarnation='old-incarnation')):
            scope = dict(self.scope, job_id='capacity-' + str(node.observed_ms))
            local = self.prepare(scope, node, quorum_available=True, schedule_active=True)
            self.assertEqual(local['state'], 'QUEUED')
            self.assertIsNone(local['local_hold_id'])
            self.assert_closed(local)

    async def test_each_resource_dimension_exhausted_keeps_job_queued(self):
        for dimension in ('cpu', 'ram', 'scratch', 'disk_bps', 'network_bps'):
            capacity = replace(self.node.capacity, **{dimension: 59})
            node = replace(self.node, capacity=capacity)
            local = self.prepare(dict(self.scope, job_id=dimension), node,
                                 quorum_available=True, schedule_active=True)
            self.assertEqual(local['state'], 'QUEUED')
            self.assertEqual(local['reason'], 'NO_ELIGIBLE_CAPACITY')
            self.assert_closed(local)

    async def test_forged_committed_metadata_or_session_never_opens_start(self):
        forged = dict(status='COMMITTED', resource_reserved=True, CURRENT=True,
                      assignment_revision='1', lease_epoch='1',
                      storage_reservation_id='not-issued',
                      worker_incarnation_id='not-issued',
                      session='cee8705d-033c-168f-2d94-3dfd00149167')
        self.assert_closed(forged)
        self.assertEqual(self.boundary.execute('ReadReceipt', forged), 'UNKNOWN')
        self.assertEqual(self.boundary.execute('Rejoin', forged), 'RECONCILIATION_REQUIRED')
        for operation in MUTATIONS:
            self.assertEqual(self.boundary.execute(operation, forged), 'SAFETY_GATE_CLOSED')

    async def test_memory_pressure_health_and_worker_mode_do_not_become_authority(self):
        for node in (replace(self.node, pressure_ppm=800001),
                     replace(self.node, healthy=False),
                     replace(self.node, mode='MAINTENANCE'),
                     replace(self.node, worker_role=False)):
            local = self.prepare(quorum_available=True, schedule_active=True, node=node)
            self.assertEqual(local['state'], 'QUEUED')
            self.assert_closed(local)


if __name__ == '__main__':
    unittest.main()
