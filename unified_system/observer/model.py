"""Observer-owned observation codec; never an admission or authority codec."""
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import hashlib
import ipaddress
import json
import re


class ObserverError(ValueError):
    pass


NODES = ('LS5', 'PC4', 'PC3', 'PC2', 'PC1', 'LS7')
AXES = ('LAN_REACHABLE', 'SSH_AUTHENTICATED', 'TOKEN_QUALIFIED', 'PACKAGE_VERIFIED',
        'INSTALLED', 'SERVICE_RUNNING', 'API_HEALTHY', 'WORKER_REGISTERED',
        'JOB_EXECUTING', 'STORAGE_HEALTHY', 'PHYSICAL_ACCEPTED')
STATES = frozenset(('PASS', 'FAIL', 'BLOCKED', 'UNKNOWN', 'STALE'))
FIELDS = {
    'computers': frozenset(AXES),
    'services': frozenset(('SERVICE_RUNNING', 'API_HEALTHY')),
    'market_data': frozenset(('POSTGRESQL_HEALTH', 'SCHEMA_MIGRATION', 'RAW_ARCHIVE',
        'LIVE_COLLECTOR', 'HISTORICAL_BACKFILL', 'INSTRUMENTS_TRACKED', 'LAST_EVENT',
        'DATASET_COVERAGE', 'GAP_COUNT', 'DISK_USAGE', 'CHECKPOINT_RECOVERY',
        'VERIFIED_PUBLICATION')),
    'development': frozenset(('AGENT_STATE', 'LATEST_CHANGE', 'INTEGRATION_CANDIDATE',
        'A8_REVIEW', 'BLOCKER', 'NEXT_MILESTONE', 'OPERATOR_DECISION', 'MISSION_SEQUENCE', 'MISSION_PROGRESS')),
    'ci': frozenset(('RUN_STATUS', 'PR_STATUS')),
    'acceptance': frozenset(('MILESTONE', 'A8_REVIEW', 'BLOCKER')),
}
EVENT_KINDS = frozenset(('MILESTONE_PASS', 'PHYSICAL_NODE_ADMITTED', 'NODE_DISCONNECTED',
    'SERVICE_STOPPED', 'CI_FAILURE', 'NEW_BLOCKER', 'OPERATOR_DECISION_REQUIRED',
    'DATA_CAPTURE_STOPPED', 'RESOURCE_WARNING', 'DAILY_SUMMARY', 'SOURCE_UNAVAILABLE'))


def need(value, code='OBSERVER_INPUT_REJECTED'):
    if not value:
        raise ObserverError(code)


def utc(value):
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            raise ObserverError('INVALID_TIMESTAMP') from None
    need(type(value) is datetime and value.tzinfo is not None and value.utcoffset() is not None,
         'UTC_TIMESTAMP_REQUIRED')
    return value.astimezone(timezone.utc)


def stamp(value):
    return utc(value).isoformat().replace('+00:00', 'Z')


def version(value):
    need(type(value) is str and re.fullmatch(r'(?:[a-f0-9]{40}|[a-f0-9]{64})', value),
         'EXACT_SOURCE_VERSION_REQUIRED')
    return value


