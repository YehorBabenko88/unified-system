"""Elevated-broker input: actual GitHub V2 review facts, never a host grant.

No CLI/dispatch/record writer exists. Runtime uses only the pure protected-record
codec; it must never receive this provider or its token.
"""
import hashlib
import json
import time
from scripts import ci_service_operational_admission as legacy
from unified_system import collector_operational_review as codec


class GitHubCollectorReviewProvider:
    __slots__ = ('_token',)

    def __init__(self, token):
        codec.need(type(token) is str and bool(token) and '\r' not in token and '\n' not in token)
        self._token = token

    def acquire(self, ctx):
        try:
            return self._acquire(ctx)
        except Exception:
            raise ValueError('COLLECTOR_OPERATIONAL_REVIEW_REJECTED') from None

    def _acquire(self, ctx):
        codec.fields(ctx, 'event repository sha source_sha attempt run_id actor authorization_commit authorization_sha256 job_name runner_name')
        codec.need(all(type(v) is str for v in ctx.values()))
        legacy.context_ok(ctx)
        codec.need(ctx['job_name'] == 'collector-c3')
        codec.text(ctx['runner_name'], r'[A-Za-z0-9 _.-]{1,128}')
        codec.text(ctx['actor'], r'[A-Za-z0-9-]{1,39}')
        started = time.time()
        receipts = {}

        def read(name, url, *, authorization=False):
            raw = legacy.get(url, self._token)
            receipts[name] = dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
            if authorization:
                return raw
            value = legacy.decode_json(raw)
            json.dumps(value, allow_nan=False)  # same duplicate guard; nonfinite remote data also denies
            return value

        api = 'https://api.github.com/repos/'+codec.REPOSITORY
        authorization_raw = read('authorization', 'https://raw.githubusercontent.com/'+codec.REPOSITORY+'/'+ctx['authorization_commit']+
                                 '/docs/collector/ci-collector-operational-intent-v2.json', authorization=True)
        codec.need(hashlib.sha256(authorization_raw).hexdigest() == ctx['authorization_sha256'])
        auth = codec.parse_authorization(authorization_raw)
        codec.need(auth['source']['head'] == ctx['sha'])
        run = read('run', api+'/actions/runs/'+ctx['run_id'])
        codec.need(type(run) is dict)
        codec.integer(run['id']); codec.integer(run['run_attempt'], 1, 1)
        codec.need(run['id'] == int(ctx['run_id']) and run['event'] == 'workflow_dispatch' and run['head_sha'] == ctx['sha'])
        codec.need(run['status'] == 'in_progress' and run['conclusion'] is None)
        codec.need(run['display_title'] == codec.dispatch_title(ctx['authorization_sha256'], ctx['authorization_commit']))
        codec.need(run['path'] == codec.WORKFLOW and run['repository']['full_name'] == codec.REPOSITORY and run['head_repository']['full_name'] == codec.REPOSITORY)
        codec.need(run['actor']['login'] == ctx['actor'] and run['triggering_actor']['login'] == ctx['actor'])
        commit = read('commit', api+'/git/commits/'+ctx['sha'])
        codec.need(type(commit) is dict and commit['sha'] == ctx['sha'] and commit['tree']['sha'] == auth['source']['tree'])
        jobs = read('jobs', api+'/actions/runs/'+ctx['run_id']+'/attempts/1/jobs')
        codec.need(type(jobs) is dict and type(jobs['jobs']) is list and type(jobs['total_count']) is int and jobs['total_count'] == len(jobs['jobs']))
        matches = [job for job in jobs['jobs'] if job.get('name') == auth['target']['job_name']]
        codec.need(len(matches) == 1)
        job = matches[0]
        for key in ('id', 'run_id', 'run_attempt', 'runner_id'):
            codec.integer(job[key])
        codec.need(job['run_id'] == run['id'] and job['run_attempt'] == 1 and job['head_sha'] == ctx['sha'])
        codec.need(job['status'] == 'in_progress' and job['conclusion'] is None and job['runner_name'] == ctx['runner_name'])
        codec.need(job['labels'] == [auth['target']['runner_label']] and type(job['runner_group_id']) is int and job['runner_group_id'] == 0 and job['runner_group_name'] == 'GitHub Actions')
        environment = read('environment', api+'/environments/'+codec.ENVIRONMENT)
        history = read('history', api+'/actions/runs/'+ctx['run_id']+'/approvals')
        codec.need(type(environment) is dict and type(history) is list)  # None never means V2 preflight
        legacy.verify_protected_review(ctx, environment, history, environment_name=codec.ENVIRONMENT, approved_by=auth['approved_by'])
        rules = [rule for rule in environment['protection_rules'] if rule.get('type') == 'required_reviewers']
        reviewers = [r['reviewer'] for r in rules[0]['reviewers'] if r['type'] == 'User' and r['reviewer'].get('login') == auth['approved_by']]
        codec.need(len(reviewers) == 1); reviewer = reviewers[0]; codec.integer(reviewer['id'])
        relevant = [row for row in history if any(e.get('id') == environment['id'] and e.get('name') == codec.ENVIRONMENT for e in row.get('environments', []))]
        matching_environments = [e for e in relevant[0]['environments'] if e.get('id') == environment['id'] and e.get('name') == codec.ENVIRONMENT]
        codec.need(len(matching_environments) == 1); codec.integer(matching_environments[0]['id'])
        codec.need(relevant[0]['user']['id'] == reviewer['id']); codec.integer(relevant[0]['user']['id'])
        facts = dict(schema=codec.REVIEW_SCHEMA, scope=codec.SCOPE,
                     authorization_id=auth['authorization_id'], authorization_sha256=ctx['authorization_sha256'],
                     authorization_commit=ctx['authorization_commit'], cohort_id=auth['cohort_id'], source=auth['source'],
                     run=dict(id=run['id'], attempt=1, event='workflow_dispatch', workflow=run['path'], head=run['head_sha'],
                              tree=commit['tree']['sha'], actor=ctx['actor'], created_at=run['created_at'],
                              display_title=run['display_title'], status=run['status'], conclusion=run['conclusion']),
                     job=dict(id=job['id'], name=job['name'], runner_id=job['runner_id'], runner_name=job['runner_name'], runner_label=auth['target']['runner_label']),
                     environment=dict(id=environment['id'], name=codec.ENVIRONMENT, required_reviewer_id=reviewer['id']),
                     reviewer=dict(id=reviewer['id'], login=auth['approved_by']), expires_at=auth['expires_at'], response_bodies=receipts)
        codec.need(time.time() >= started)
        raw = codec.encode(facts)
        codec.parse_review(raw, authorization_raw)  # repeat expiry and all cross-record joins
        return raw
