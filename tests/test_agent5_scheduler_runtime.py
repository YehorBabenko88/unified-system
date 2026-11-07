"""Independent runtime fixture tests; no native authority/production admission."""
import json
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys
import time

from scheduler_components.domain_v1 import encode_command, decode_command
from scheduler_components.attempt_registry import AttemptRegistry, IntentConflict
from scheduler_components.runtime import SchedulerRuntime, Unavailable
from scheduler_components.worker_control import SyntheticWorker
from scheduler_components.benchmarks import measure_local


def command(request='00000000-0000-4000-8000-000000000001'):
    return dict(schema='unified.scheduler.command.v1-c3.review1',
                operation='ASSIGN', request_id=request, idempotency_key=request,
                scope=dict(cluster_id='cluster', cluster_generation='generation',
                           job_id='job', dataset_id='dataset', source_id='source', partition_id='partition'),
                node_id='node', worker_incarnation_id='00000000-0000-4000-8000-000000000002',
                assignment_id='00000000-0000-4000-8000-000000000003',
                expected_assignment_revision='0',
                resources=dict(cpu_millicores='1000', ram_bytes='4096', scratch_bytes='4096',
                               disk_bytes_per_second='1024', network_bytes_per_second='1024'),
                resource_units='LOGICAL_PROCESSOR_1000_MILLICORES_BYTES_BYTES_PER_SECOND',
                storage_reservation_id='reservation', storage_budget_revision='1')


class FixtureAuthority:
    """Synthetic authority port; its tokens have no native authority meaning."""
    def __init__(self):
        self.calls = []
        self.available = True
        self.outcome = ('COMMITTED', b'fixture-grant')

    def execute(self, raw):
        self.calls.append(raw)
        return self.outcome

    def reconcile(self, raw):
        self.calls.append(raw)
        return self.outcome

    def verify_outcome(self, raw, state, receipt):
        if receipt != b'fixture-grant' or state != 'COMMITTED':
            raise Unavailable('fixture proof rejected')

    def require_dispatch(self, raw, receipt):
        if not self.available:
            raise Unavailable('no quorum or reservation/lease no longer valid')


