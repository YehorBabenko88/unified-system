from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from unittest import mock

from unified_system import ci_queue_controller as q
from unified_system.journal import Journal


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'queue.sqlite'
        self.pin = q.Pin('YehorBabenko88/math', 409676563, 42352374979, 1,
                         '2446d04624469e34aa96ed766be7a4887d6d654c', 128343065197)
        self.c = q.Controller.create(self.path, self.pin, limit=4, initial=10, cap=40, seed=7)
        self.run = dict(id=self.pin.run_id, workflow_id=self.pin.workflow_id, run_attempt=1,
                        head_sha=self.pin.source_sha, repository={'full_name': self.pin.repository},
                        status='queued', conclusion=None, created_at='2026-11-07T00:00:00Z')
        self.job = dict(id=self.pin.job_id, run_id=self.pin.run_id, run_attempt=1, head_sha=self.pin.source_sha,
                        status='queued', conclusion=None, runner_id=None, steps=[])

    def observe(self, now=100, run=None, job=None):
        return self.c.observe(json.dumps({'run': run or self.run, 'job': job or self.job,
                                         'artifacts': []}).encode(), now=now)

    def test_queued_without_runner_or_steps(self):
        self.assertEqual(self.observe()['state'], 'QUEUED')

    def test_attempt_and_head_mismatch(self):
        for field, value in [('run_attempt', 2), ('head_sha', 'a'*40)]:
            run = dict(self.run, **{field: value})
            with self.assertRaises(ValueError): self.observe(run=run)
        with self.assertRaises(ValueError): self.observe(run=dict(self.run, workflow_id=float(self.pin.workflow_id)))
        self.assertEqual(self.c.history(), [])

    def test_null_and_unknown_never_success(self):
        for state in ['completed', 'surprise']:
            run, job = dict(self.run, status=state), dict(self.job, status=state)
            self.assertEqual(self.observe(now=100 if state == 'completed' else 200, run=run, job=job)['state'], 'UNKNOWN')

    def test_terminal_conflict_stays_unknown(self):
        for now, conclusion in [(100, 'success'), (200, 'failure'), (300, 'success')]:
            result = self.observe(now, dict(self.run, status='completed', conclusion=conclusion),
                                  dict(self.job, status='completed', conclusion=conclusion))
            self.assertEqual(result['state'], 'SUCCESS' if now == 100 else 'UNKNOWN')

    def test_duplicate_and_old_observation(self):
        first = self.observe()
        self.assertEqual(self.observe(200)['state'], first['state'])
        self.assertEqual(len(self.c.history()), 2)
        with self.assertRaises(ValueError): self.observe(150)

    def test_restart_preserves_backoff_and_limit(self):
        first = self.observe()
        self.c = q.Controller.open(self.path, self.pin)
        with self.assertRaises(ValueError): self.observe(first['next_at'] - 1)
        for now in [200, 300, 400]: self.observe(now)
        self.c = q.Controller.open(self.path, self.pin)
        with self.assertRaises(ValueError): self.observe(1000)

    def test_clock_rollback_cannot_observe(self):
        self.observe()
        with self.assertRaises(ValueError): self.observe(99)

    def test_terminal_regression_does_not_restore_success(self):
        self.observe(100, dict(self.run,status='completed',conclusion='success'),
                     dict(self.job,status='completed',conclusion='success'))
        self.assertEqual(self.observe(200)['state'], 'UNKNOWN')

    def test_workflow_job_consistency(self):
        self.assertEqual(self.observe(100, dict(self.run,status='in_progress'))['state'], 'QUEUED')
        self.assertEqual(self.observe(200, dict(self.run,status='pending'))['state'], 'UNKNOWN')
        self.assertEqual(self.observe(300, job=dict(self.job,status='in_progress'))['state'], 'UNKNOWN')

    def test_payload_cannot_renew_authorization(self):
        self.run['authorization_state'] = 'AUTHORIZED'
        self.job['authorization_state'] = 'UNUSED'
        self.assertEqual(self.observe()['authorization_state'], 'CONSUMED')

    def test_consumed_authorization_and_no_executor(self):
        self.assertEqual(self.observe()['authorization_state'], 'CONSUMED')
        for name in ['dispatch', 'rerun', 'cancel', 'renew', 'execute']:
            self.assertFalse(hasattr(self.c, name))
        with self.assertRaises(ValueError):
            q.Controller.open(self.path, q.Pin(self.pin.repository, self.pin.workflow_id, self.pin.run_id, 2, self.pin.source_sha, self.pin.job_id))

    def test_archived_math_queue_zero_runner(self):
        # Reduced verbatim scalar fields from Math115 observation-240m API
        # snapshots; source-byte SHA256 values are pinned in the operations doc.
        run = dict(self.run, created_at='2026-11-07T07:42:12Z')
        job = dict(self.job, runner_id=0, created_at='2026-11-07T07:42:13Z',
                   started_at='2026-11-07T07:42:13Z', completed_at=None)
        result = self.observe(run=run, job=job)
        self.assertEqual(result['state'], 'QUEUED')
        self.assertEqual(result['runner_assignment'], 0)
        self.assertEqual(result['runner_assignment_state'], 'UNASSIGNED')
        self.assertEqual(result['authorization_state'], 'CONSUMED')

    def test_ordinary_run_does_not_invent_consumed_authorization(self):
        pin = q.Pin('YehorBabenko88/unified-system', 1, 2, 1, 'a'*40, 3)
        controller = q.Controller.create(Path(self.tmp.name)/'ordinary.sqlite', pin)
        run = dict(self.run,id=2,workflow_id=1,head_sha='a'*40,repository={'full_name':pin.repository})
        job = dict(self.job,id=3,run_id=2,head_sha='a'*40)
        result = controller.observe(json.dumps({'run':run,'job':job,'artifacts':[]}).encode(),now=100)
        self.assertEqual(result['authorization_state'], 'NOT_APPLICABLE')
        self.assertEqual(q.Controller.open(controller.journal.path,pin).history(),[result])

    def test_exact_pin_type_required(self):
        for pin in [None, asdict_for_test(self.pin), object()]:
            path = Path(self.tmp.name)/'invalid-pin.sqlite'
            with self.assertRaises(ValueError): q.Controller.create(path,pin)
            self.assertFalse(path.exists())

    def test_protected_identity_is_exact(self):
        for change in [{'repository':'other/math'},{'workflow_id':1},{'job_id':1}]:
            values = asdict_for_test(self.pin); values.update(change)
            with self.assertRaises(ValueError): q.Pin(**values)

    def test_foreign_file_between_check_and_initialize_is_not_adopted(self):
        path = Path(self.tmp.name)/'racing-foreign.sqlite'
        with closing(sqlite3.connect(path)) as database:
            database.execute('CREATE TABLE foreign_owner(value TEXT)');database.commit()
        before = path.read_bytes()
        # A stale/non-authoritative existence check must never authorize adoption.
        with mock.patch.object(Path,'exists',return_value=False):
            with self.assertRaises(ValueError): q.Controller.create(path,self.pin)
        self.assertEqual(path.read_bytes(),before)

    def test_initialization_failure_retains_owned_reservation(self):
        path = Path(self.tmp.name)/'partial.sqlite'
        with mock.patch.object(Journal,'initialize',side_effect=RuntimeError('injected')):
            with self.assertRaises(RuntimeError): q.Controller.create(path,self.pin)
        self.assertTrue(path.is_file())
        with self.assertRaises(ValueError): q.Controller.create(path,self.pin)
        with self.assertRaises(ValueError): q.Controller.open(path,self.pin)

    def test_simultaneous_creators_have_single_exclusive_owner(self):
        path = Path(self.tmp.name)/'simultaneous.sqlite'
        gate = threading.Barrier(2)
        original_open = q.os.open
        def reserve(*args, **kwargs):
            gate.wait(timeout=5)
            return original_open(*args, **kwargs)
        def create():
            try:
                q.Controller.create(path,self.pin)
                return 'created'
            except ValueError:
                return 'rejected'
        with mock.patch.object(q.os,'open',side_effect=reserve):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _:create(), range(2)))
        self.assertEqual(sorted(results),['created','rejected'])
        self.assertEqual(q.Controller.open(path,self.pin).history(),[])

    def test_corruption_and_foreign_journal_not_adopted(self):
        other = Path(self.tmp.name) / 'other.sqlite'
        journal = Journal(other); journal.initialize(); journal.append('OBSERVING', {'kind':'foreign'})
        with self.assertRaises(ValueError): q.Controller.open(other, self.pin)
        self.path.write_bytes(b'broken database')
        with self.assertRaises(ValueError): q.Controller.open(self.path, self.pin)

    def test_bounds_and_existing_creation(self):
        with self.assertRaises(ValueError): self.c.observe(b'x' * 262145, now=100)
        with self.assertRaises(ValueError): q.Controller.create(self.path, self.pin)
        with self.assertRaises(ValueError): self.c.observe(b'{}', now=float('nan'))

    def test_redacts_raw_fields_and_artifact_urls(self):
        self.run['token'] = 'TOP_SECRET'
        raw = json.dumps({'run':self.run, 'job':self.job, 'artifacts':[
            {'id': 999, 'archive_download_url':'https://private/?token=TOP_SECRET'}]}).encode()
        result = self.c.observe(raw, now=100)
        self.assertNotIn('TOP_SECRET', json.dumps(self.c.history()))
        self.assertEqual(result['artifacts'], [{'id':999}])
        self.assertEqual(len(result['raw_sha256']), 64)
        self.assertEqual(result['data_origin'], 'UNVERIFIED_CAPTURE')

    def test_states_and_no_timeout_infrastructure_diagnosis(self):
        for status, conclusion, expected in [('in_progress',None,'RUNNING'), ('completed','failure','FAILURE'),
                                               ('completed','cancelled','CANCELLED')]:
            with self.subTest(expected=expected):
                raw = json.dumps({'run':dict(self.run,status=status,conclusion=conclusion),
                                  'job':dict(self.job,status=status,conclusion=conclusion),'artifacts':[]}).encode()
                result = self.c.observe(raw, now=100 + len(self.c.history())*100)
                # Contradictory terminal outcomes are sticky UNKNOWN.
                self.assertEqual(result['state'], 'UNKNOWN' if expected == 'CANCELLED' else expected)


def asdict_for_test(pin):
    from dataclasses import asdict
    return asdict(pin)


if __name__ == '__main__': unittest.main()