def label(value):
    need(type(value) is str and 1 <= len(value) <= 96 and
         re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9 _.#:/-]*', value), 'UNSAFE_LABEL')
    need(not any(c in value for c in ('=', '\\', '@')) and '://' not in value and
         not value.startswith('/') and not re.search(r'[A-Za-z]:[/\\]', value), 'PRIVATE_LABEL')
    need(not re.search(r'(?i)token|secret|password|credential|private.key', value), 'SECRET_LABEL')
    need(not re.search(r'(?i)(?:gh[pousr]_|github_pat_|sk-)[A-Za-z0-9_-]{12,}|[0-9]{5,}:[A-Za-z0-9_-]{20,}', value), 'SECRET_LABEL')
    for match in re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', value):
        try:
            ipaddress.ip_address(match)
        except ValueError:
            continue
        raise ObserverError('ADDRESS_LABEL')
    need(not re.search(r'(?:^|[^A-Fa-f0-9])(?:[A-Fa-f0-9]{1,4}:){2}', value), 'ADDRESS_LABEL')
    return value


def integer(value, maximum=10**15):
    need(type(value) is int and 0 <= value <= maximum, 'BOUNDED_INTEGER_REQUIRED')
    return value


def pairs(values):
    result = {}
    for key, value in values:
        need(key not in result, 'DUPLICATE_JSON_KEY')
        result[key] = value
    return result


def decode(raw):
    need(type(raw) is bytes and 0 < len(raw) <= 1048576, 'SOURCE_BYTE_LIMIT')
    try:
        return json.loads(raw, object_pairs_hook=pairs,
                          parse_constant=lambda _: need(False, 'NONFINITE_JSON'))
    except (UnicodeError, ValueError, RecursionError) as exc:
        if isinstance(exc, ObserverError):
            raise
        raise ObserverError('SOURCE_JSON_REJECTED') from None


@dataclass(frozen=True)
class SourcePolicy:
    source_id: str
    kind: str
    source_version: str
    admitted_axes: frozenset = frozenset()
    ttl_seconds: int = 300
    interval_seconds: int = 60
    mode: str = 'SYNTHETIC'

    def __post_init__(self):
        label(self.source_id); version(self.source_version)
        need(re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,31}', self.source_id), 'SOURCE_ID_REQUIRED')
        need(self.kind in ('snapshot', 'github', 'supervisor_status', 'node_health',
             'storage_status', 'mission_projection', 'a8_acceptance'), 'SOURCE_KIND')
        need(type(self.admitted_axes) is frozenset and self.admitted_axes <=
             frozenset().union(*FIELDS.values()), 'SOURCE_AXIS_POLICY')
        need(type(self.ttl_seconds) is int and 1 <= self.ttl_seconds <= 86400, 'SOURCE_TTL')
        need(type(self.interval_seconds) is int and 15 <= self.interval_seconds <= 3600,
             'SOURCE_INTERVAL')
        need(self.mode in ('SYNTHETIC', 'UNQUALIFIED', 'QUALIFIED'), 'SOURCE_MODE')


@dataclass(frozen=True)
class Fact:
    section: str
    subject: str
    field: str
    status: str
    observed_at: str
    source: str
    version: str
    digest: str
    ttl_seconds: int
    scope: str
    mode: str
    value: object = None

    @property
    def key(self):
        return '/'.join((self.section, self.subject, self.field))


def safe_value(field, value):
    if value is None:
        return None
    if field in AXES or field in ('POSTGRESQL_HEALTH', 'SCHEMA_MIGRATION', 'RAW_ARCHIVE',
                                  'LIVE_COLLECTOR'):
        return None  # Source-specific bodies and diagnostics never enter public views.
    if field in ('GAP_COUNT', 'MISSION_SEQUENCE'):
        return integer(value)
    if field == 'MISSION_PROGRESS':
        need(type(value) is dict and set(value) == {'task_count','axis_counts','continuation_counts','root_task'}, 'MISSION_PROGRESS_SHAPE')
        integer(value['task_count'],1024)
        axes=('source','tested','integrated','windows','physical');states=('UNKNOWN','PASS','FAIL','BLOCKED')
        need(type(value['axis_counts']) is dict and set(value['axis_counts'])==set(axes), 'MISSION_AXES')
        for counts in value['axis_counts'].values():
            need(type(counts) is dict and set(counts)==set(states), 'MISSION_AXIS_COUNTS')
            for count in counts.values():integer(count,1024)
        counts=value['continuation_counts']
        need(type(counts) is dict and set(counts)=={'TODO','IN_PROGRESS','BLOCKED','COMPLETE','UNKNOWN'},'CONTINUATION_COUNTS')
        for count in counts.values():integer(count,1024)
        root=value['root_task']
        if root is not None:
            need(type(root) is dict and set(root)=={'id','axes','continuation_status','next_milestone','source_head','evidence_sha256','operator_decision_required'} and root['id']=='ROOT.LEVEL2.LS5','ROOT_TASK_VIEW')
            need(type(root['axes']) is dict and set(root['axes'])==set(axes) and all(v in states for v in root['axes'].values()),'ROOT_TASK_AXES')
            need(root['continuation_status'] in counts and type(root['operator_decision_required']) is bool,'ROOT_CONTINUATION')
            if root['next_milestone'] is not None:need(type(root['next_milestone']) is str and re.fullmatch('[A-Z][A-Z0-9_]{0,95}',root['next_milestone']),'NEXT_MILESTONE_ID')
            if root['source_head'] is not None:version(root['source_head'])
            if root['evidence_sha256'] is not None:need(type(root['evidence_sha256']) is str and re.fullmatch('[a-f0-9]{64}',root['evidence_sha256']),'ROOT_EVIDENCE_DIGEST')
        return value
    if field == 'LAST_EVENT':
        return stamp(value)
    if field in ('LATEST_CHANGE', 'INTEGRATION_CANDIDATE'):
        return version(value)
    if field == 'INSTRUMENTS_TRACKED':
        need(type(value) is list and len(value) <= 100 and all(type(v) is str and
             re.fullmatch('[A-Z0-9_-]{1,24}', v) for v in value), 'INSTRUMENTS')
        return sorted(set(value))
    if field in ('DATASET_COVERAGE', 'DISK_USAGE', 'HISTORICAL_BACKFILL'):
        need(type(value) is dict and set(value) == {'observed', 'total'}, 'METRIC_SHAPE')
        result = {k: integer(v) for k, v in value.items()}
        need(result['observed'] <= result['total'], 'METRIC_BOUNDS')
        return result
    if field == 'PR_STATUS':
        need(type(value) is dict and set(value) == {'number', 'state', 'draft', 'head'}, 'PR_SHAPE')
        integer(value['number']); version(value['head'])
        need(value['state'] in ('open', 'closed') and type(value['draft']) is bool, 'PR_STATE')
        return value
    if field == 'BLOCKER':
        need(type(value) is dict and set(value) == {'severity', 'code', 'owner'} and
             value['severity'] in ('P0', 'P1', 'P2'), 'BLOCKER_SHAPE')
        return {k: label(v) for k, v in value.items()}
    enums = {
        'AGENT_STATE': ('ACTIVE', 'IDLE', 'BLOCKED', 'BLOCKED_COMMUNICATION', 'UNKNOWN'),
        'RUN_STATUS': ('QUEUED', 'IN_PROGRESS', 'SUCCESS', 'FAILURE', 'CANCELLED', 'UNKNOWN'),
        'VERIFIED_PUBLICATION': ('LOCAL_UNATTESTED', 'COMMIT_UNCONFIRMED', 'COMMITTED', 'UNKNOWN'),
        'CHECKPOINT_RECOVERY': ('UNKNOWN', 'COMMIT_UNCONFIRMED', 'REOPENED', 'BLOCKED', 'NOT_RUN'),
        'A8_REVIEW': ('PENDING', 'SOURCE_ACK', 'SCOPED_PASS', 'REJECTED', 'NOT_RUN'),
    }
    if field in enums:
        need(value in enums[field], 'VALUE_ENUM')
        return value
    return label(value)


def parse_snapshot(raw, policy, now):
    data = decode(raw); now = utc(now)
    need(type(data) is dict and set(data) == {'schema', 'source_version', 'observed_at', 'facts'}
         and data['schema'] == 'unified.observer.source.v1', 'SOURCE_SCHEMA')
    need(data['source_version'] == policy.source_version, 'SOURCE_VERSION_CHANGED')
    observed = utc(data['observed_at'])
    need(observed <= now + timedelta(seconds=5), 'FUTURE_OBSERVATION')
    rows = data['facts']; need(type(rows) is list and len(rows) <= 256, 'SOURCE_FACT_LIMIT')
    digest = hashlib.sha256(raw).hexdigest(); result = []; seen = set()
    for row in rows:
        need(type(row) is dict and set(row) == {'section', 'subject', 'field', 'status', 'scope', 'value'}, 'FACT_SCHEMA')
        section, subject, field = row['section'], label(row['subject']), row['field']
        need(type(section) is str and type(field) is str and type(row['status']) is str and
             section in FIELDS and field in FIELDS[section] and row['status'] in STATES, 'FACT_FIELD')
        if section == 'computers': need(subject in NODES, 'OFFICE_NODE_REQUIRED')
        scope = row['scope']; need(type(scope) is str and scope in
            (frozenset().union(*FIELDS.values()) | {'UNKNOWN','UNQUALIFIED','UNVERIFIED_CONTROL_PLANE_OBSERVATION'}), 'FACT_SCOPE')
        value = safe_value(field, row['value']); status = row['status']
        if status == 'PASS' and (field not in policy.admitted_axes or scope != field):
            status = 'UNKNOWN'
        if field == 'PHYSICAL_ACCEPTED' and row['status'] == 'PASS' and not (
                policy.kind == 'a8_acceptance' and policy.mode == 'QUALIFIED' and
                field in policy.admitted_axes and scope == field):
            status = 'BLOCKED'
        if field == 'VERIFIED_PUBLICATION' and row['status'] == 'PASS' and not (
                value == 'COMMITTED' and policy.mode == 'QUALIFIED' and
                field in policy.admitted_axes and scope == field):
            status = 'BLOCKED'
        fact = Fact(section, subject, field, status, stamp(observed), policy.source_id,
                    policy.source_version, digest, policy.ttl_seconds, scope, policy.mode, value)
        need(fact.key not in seen, 'DUPLICATE_FACT'); seen.add(fact.key); result.append(fact)
    return result
