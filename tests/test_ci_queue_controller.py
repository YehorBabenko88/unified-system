import copy
import json
from pathlib import Path
import tempfile
import unittest

from unified_system import ci_queue_controller as q
from unified_system.journal import Journal


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'queue.sqlite'
        self.pin = q.Pin('YehorBabenko88/math', 123, 42352374979, 1,
                         '2446d04624469e34aa96ed766be7a4887d6d654c', 456)
        self.c = q.Controller.create(self.path, self.pin, limit=4, initial=10, cap=40, seed=7)
        self.run = dict(id=self.pin.run_id, workflow_id=123, run_attempt=1,
                        head_sha=self.pin.source_sha, repository={'full_name': self.pin.repository},
                        status='queued', conclusion=None, created_at='2026-11-07T00:00:00Z')
        self.job = dict(id=456, run_id=self.pin.run_id, run_attempt=1, head_sha=self.pin.source_sha,
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
        with self.assertRaises(ValueError): self.observe(run=dict(self.run, workflow_id=123.0))
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
            q.Controller.open(self.path, q.Pin(self.pin.repository, 123, self.pin.run_id, 2, self.pin.source_sha, 456))

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


if __name__ == '__main__': unittest.main()
