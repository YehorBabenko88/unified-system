"""Pure review validation; transport acquisition and native effects stay inert."""
import copy
import datetime
import hashlib
import io
import json
import unittest
from unittest.mock import patch
from scripts import ci_service_operational_admission as legacy
from unified_system.service_bootstrap import canonical


NOW = 1900000000


def iso(value):
    return datetime.datetime.fromtimestamp(value, datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def authorization():
    # Inert test data only; never an issued owner approval record.
    return dict(schema='unified.collector.operational-authorization.v2', scope='ADMISSION_FOR_C3_QUALIFICATION',
                authorization_id='11111111-1111-4111-8111-111111111111', cohort_id='22222222-2222-4222-8222-222222222222',
                source=dict(head='a'*40, tree='b'*40, source_manifest_sha256='c'*64),
                capsule=dict(manifest_sha256='d'*64, manifest_bytes=100, archive=dict(kind='UNPACKED_MANIFEST_ONLY')),
                target=dict(runner_label='windows-2022', job_name='collector-c3',
                            installation_id='33333333-3333-4333-8333-333333333333',
                            service_name_policy='UNIFIED_COLLECTOR_V2_INSTALLATION_UUID_SHA256_24',
                            root_relative_runner_temp='unified-collector-c3/33333333-3333-4333-8333-333333333333'),
                graph_profile='COLLECTOR_C3_FINITE_SYNTHETIC_V2',
                evidence_requirements=dict(source_schema='unified.collector.source-admission.v2',
                                           capacity_schema='unified.collector.capacity-admission.v2',
                                           resource_schema='unified.collector.resource-outcome.v2', scope='ADMISSION_FOR_C3_QUALIFICATION'),
                bounds=dict(workers=1, capture_attempts=1, frames=1, frame_bytes=16, raw_bytes=32,
                            duration_seconds=10, capacity_max_age_seconds=60,
                            stop_policy=dict(transport='NSSM_CONSOLE_CTRL_C_V1', console=0, skip_methods=6,
                                             kill_process_tree=0, console_grace_ms=1000, owner_retire_seconds=5,
                                             actuation_timeout_seconds=10)),
                issued_at=iso(NOW-60), expires_at=iso(NOW+3600), approved_by='operator')


class V2CodecTests(unittest.TestCase):
    def codec(self):
        from unified_system import collector_operational_review
        return collector_operational_review

    def test_static_authorization_has_exact_agreed_bounds_and_no_resolved_host(self):
        codec = self.codec(); auth = authorization()
        self.assertEqual(codec.parse_authorization(canonical(auth), now=NOW), auth)
        expected = 'UnifiedCollector_'+hashlib.sha256(canonical(dict(
            domain='unified.owned-collector-stopped-service.v2', installation_id=auth['target']['installation_id']))).hexdigest()[:24]
        self.assertEqual(codec.derived_service_name(auth), expected)

    def test_wrong_scope_graph_old_v1_unagreed_fields_stale_and_duplicate_deny(self):
        codec = self.codec()
        for key, value in [('schema', 'unified.owned-collector-stopped-service.v1'), ('scope', 'C3_PASS'),
                           ('graph_profile', 'REMOVE_APP_ONLY'), ('expires_at', iso(NOW-1)),
                           ('issued_at', iso(NOW+1)), ('actual_host', 'not-known-before-assignment')]:
            auth = authorization(); auth[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                codec.parse_authorization(canonical(auth), now=NOW)

        with self.assertRaises(ValueError):
            codec.parse_authorization(b'{"schema":"v1","schema":"v2"}\n', now=NOW)

    def test_numeric_aliases_and_bad_flat_or_stop_bounds_deny(self):
        codec = self.codec()
        for key, value in [('workers', True), ('capture_attempts', 2), ('frames', 5), ('frame_bytes', 1048577),
                           ('raw_bytes', 1), ('duration_seconds', 121), ('capacity_max_age_seconds', 99999)]:
            auth = authorization(); auth['bounds'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                codec.parse_authorization(canonical(auth), now=NOW)
        for key, value in [('console', False), ('skip_methods', 6.0), ('kill_process_tree', '0'),
                           ('console_grace_ms', 5000), ('owner_retire_seconds', 6), ('margin_ms', 1)]:
            auth = authorization(); auth['bounds']['stop_policy'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                codec.parse_authorization(canonical(auth), now=NOW)


class V2ProviderTests(unittest.TestCase):
    def setUp(self):
        self.auth = authorization(); self.raw = canonical(self.auth)
        self.ctx = dict(event='workflow_dispatch', repository='YehorBabenko88/unified-system',
                        sha='a'*40, source_sha='a'*40, attempt='1', run_id='12', actor='dispatcher',
                        authorization_commit='f'*40, authorization_sha256=hashlib.sha256(self.raw).hexdigest(),
                        job_name='collector-c3', runner_name='GitHub Actions 100')
        api = 'https://api.github.com/repos/YehorBabenko88/unified-system'
        self.paths = dict(authorization='https://raw.githubusercontent.com/YehorBabenko88/unified-system/'+'f'*40+'/docs/collector/ci-collector-operational-intent-v2.json',
                          run=api+'/actions/runs/12', commit=api+'/git/commits/'+'a'*40,
                          jobs=api+'/actions/runs/12/attempts/1/jobs',
                          environment=api+'/environments/collector-c3-operational-v2', history=api+'/actions/runs/12/approvals')
        self.bodies = dict(authorization=self.raw,
                          run=json.dumps(dict(id=12, run_attempt=1, event='workflow_dispatch', head_sha='a'*40,
                                              status='in_progress', conclusion=None,
                                              display_title='collector-c3-operational-v2 '+self.ctx['authorization_sha256']+' '+self.ctx['authorization_commit'],
                                              path='.github/workflows/lab-stopped-service.yml', actor=dict(login='dispatcher'),
                                              triggering_actor=dict(login='dispatcher'), repository=dict(full_name=self.ctx['repository']),
                                              head_repository=dict(full_name=self.ctx['repository']), created_at=iso(NOW-30))).encode(),
                          commit=json.dumps(dict(sha='a'*40, tree=dict(sha='b'*40))).encode(),
                          jobs=json.dumps(dict(total_count=1, jobs=[dict(id=34, run_id=12, run_attempt=1, head_sha='a'*40,
                              name='collector-c3', status='in_progress', conclusion=None, runner_id=100,
                              runner_name='GitHub Actions 100', runner_group_id=0, runner_group_name='GitHub Actions', labels=['windows-2022'])])).encode(),
                          environment=json.dumps(dict(id=7, name='collector-c3-operational-v2', protection_rules=[dict(type='required_reviewers',
                              prevent_self_review=True, reviewers=[dict(type='User', reviewer=dict(id=9, login='operator'))])])).encode(),
                          history=json.dumps([dict(state='approved', comment='PRIVATE_REVIEW_COMMENT', user=dict(id=9, login='operator', type='User'),
                              environments=[dict(id=7, name='collector-c3-operational-v2')])]).encode())
        self.calls = []

    def acquire(self, *, ctx=None, final_url=None, status=200):
        from scripts.ci_collector_operational_admission import GitHubCollectorReviewProvider
        from unified_system import collector_operational_review as codec
        outer = self
        class Response(io.BytesIO):
            headers = {}
            def __init__(self, raw, url):
                super().__init__(raw); self.url = url; self.status = status
            def geturl(self):
                return final_url or self.url
        class Opener:
            def open(self, request, timeout):
                outer.calls.append(request.full_url)
                outer.assertEqual(request.get_method(), 'GET'); outer.assertEqual(timeout, 20)
                key = next(k for k, value in outer.paths.items() if value == request.full_url)
                return Response(outer.bodies[key], request.full_url)
        with patch.object(legacy, 'build_opener', return_value=Opener()), patch.object(codec.time, 'time', return_value=NOW):
            return GitHubCollectorReviewProvider('PRIVATE_TOKEN').acquire(self.ctx if ctx is None else ctx)

    def mutate(self, key, callback):
        body = json.loads(self.bodies[key]); callback(body); self.bodies[key] = json.dumps(body).encode()

    def test_actual_acquisition_validators_join_current_review_and_return_only_facts(self):
        from unified_system import collector_operational_review as codec
        raw = self.acquire(); result = codec.parse_review(raw, self.raw, now=NOW)
        self.assertEqual(result['run']['id'], 12); self.assertEqual(result['job']['id'], 34)
        self.assertEqual(result['reviewer'], dict(id=9, login='operator'))
        self.assertNotIn(b'PRIVATE', raw); self.assertLessEqual(len(raw), 65536)
        self.assertEqual(len(self.calls), 6)
        self.assertEqual(codec.phase_id(result), codec.phase_id(copy.deepcopy(result)))

    def test_push_rerun_or_wrong_job_context_denies_before_http(self):
        for key, value in [('event', 'push'), ('attempt', '2'), ('job_name', 'old-v1-job')]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.acquire(ctx=dict(self.ctx, **{key: value}))
        self.assertEqual(self.calls, [])

    def test_missing_actual_review_or_unconfigured_environment_never_uses_status_or_hash(self):
        for key, body in [('history', b'[]'), ('history', b'null'), ('environment', b'{}')]:
            with self.subTest(key=key):
                original = self.bodies[key]; self.bodies[key] = body
                with self.assertRaises(ValueError): self.acquire()
                self.bodies[key] = original

    def test_wrong_run_source_tree_job_or_reviewer_identity_denies(self):
        cases = [('run', lambda x:x.update(run_attempt=2)), ('run', lambda x:x.update(head_sha='0'*40)),
                 ('commit', lambda x:x['tree'].update(sha='0'*40)),
                 ('jobs', lambda x:x['jobs'][0].update(runner_name='foreign')),
                 ('jobs', lambda x:x['jobs'][0].update(labels=['self-hosted'])),
                 ('history', lambda x:x[0]['user'].update(id=99))]
        for key, callback in cases:
            with self.subTest(key=key):
                original = self.bodies[key]; self.mutate(key, callback)
                with self.assertRaises(ValueError): self.acquire()
                self.bodies[key] = original

    def test_actual_run_title_scope_commitment_current_state_and_review_id_types(self):
        cases = [('run', lambda x:x.update(display_title='not-the-approved-scope')),
                 ('run', lambda x:x.update(status='completed', conclusion='success')),
                 ('history', lambda x:x[0]['environments'][0].update(id=7.0))]
        for key, callback in cases:
            with self.subTest(key=key):
                original = self.bodies[key]; self.mutate(key, callback)
                with self.assertRaises(ValueError): self.acquire()
                self.bodies[key] = original

    def test_duplicate_remote_keys_redirects_http_failure_and_oversize_deny(self):
        original = self.bodies['history']
        for raw in [b'[{"state":"rejected","state":"approved"}]', b'x'*65537]:
            self.bodies['history'] = raw
            with self.assertRaises(ValueError): self.acquire()
        self.bodies['history'] = original
        with self.assertRaises(ValueError): self.acquire(final_url='https://untrusted.invalid/')
        with self.assertRaises(ValueError): self.acquire(status=403)

    def test_old_v1_record_wrong_action_profile_or_stale_authorization_denies(self):
        for key, value in [('schema', 'unified.stopped-service.v1'), ('graph_profile', 'START_ONLY'), ('expires_at', iso(NOW-1))]:
            auth = authorization(); auth[key] = value; self.bodies['authorization'] = canonical(auth)
            ctx = dict(self.ctx, authorization_sha256=hashlib.sha256(self.bodies['authorization']).hexdigest())
            with self.subTest(key=key), self.assertRaises(ValueError): self.acquire(ctx=ctx)

    def test_public_provider_has_no_transport_override_and_private_errors_are_closed(self):
        import inspect
        from scripts.ci_collector_operational_admission import GitHubCollectorReviewProvider
        from unified_system import collector_operational_review as codec
        self.assertEqual(str(inspect.signature(GitHubCollectorReviewProvider)), '(token)')
        class Broken:
            def open(self, *args, **kwargs):
                raise RuntimeError('PRIVATE_ACQUISITION_ERROR')
        with patch.object(legacy, 'build_opener', return_value=Broken()), patch.object(codec.time, 'time', return_value=NOW):
            with self.assertRaises(ValueError) as caught:
                GitHubCollectorReviewProvider('PRIVATE_TOKEN').acquire(self.ctx)
        self.assertEqual(str(caught.exception), 'COLLECTOR_OPERATIONAL_REVIEW_REJECTED')


class SharedProtectedReviewTests(unittest.TestCase):
    def setUp(self):
        self.context = {'actor': 'dispatcher'}
        self.environment = {'id': 7, 'name': 'collector-c3-operational-v2', 'protection_rules': [
            {'type': 'required_reviewers', 'prevent_self_review': True,
             'reviewers': [{'type': 'User', 'reviewer': {'login': 'operator'}}]}]}
        self.history = [{'state': 'approved', 'user': {'login': 'operator', 'type': 'User'},
                         'environments': [{'id': 7, 'name': 'collector-c3-operational-v2'}]}]

    def verify(self, environment=None, history=None, context=None):
        return legacy.verify_protected_review(
            self.context if context is None else context,
            self.environment if environment is None else environment,
            self.history if history is None else history,
            environment_name='collector-c3-operational-v2', approved_by='operator')

    def test_same_actual_review_logic_accepts_explicit_environment_name(self):
        self.assertEqual(self.verify(), 'operator')

    def test_wrong_environment_reviewer_rejection_and_ambiguous_history_deny(self):
        for env, history in [(dict(self.environment, name='other'), self.history),
                             (dict(self.environment, protection_rules=[]), self.history),
                             (self.environment, []), (self.environment, self.history*2)]:
            with self.subTest(environment=env, history=history), self.assertRaises(ValueError):
                self.verify(env, history)
        for field, value in [('state', 'rejected'), ('user', {'login': 'foreign', 'type': 'User'}),
                             ('environments', [{'id': 8, 'name': 'collector-c3-operational-v2'}])]:
            history = copy.deepcopy(self.history)
            history[0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.verify(history=history)

    def test_existing_self_review_policy_is_not_weakened(self):
        with self.assertRaises(ValueError):
            self.verify(context={'actor': 'operator'})


if __name__ == '__main__':
    unittest.main()