class Worker:
    def __init__(self):
        self.starts = []
        self.pauses = []
    def start(self, request_id, raw, grant):
        self.starts.append(request_id)
        return b'fixture-started'
    def inspect(self, request_id):
        return b'fixture-started' if request_id in self.starts else None
    def pause(self, request_id):
        self.pauses.append(request_id)


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'attempts.db'
        self.registry = AttemptRegistry(self.path)
        self.authority = FixtureAuthority()
        self.worker = Worker()
        self.runtime = SchedulerRuntime(self.registry, self.authority, self.worker)

    def tearDown(self):
        self.registry.close()
        self.tmp.cleanup()

    def test_new_domain_has_exact_units_and_no_numeric_alias(self):
        raw = encode_command(command())
        self.assertEqual(decode_command(raw), command())
        for value in (1000, True, '01', '1.0', '-1', '9223372036854775808'):
            c = command(); c['resources']['cpu_millicores'] = value
            with self.assertRaises(ValueError): encode_command(c)

    def test_noncanonical_bytes_and_extra_fields_reject(self):
        with self.assertRaises(ValueError): decode_command(json.dumps(command()).encode())
        c = command(); c['lease_epoch'] = '1'
        with self.assertRaises(ValueError): encode_command(c)

    def test_missing_authority_never_sends(self):
        runtime = SchedulerRuntime(self.registry, None, self.worker)
        with self.assertRaises(Unavailable): runtime.submit(command())
        self.assertEqual(self.worker.starts, [])

    def test_standby_and_pressure_gate_new_assignment(self):
        for options in ({'active': False}, {'capacity_fresh': False}, {'resources_available': False}):
            with self.assertRaises(Unavailable): self.runtime.submit(command(), **options)
        self.assertEqual(self.authority.calls, [])

    def test_original_intent_is_written_before_handoff(self):
        def execute(raw):
            self.assertEqual(self.registry.get(command()['request_id'])['raw'], raw)
            self.assertEqual(self.registry.get(command()['request_id'])['state'], 'SUBMITTED')
            return self.authority.outcome
        self.authority.execute = execute
        self.assertEqual(self.runtime.submit(command())['state'], 'COMMITTED')

    def test_same_request_different_full_intent_conflicts(self):
        self.runtime.submit(command())
        c = command(); c['storage_budget_revision'] = '2'
        with self.assertRaises(IntentConflict): self.runtime.submit(c)

    def test_idempotency_key_cannot_move_to_new_request(self):
        self.runtime.submit(command())
        c = command('00000000-0000-4000-8000-000000000009')
        c['idempotency_key'] = command()['idempotency_key']
        with self.assertRaises(IntentConflict): self.runtime.submit(c)

    def test_unknown_restart_reconciles_original_never_reexecutes(self):
        self.authority.outcome = ('UNKNOWN', None)
        self.assertEqual(self.runtime.submit(command())['state'], 'UNKNOWN')
        self.registry.close(); self.registry = AttemptRegistry(self.path)
        runtime = SchedulerRuntime(self.registry, self.authority, self.worker)
        runtime.submit(command())
        self.assertEqual(len(self.authority.calls), 1)
        self.authority.outcome = ('COMMITTED', b'fixture-grant')
        runtime.reconcile(command()['request_id'])
        self.assertEqual(self.authority.calls[0], self.authority.calls[1])
        self.assertEqual(len(self.worker.starts), 1)

    def test_crash_after_seal_never_resubmits(self):
        raw = encode_command(command()); self.registry.prepare(raw); self.registry.seal(command()['request_id'])
        self.registry.close(); self.registry = AttemptRegistry(self.path)
        runtime = SchedulerRuntime(self.registry, self.authority, self.worker)
        runtime.submit(command())
        self.assertEqual(self.authority.calls, [])
        self.assertEqual(self.worker.starts, [])

    def test_stale_grant_or_reservation_blocks_dispatch(self):
        self.authority.available = False
        self.runtime.submit(command())
        self.assertEqual(self.worker.starts, [])

    def test_worker_incarnation_change_is_not_rekeyed(self):
        self.runtime.submit(command())
        c = command(); c['worker_incarnation_id'] = '00000000-0000-4000-8000-000000000099'
        with self.assertRaises(IntentConflict): self.runtime.submit(c)
        self.assertEqual(len(self.worker.starts), 1)

    def test_duplicate_committed_command_does_not_restart_worker(self):
        self.runtime.submit(command()); self.runtime.submit(command())
        self.assertEqual(len(self.worker.starts), 1)

    def test_uncertain_worker_start_is_queried_not_restarted(self):
        original = self.worker.start
        def uncertain(request_id, raw, grant):
            original(request_id, raw, grant)
            raise OSError('reply lost after start')
        self.worker.start = uncertain
        self.runtime.submit(command()); self.runtime.reconcile(command()['request_id'])
        self.assertEqual(len(self.worker.starts), 1)
        self.assertEqual(self.registry.get(command()['request_id'])['dispatch_state'], 'STARTED')

    def test_draining_pauses_but_never_calls_storage_publication(self):
        self.runtime.submit(command())
        self.runtime.drain(command()['request_id'])
        self.assertEqual(self.worker.pauses, [command()['request_id']])
        self.assertEqual(len(self.authority.calls), 1)

    def test_drain_before_dispatch_survives_restart(self):
        self.authority.available = False
        self.runtime.submit(command()); self.runtime.drain(command()['request_id'])
        self.registry.close(); self.registry = AttemptRegistry(self.path)
        runtime = SchedulerRuntime(self.registry, self.authority, self.worker)
        self.authority.available = True
        runtime.reconcile(command()['request_id'])
        self.assertEqual(self.worker.starts, [])

    def test_pause_intent_wins_claim_start_race(self):
        with SyntheticWorker() as worker:
            runtime = SchedulerRuntime(self.registry, self.authority, worker)
            original = worker.start
            def racing(request_id, raw, grant):
                runtime.drain(request_id)
                return original(request_id, raw, grant)
            worker.start = racing
            runtime.submit(command())
            self.assertEqual(worker.inspect(command()['request_id']), b'PAUSED')

    def test_failed_pause_is_retried_during_reconciliation(self):
        self.runtime.submit(command())
        original = self.worker.pause
        self.worker.pause = lambda request: (_ for _ in ()).throw(OSError('lost pause'))
        with self.assertRaises(OSError): self.runtime.drain(command()['request_id'])
        self.worker.pause = original
        self.runtime.reconcile(command()['request_id'])
        self.assertEqual(self.worker.pauses, [command()['request_id']])

    def test_unverified_receipt_and_malformed_unknown_remain_uncertain(self):
        self.authority.outcome = ('COMMITTED', b'forged-grant')
        self.assertEqual(self.runtime.submit(command())['state'], 'UNKNOWN')
        self.authority.outcome = ('UNKNOWN', b'not-an-unknown-proof')
        self.assertEqual(self.runtime.reconcile(command()['request_id'])['state'], 'UNKNOWN')
        self.assertEqual(self.worker.starts, [])

    def test_silent_child_has_bounded_response_wait(self):
        with SyntheticWorker(response_timeout=0.1) as worker:
            worker.close()
            worker.process = subprocess.Popen([sys.executable, '-I', '-c', 'import time; time.sleep(20)'],
                                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            started = time.monotonic()
            with self.assertRaises(TimeoutError): worker.inspect('one')
            self.assertLess(time.monotonic() - started, 5)
            self.assertIsNotNone(worker.process.poll())

    def test_actual_synthetic_subprocess_idempotent_control(self):
        with SyntheticWorker() as worker:
            self.assertEqual(worker.start('one', b'opaque-untrusted-fixture'), b'STARTED')
            self.assertEqual(worker.start('one', b'opaque-untrusted-fixture'), b'STARTED')
            self.assertEqual(worker.inspect('one'), b'STARTED')
            worker.pause('one')
            self.assertEqual(worker.inspect('one'), b'PAUSED')
            self.assertIsNone(worker.inspect('missing'))

    def test_benchmark_requires_explicit_opt_in(self):
        with self.assertRaises(ValueError): measure_local()

    def test_benchmark_rejects_unbounded_cpu_and_io(self):
        for options in ({'cpu_duration_ms': 2001}, {'cpu_duration_ms': True},
                        {'scratch_bytes': 8 * 1024 * 1024 + 1},
                        {'loopback_bytes': 1024 * 1024 + 1}, {'loopback_bytes': 0}):
            with self.assertRaises(ValueError): measure_local(allow_local_measurement=True, **options)


if __name__ == '__main__': unittest.main()
