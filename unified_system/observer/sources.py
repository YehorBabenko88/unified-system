"""Bounded, explicit read-only inputs. No SSH or direct database adapter."""
from dataclasses import replace
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from .model import ObserverError, SourcePolicy, decode, integer, need, parse_snapshot, stamp, version
from .store import ObserverStore, ordinary

REPOSITORIES = frozenset('YehorBabenko88/' + name for name in (
    'unified-system', 'bybit-cluster-grid', 'strattester', 'Terminan', 'math', 'meta_analyse'))


class SnapshotSource:
    def __init__(self, policy, path):
        need(type(policy) is SourcePolicy, 'SOURCE_POLICY_REQUIRED')
        self.policy, self.path = policy, Path(path)
        need(self.path.is_absolute(), 'ABSOLUTE_SNAPSHOT_REQUIRED')

    def read_bytes(self):
        ordinary(self.path, False); before = self.path.stat()
        need(0 < before.st_size <= 1048576, 'SOURCE_BYTE_LIMIT')
        with self.path.open('rb') as stream:
            raw = stream.read(1048577)
        after = self.path.stat()
        need(len(raw) == before.st_size and (before.st_ino, before.st_size, before.st_mtime_ns) ==
             (after.st_ino, after.st_size, after.st_mtime_ns), 'SNAPSHOT_CHANGED')
        return raw

    def read(self, now):
        return parse_snapshot(self.read_bytes(), self.policy, now)


class MissionProjectionSource(SnapshotSource):
    """Exported JSON only. Never calls MissionController.open or sqlite on input."""
    def read(self, now):
        raw = self.read_bytes(); data = decode(raw)
        need(type(data) is dict and set(data) == {'schema', 'source_version', 'observed_at', 'projection'}
             and data['schema'] == 'unified.observer.mission-export.v1', 'MISSION_EXPORT_SCHEMA')
        projection = data['projection']
        need(type(projection) is dict and type(projection.get('tasks')) is dict, 'MISSION_PROJECTION')
        integer(projection['sequence'])
        need(len(projection['tasks']) <= 1024, 'MISSION_TASK_BOUND')
        if 'continuation_sequence' in projection:
            need(projection['continuation_sequence'] == projection['sequence'], 'MISSION_EXPORT_SEQUENCE_CONFLICT')
        axes=('source','tested','integrated','windows','physical');states=('UNKNOWN','PASS','FAIL','BLOCKED')
        axis_counts={axis:dict.fromkeys(states,0) for axis in axes}
        for task in projection['tasks'].values():
            need(type(task) is dict, 'MISSION_TASK_ROW')
            source_axes=task.get('axes',{})
            need(type(source_axes) is dict, 'MISSION_TASK_AXES')
            for axis in axes:
                state=source_axes.get(axis,'UNKNOWN')
                need(state in states,'MISSION_AXIS_STATE');axis_counts[axis][state]+=1
        continuations=projection.get('continuations',{})
        need(type(continuations) is dict and len(continuations)<=1024,'MISSION_CONTINUATION_BOUND')
        continuation_counts=dict.fromkeys(('TODO','IN_PROGRESS','BLOCKED','COMPLETE','UNKNOWN'),0)
        for record in continuations.values():
            need(type(record) is dict and type(record.get('metadata',{})) is dict,'MISSION_CONTINUATION_ROW')
            state=record.get('metadata',{}).get('status','UNKNOWN')
            need(state in continuation_counts,'MISSION_CONTINUATION_STATE');continuation_counts[state]+=1
        root_view=None
        if 'ROOT.LEVEL2.LS5' in projection['tasks']:
            task=projection['tasks']['ROOT.LEVEL2.LS5'];metadata=continuations.get('ROOT.LEVEL2.LS5',{}).get('metadata',{})
            step=metadata.get('next_executable_step',{}).get('step_id')
            if type(step) is not str or not re.fullmatch('[A-Z][A-Z0-9_]{0,95}',step):step=None
            evidence=metadata.get('evidence',[])
            need(type(evidence) is list and len(evidence)<=128,'MISSION_EVIDENCE_BOUND')
            last_digest=evidence[-1].get('sha256') if evidence and type(evidence[-1]) is dict else None
            root_view={'id':'ROOT.LEVEL2.LS5','axes':{axis:task.get('axes',{}).get(axis,'UNKNOWN') for axis in axes},
                'continuation_status':metadata.get('status','UNKNOWN'),'next_milestone':step,
                'source_head':metadata.get('source_head'),'evidence_sha256':last_digest,
                'operator_decision_required':bool(metadata.get('required_authorization',[]))}
        progress={'task_count':len(projection['tasks']),'axis_counts':axis_counts,
                  'continuation_counts':continuation_counts,'root_task':root_view}
        document = {'schema':'unified.observer.source.v1', 'source_version':data['source_version'],
            'observed_at':data['observed_at'], 'facts':[{'section':'development', 'subject':'Master Mission',
            'field':'MISSION_SEQUENCE', 'scope':'MISSION_SEQUENCE', 'status':'UNKNOWN',
            'value':projection['sequence']}]}
        document['facts'].append({'section':'development','subject':'Master Mission','field':'MISSION_PROGRESS',
            'scope':'MISSION_PROGRESS','status':'UNKNOWN','value':progress})
        facts = parse_snapshot(json.dumps(document).encode(), self.policy, now)
        return [replace(f, digest=hashlib.sha256(raw).hexdigest()) for f in facts]


