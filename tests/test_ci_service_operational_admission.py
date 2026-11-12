"""Pure admission fixtures: never run SCM, ACL commands, or network requests."""
import copy
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest
import io
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('admission', ROOT/'scripts/ci_service_operational_admission.py')
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.context = dict(event='workflow_dispatch', repository=guard.REPOSITORY,
                            sha='a'*40, source_sha='a'*40, attempt='1', run_id='123',
                            authorization_commit='b'*40, actor='operator')
        self.record = dict(status='APPROVED', SourceKind='explicit_operator_record',
                           repository=guard.REPOSITORY, source_sha='a'*40,
                           workflow=guard.WORKFLOW, environment=guard.ENVIRONMENT,
                           matrix=list(guard.MATRIX), permissions=list(guard.EFFECTS),
                           attempt=1, approved_by='operator', expires_at=datetime.datetime.fromtimestamp(1900003600, datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
        self.environment = dict(id=7, name=guard.ENVIRONMENT, protection_rules=[
            dict(type='required_reviewers', prevent_self_review=False,
                 reviewers=[dict(type='User', reviewer=dict(login='operator'))])])
        self.history = [dict(state='approved', user=dict(login='operator', type='User'),
                             environments=[dict(id=7, name=guard.ENVIRONMENT)])]

    def check(self, context=None, record=None, environment=None, history=None):
        raw = json.dumps(self.record if record is None else record).encode()
        ctx = dict(self.context if context is None else context)
        ctx['authorization_sha256'] = hashlib.sha256(raw).hexdigest()
        return guard.validate(ctx, raw, self.environment if environment is None else environment,
                              self.history if history is None else history, now=1900000000)

    def test_exact_record_and_run_specific_required_reviewer_history_admit(self):
        self.assertEqual(self.check(), 'operator')

    def test_ordinary_events_and_reruns_block_even_with_record_and_approval(self):
        for key, value in [('event', 'push'), ('event', 'pull_request'), ('attempt', '2'),
                           ('repository', 'other/repo'), ('source_sha', 'c'*40)]:
            ctx = dict(self.context, **{key: value})
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                self.check(context=ctx)

    def test_missing_pending_expired_or_wrong_scope_blocks(self):
        for key, value in [('status', 'PENDING'), ('SourceKind', 'hash'), ('source_sha', 'c'*40),
                           ('expires_at', '2020-01-01T00:00:00Z'), ('matrix', ['windows-2022']),
                           ('permissions', ['all']), ('approved_by', 'someone'), ('attempt', 2)]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.check(record=dict(self.record, **{key: value}))

    def test_no_environment_or_required_user_reviewer_blocks(self):
        for env in [{}, dict(self.environment, protection_rules=[]),
                    dict(self.environment, protection_rules=[dict(type='required_reviewers', reviewers=[])]),
                    dict(self.environment, name='other')]:
            with self.subTest(env=env), self.assertRaises(ValueError):
                self.check(environment=env)

    def test_existing_prevent_self_review_policy_is_respected(self):
        env = copy.deepcopy(self.environment)
        env['protection_rules'][0]['prevent_self_review'] = True
        with self.assertRaises(ValueError):
            self.check(environment=env)
        self.assertEqual(self.check(context=dict(self.context, actor='dispatcher'), environment=env), 'operator')

    def test_duplicate_record_and_remote_metadata_keys_are_rejected(self):
        for raw in [b'{"status":"DENIED","status":"APPROVED"}',
                    b'{"protection_rules":[],"protection_rules":[{}]}',
                    b'[{"state":"rejected","state":"approved"}]']:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                guard.decode_json(raw)
        raw = json.dumps(self.record).replace('"status": "APPROVED"',
                                             '"status":"DENIED","status":"APPROVED"').encode()
        ctx = dict(self.context, authorization_sha256=hashlib.sha256(raw).hexdigest())
        with self.assertRaises(ValueError):
            guard.validate(ctx, raw, self.environment, self.history, now=1900000000)

    def test_hash_alone_and_wrong_or_ambiguous_history_never_authorize(self):
        wrong = copy.deepcopy(self.history)
        wrong[0]['environments'][0]['id'] = 8
        rejected = copy.deepcopy(self.history)
        rejected[0]['state'] = 'rejected'
        for history in [[], wrong, rejected, self.history * 2]:
            with self.subTest(history=history), self.assertRaises(ValueError):
                self.check(history=history)

    def test_workflow_cannot_reach_native_before_both_admissions(self):
        text = (ROOT/guard.WORKFLOW).read_text()
        self.assertIn("needs.admission.outputs.admitted == 'true'", text)
        self.assertIn("github.event_name == 'workflow_dispatch'", text)
        self.assertIn('environment: '+guard.ENVIRONMENT, text)
        self.assertLess(text.index('--phase review'), text.index('Fetch exact reviewed Grid'))
        self.assertIn('C3_OPERATIONAL_ADMISSION_BLOCKED', text)

    def test_default_event_denies_before_any_http(self):
        with patch.dict(guard.os.environ, {}, clear=True), patch.object(guard, 'get') as get:
            with patch('sys.argv', ['guard', '--phase', 'preflight']):
                self.assertEqual(guard.main(), 1)
            get.assert_not_called()

    def test_null_review_response_is_not_preflight(self):
        env = dict(GITHUB_EVENT_NAME='workflow_dispatch', GITHUB_REPOSITORY=guard.REPOSITORY,
                   GITHUB_SHA='a'*40, GITHUB_RUN_ATTEMPT='1', GITHUB_RUN_ID='123',
                   CI_SOURCE_SHA='a'*40, CI_AUTHORIZATION_COMMIT='b'*40,
                   CI_AUTHORIZATION_SHA256='c'*64)
        with patch.dict(guard.os.environ, env, clear=True), patch.object(guard, 'validate') as validate:
            with patch.object(guard, 'get', side_effect=[b'{}', b'{}', b'null']):
                with patch('sys.argv', ['guard', '--phase', 'review']):
                    self.assertEqual(guard.main(), 1)
            validate.assert_not_called()

    def test_redirect_and_oversized_or_non200_http_fail_closed(self):
        with self.assertRaises(ValueError):
            guard.NoRedirect().redirect_request(None, None, None, None, None, None)
        class Response(io.BytesIO):
            status = 200
            headers = {}
            def geturl(self):
                return url
        url = 'https://api.github.com/repos/'+guard.REPOSITORY+'/environments/'+guard.ENVIRONMENT
        class Opener:
            def open(self, request, timeout):
                return Response(b'x'*(guard.LIMIT+1))
        with self.assertRaises(ValueError):
            guard.get(url, '', opener=Opener())


if __name__ == '__main__':
    unittest.main()
