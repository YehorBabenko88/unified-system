"""Fail-closed, read-only admission for the legacy hosted stopped-service lane."""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import time
from urllib.request import HTTPRedirectHandler, Request, build_opener

REPOSITORY = 'YehorBabenko88/unified-system'
WORKFLOW = '.github/workflows/lab-stopped-service.yml'
ENVIRONMENT = 'collector-c3-stopped-service'
MATRIX = ('windows-2022', 'windows-2025')
EFFECTS = ('hosted-disposable-service-register-stopped', 'hosted-disposable-acl',
           'hosted-disposable-app-only-removal')
LIMIT = 65536


def need(condition):
    if not condition:
        raise ValueError('C3_OPERATIONAL_ADMISSION_BLOCKED')


def decode_json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            need(key not in result)
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique)


def context_ok(ctx):
    need(ctx['event'] == 'workflow_dispatch' and ctx['repository'] == REPOSITORY)
    need(ctx['attempt'] == '1' and re.fullmatch(r'[1-9][0-9]*', ctx['run_id']))
    need(re.fullmatch(r'[0-9a-f]{40}', ctx['sha']) and ctx['source_sha'] == ctx['sha'])
    need(re.fullmatch(r'[0-9a-f]{40}', ctx['authorization_commit']))
    need(re.fullmatch(r'[0-9a-f]{64}', ctx['authorization_sha256']))


def validate(ctx, raw, environment, history=None, *, now=None):
    context_ok(ctx)
    need(0 < len(raw) <= LIMIT and hashlib.sha256(raw).hexdigest() == ctx['authorization_sha256'])
    record = decode_json(raw)
    expected = dict(status='APPROVED', SourceKind='explicit_operator_record',
                    repository=REPOSITORY, source_sha=ctx['sha'], workflow=WORKFLOW,
                    environment=ENVIRONMENT, matrix=list(MATRIX), permissions=list(EFFECTS), attempt=1)
    need(set(record) == set(expected) | {'approved_by', 'expires_at'})
    need(all(type(record[k]) is type(v) and record[k] == v for k, v in expected.items()))
    need(isinstance(record['approved_by'], str) and re.fullmatch(r'[A-Za-z0-9-]{1,39}', record['approved_by']))
    expiry = datetime.datetime.strptime(record['expires_at'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc).timestamp()
    now = time.time() if now is None else now
    need(now < expiry <= now + 86400)
    return verify_protected_review(ctx, environment, history, environment_name=ENVIRONMENT, approved_by=record['approved_by'])


def verify_protected_review(ctx, environment, history, *, environment_name, approved_by):
    """Existing review checks only; None history preserves legacy preflight semantics."""
    need(environment.get('name') == environment_name and type(environment.get('id')) is int)
    rules = [r for r in environment.get('protection_rules', []) if r.get('type') == 'required_reviewers']
    need(len(rules) == 1)
    reviewers = rules[0].get('reviewers', [])
    need(reviewers and all(r.get('type') == 'User' for r in reviewers))
    need(approved_by in [r['reviewer']['login'] for r in reviewers])
    need(type(rules[0].get('prevent_self_review')) is bool)
    if rules[0]['prevent_self_review']:
        need(bool(ctx.get('actor')) and approved_by.lower() != ctx['actor'].lower())
    if history is not None:
        need(isinstance(history, list))
        relevant = [r for r in history if any(e.get('id') == environment['id'] and e.get('name') == environment_name for e in r.get('environments', []))]
        # No ordering assumption, rejected or ambiguous histories cannot admit.
        need(len(relevant) == 1)
        review = relevant[0]
        need(review.get('state') == 'approved' and review.get('user', {}).get('type') == 'User')
        need(review['user'].get('login') == approved_by)
    return approved_by

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args):
        raise ValueError('C3_OPERATIONAL_ADMISSION_BLOCKED')


def get(url, token, *, opener=None):
    need(url.startswith('https://api.github.com/repos/'+REPOSITORY+'/') or
         url.startswith('https://raw.githubusercontent.com/'+REPOSITORY+'/'))
    headers = {'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
    if token:
        headers['Authorization'] = 'Bearer '+token
    opener = build_opener(NoRedirect()) if opener is None else opener
    with opener.open(Request(url, headers=headers, method='GET'), timeout=20) as response:
        need(response.geturl() == url and response.status == 200 and not response.headers.get('Link'))
        raw = response.read(LIMIT + 1)
    need(0 < len(raw) <= LIMIT)
    return raw


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', choices=('preflight', 'review'), required=True)
    args = parser.parse_args()
    ctx = {key: os.environ.get(value, '') for key, value in dict(
        event='GITHUB_EVENT_NAME', repository='GITHUB_REPOSITORY', sha='GITHUB_SHA', actor='GITHUB_ACTOR',
        attempt='GITHUB_RUN_ATTEMPT', run_id='GITHUB_RUN_ID', source_sha='CI_SOURCE_SHA',
        authorization_commit='CI_AUTHORIZATION_COMMIT', authorization_sha256='CI_AUTHORIZATION_SHA256').items()}
    try:
        context_ok(ctx)  # ordinary source events deny before any HTTP call
        token = os.environ.get('GH_TOKEN', '')
        raw = get('https://raw.githubusercontent.com/'+REPOSITORY+'/'+ctx['authorization_commit']+
                  '/docs/collector/ci-operational-authorization.json', token)
        api = 'https://api.github.com/repos/'+REPOSITORY
        environment = decode_json(get(api+'/environments/'+ENVIRONMENT, token))
        history = None if args.phase == 'preflight' else decode_json(get(api+'/actions/runs/'+ctx['run_id']+'/approvals', token))
        if args.phase == 'review':
            need(isinstance(history, list))
        validate(ctx, raw, environment, history)
        if args.phase == 'preflight':
            with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as stream:
                stream.write('admitted=true\n')
        print('C3_OPERATIONAL_ADMISSION_PREREQUISITES_VALID' if history is None else 'C3_OPERATIONAL_ADMISSION_REVIEW_VERIFIED')
        print('This admission result is not C3 acceptance PASS.')
        return 0
    except Exception:
        # No response/token/record content is printed on failure.
        print('::error::C3_OPERATIONAL_ADMISSION_BLOCKED; native acceptance remains BLOCKED, not PASS')
        return 1


if __name__ == '__main__':
    sys.exit(main())