class ReadOnlyHTTPS:
    """Optional GET transport. Construction requires separate network admission.

    This boolean is configuration, not a native issuer or proof of token scopes.
    Physical admission must independently verify the read-only credential and URL.
    """
    def __init__(self, allowed_urls, *, network_admitted=False, token=None,
                 read_only_credential_confirmed=False, budget_store=None, clock=None):
        need(network_admitted is True, 'NETWORK_ADMISSION_REQUIRED')
        need(type(allowed_urls) is frozenset and 1 <= len(allowed_urls) <= 16, 'EXACT_URL_ALLOWLIST')
        for url in allowed_urls:
            parsed = urlsplit(url)
            need(parsed.scheme == 'https' and parsed.hostname == 'api.github.com' and
                 not parsed.username and not parsed.password and parsed.port in (None, 443) and
                 not parsed.fragment, 'READ_ONLY_GITHUB_URL_REQUIRED')
            allowed = {'https://api.github.com/repos/' + repo + '/' + suffix for repo in REPOSITORIES
                for suffix in ('actions/runs?per_page=10', 'pulls?state=all&sort=updated&direction=desc&per_page=10')}
            need(url in allowed, 'READ_ONLY_SOURCE_URL_REQUIRED')
        need(token is None or (type(token) is str and 0 < len(token) <= 512 and
             read_only_credential_confirmed is True), 'READ_ONLY_CREDENTIAL_REQUIRED')
        need(type(budget_store) is ObserverStore, 'PERSISTENT_GITHUB_BUDGET_REQUIRED')
        from datetime import datetime, timezone
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._budget = budget_store
        self._urls, self._token = allowed_urls, token

    def __repr__(self): return '<Observer ReadOnlyHTTPS: credentials redacted>'

    def get(self, url):
        need(url in self._urls, 'URL_NOT_ADMITTED')
        self._budget.reserve_github(hashlib.sha256(url.encode()).hexdigest(), self._clock())
        import ssl
        import time
        import urllib.request
        import urllib.error
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs): return None
        headers = {'Accept':'application/vnd.github+json', 'User-Agent':'Unified-Observer/1',
                   'X-GitHub-Api-Version':'2022-11-28'}
        if self._token: headers['Authorization'] = 'Bearer ' + self._token
        request = urllib.request.Request(url, method='GET', headers=headers)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect(),
            urllib.request.HTTPSHandler(context=ssl.create_default_context()))
        try:
            deadline = time.monotonic() + 8
            with opener.open(request, timeout=3) as response:
                need(response.status == 200, 'REMOTE_SOURCE_STATUS')
                if response.headers.get('X-RateLimit-Remaining') == '0':
                    self._cooldown(response.headers)
                chunks = []; total = 0
                while True:
                    need(time.monotonic() <= deadline, 'REMOTE_SOURCE_OBSERVED_DEADLINE')
                    block = response.read1(min(65536, 1048577-total))
                    if not block: break
                    chunks.append(block); total += len(block)
                    need(total <= 1048576, 'SOURCE_BYTE_LIMIT')
                raw = b''.join(chunks)
                need(0 < len(raw) <= 1048576, 'SOURCE_BYTE_LIMIT')
                return raw
        except urllib.error.HTTPError as error:
            if error.code in (403, 429): self._cooldown(error.headers)
            error.close()
            raise ObserverError('REMOTE_SOURCE_UNAVAILABLE') from None
        except Exception:
            raise ObserverError('REMOTE_SOURCE_UNAVAILABLE') from None

    def _cooldown(self, headers):
        # Unknown/malformed reset information waits one hour; never retry here.
        from email.utils import parsedate_to_datetime
        from .model import utc
        now = self._clock(); wait = 3600
        for key in ('Retry-After', 'X-RateLimit-Reset'):
            value = headers.get(key)
            if not isinstance(value, str) or len(value) > 128: continue
            try:
                if value.isdigit():
                    seconds = int(value) - (int(utc(now).timestamp()) if key.endswith('Reset') else 0)
                elif key == 'Retry-After':
                    seconds = int((parsedate_to_datetime(value)-utc(now)).total_seconds())
                else: continue
                wait = max(wait, min(604800, seconds))
            except (ValueError, OverflowError, TypeError): pass
        self._budget.cooldown_github(now, wait)


class GitHubSource:
    def __init__(self, policy, repository, *, view='runs', client=None):
        need(policy.kind == 'github' and repository in REPOSITORIES and view in ('runs', 'pulls'), 'GITHUB_SOURCE')
        need(policy.interval_seconds >= 60, 'GITHUB_POLL_INTERVAL')
        self.policy, self.repository, self.view, self.client = policy, repository, view, client
        suffix = 'actions/runs?per_page=10' if view == 'runs' else 'pulls?state=all&sort=updated&direction=desc&per_page=10'
        self.url = 'https://api.github.com/repos/' + repository + '/' + suffix

    def read(self, now):
        need(self.client is not None, 'NETWORK_ADMISSION_REQUIRED')
        raw = self.client.get(self.url); data = decode(raw)
        rows = data.get('workflow_runs') if self.view == 'runs' and type(data) is dict else data
        need(type(rows) is list and len(rows) <= 10, 'GITHUB_PAGE_BOUND')
        result = []
        for row in rows:
            need(type(row) is dict, 'GITHUB_ROW')
            if self.view == 'runs':
                identifier = integer(row['id']); target = version(row['head_sha'])
                conclusion, state = row.get('conclusion'), row.get('status')
                value = ('SUCCESS' if conclusion == 'success' else 'FAILURE' if conclusion in
                    ('failure', 'timed_out', 'action_required', 'startup_failure') else
                    'CANCELLED' if conclusion == 'cancelled' else 'QUEUED' if state in
                    ('queued', 'requested', 'pending', 'waiting') else 'IN_PROGRESS' if
                    state == 'in_progress' else 'UNKNOWN')
                status = 'PASS' if value == 'SUCCESS' else 'FAIL' if value == 'FAILURE' else 'UNKNOWN'
                section, field = 'ci', 'RUN_STATUS'
            else:
                identifier = integer(row['number']); target = version(row['head']['sha'])
                need(type(row.get('draft')) is bool and row.get('state') in ('open', 'closed'), 'GITHUB_PR')
                value = {'number':identifier, 'state':row['state'], 'draft':row['draft'], 'head':target}
                status, section, field = 'UNKNOWN', 'ci', 'PR_STATUS'
            document = {'schema':'unified.observer.source.v1', 'source_version':self.policy.source_version,
                'observed_at':stamp(now), 'facts':[{'section':section, 'subject':self.repository + '#' + str(identifier),
                'field':field, 'scope':field, 'status':status, 'value':value}]}
            facts = parse_snapshot(json.dumps(document).encode(), self.policy, now)
            result.extend(replace(f, version=target, digest=hashlib.sha256(raw).hexdigest()) for f in facts)
        return result


class SupervisorStatusSource:
    """Consume existing unverified status API without turning it into node admission."""
    def __init__(self, policy, *, reader=None):
        need(policy.kind == 'supervisor_status', 'SUPERVISOR_POLICY')
        self.policy, self.reader = policy, reader

    def read(self, now):
        need(self.reader is not None, 'STATUS_ENDPOINT_ADMISSION_REQUIRED')
        raw = self.reader(); data = decode(raw)
        need(type(data) is dict and data.get('producer') == 'unified-system' and
             data.get('read_only') is True and data.get('trading_authorized') is False,
             'EXISTING_SUPERVISOR_STATUS_REQUIRED')
        document = {'schema':'unified.observer.source.v1', 'source_version':self.policy.source_version,
            'observed_at':stamp(now), 'facts':[{'section':'services', 'subject':'Supervisor',
            'field':'API_HEALTHY', 'scope':'UNVERIFIED_CONTROL_PLANE_OBSERVATION',
            'status':'UNKNOWN', 'value':None}]}
        return [replace(f, digest=hashlib.sha256(raw).hexdigest()) for f in
                parse_snapshot(json.dumps(document).encode(), self.policy, now)]
