"""Canonical V2 review facts only: no HTTP, token, issuer or execution grant."""
import datetime
import hashlib
import re
import time
import uuid
from .service_bootstrap import canonical, parse

LIMIT = 65536
REPOSITORY = 'YehorBabenko88/unified-system'
WORKFLOW = '.github/workflows/lab-stopped-service.yml'
ENVIRONMENT = 'collector-c3-operational-v2'
SCOPE = 'ADMISSION_FOR_C3_QUALIFICATION'
AUTHORIZATION_SCHEMA = 'unified.collector.operational-authorization.v2'
REVIEW_SCHEMA = 'unified.collector.verified-github-review.v2'
RESOLVED_SCHEMA = 'unified.collector.resolved-operation-intent.v2'
GRAPH = 'COLLECTOR_C3_FINITE_SYNTHETIC_V2'
STAGES = ('REGISTER_STOPPED', 'PUBLISH_ACTIVATION', 'START', 'STOP', 'INSPECT_STOPPED', 'REVOKE_ACTIVATION')
SERVICE_POLICY = 'UNIFIED_COLLECTOR_V2_INSTALLATION_UUID_SHA256_24'
EVIDENCE = dict(source_schema='unified.collector.source-admission.v2', capacity_schema='unified.collector.capacity-admission.v2', resource_schema='unified.collector.resource-outcome.v2', scope=SCOPE)


def need(ok):
    if not ok:
        raise ValueError('COLLECTOR_OPERATIONAL_REVIEW_REJECTED')


def fields(value, names):
    need(type(value) is dict and set(value) == set(names.split()))


def text(value, pattern):
    need(type(value) is str and re.fullmatch(pattern, value) is not None)


def integer(value, low=1, high=2**63-1):
    need(type(value) is int and low <= value <= high)


def digest(value, length=64):
    text(value, '[a-f0-9]{'+str(length)+'}')


def identifier(value):
    need(type(value) is str and str(uuid.UUID(value)) == value)


def timestamp(value):
    text(value, r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z')
    return datetime.datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc).timestamp()


def decode(raw):
    need(type(raw) is bytes and 0 < len(raw) <= LIMIT)
    return parse(raw)  # existing duplicate-free, finite, canonical-LF decoder


def encode(value):
    raw = canonical(value)
    need(0 < len(raw) <= LIMIT)
    return raw


def parse_authorization(raw, *, now=None):
    auth = decode(raw)
    fields(auth, 'schema scope authorization_id cohort_id source capsule target graph_profile evidence_requirements bounds issued_at expires_at approved_by')
    need(auth['schema'] == AUTHORIZATION_SCHEMA and auth['scope'] == SCOPE and auth['graph_profile'] == GRAPH)
    identifier(auth['authorization_id']); identifier(auth['cohort_id']); text(auth['approved_by'], r'[A-Za-z0-9-]{1,39}')
    source = auth['source']; fields(source, 'head tree source_manifest_sha256')
    digest(source['head'], 40); digest(source['tree'], 40); digest(source['source_manifest_sha256'])
    capsule = auth['capsule']; fields(capsule, 'manifest_sha256 manifest_bytes archive')
    digest(capsule['manifest_sha256']); integer(capsule['manifest_bytes'])
    archive = capsule['archive']; need(type(archive) is dict)
    if archive.get('kind') == 'UNPACKED_MANIFEST_ONLY':
        fields(archive, 'kind')
    else:
        fields(archive, 'kind sha256 bytes'); need(archive['kind'] == 'ARCHIVE'); digest(archive['sha256']); integer(archive['bytes'])
    target = auth['target']; fields(target, 'runner_label job_name installation_id service_name_policy root_relative_runner_temp')
    need(type(target['runner_label']) is str and target['runner_label'] in ('windows-2022', 'windows-2025'))
    need(target['job_name'] == 'collector-c3' and target['service_name_policy'] == SERVICE_POLICY)
    identifier(target['installation_id']); need(target['root_relative_runner_temp'] == 'unified-collector-c3/'+target['installation_id'])
    fields(auth['evidence_requirements'], 'source_schema capacity_schema resource_schema scope'); need(auth['evidence_requirements'] == EVIDENCE)
    bounds = auth['bounds']; fields(bounds, 'workers capture_attempts frames frame_bytes raw_bytes duration_seconds capacity_max_age_seconds stop_policy')
    for key, high in [('workers', 1), ('capture_attempts', 1), ('frames', 4), ('frame_bytes', 1048576), ('raw_bytes', 4194304), ('duration_seconds', 120)]:
        integer(bounds[key], 1, high)
    need(bounds['raw_bytes'] >= bounds['frame_bytes'])
    stop = bounds['stop_policy']; fields(stop, 'transport console skip_methods kill_process_tree console_grace_ms owner_retire_seconds actuation_timeout_seconds')
    need(type(stop['transport']) is str and stop['transport'] == 'NSSM_CONSOLE_CTRL_C_V1')
    for key, value in [('console', 0), ('skip_methods', 6), ('kill_process_tree', 0), ('owner_retire_seconds', 5)]:
        integer(stop[key], value, value)
    integer(stop['console_grace_ms']); integer(stop['actuation_timeout_seconds'], 1, 60)
    need(stop['console_grace_ms']+5000 < stop['actuation_timeout_seconds']*1000 <= 60000)
    issued = timestamp(auth['issued_at']); expires = timestamp(auth['expires_at']); current = time.time() if now is None else now
    need(issued <= current < expires <= issued+86400)
    integer(bounds['capacity_max_age_seconds'], 1, int(expires-issued))
    return auth


def derived_service_name(auth):
    raw = canonical(dict(domain='unified.owned-collector-stopped-service.v2', installation_id=auth['target']['installation_id']))
    return 'UnifiedCollector_'+hashlib.sha256(raw).hexdigest()[:24]


def dispatch_title(authorization_sha256, authorization_commit):
    digest(authorization_sha256); digest(authorization_commit, 40)
    return 'collector-c3-operational-v2 '+authorization_sha256+' '+authorization_commit


def parse_review(raw, authorization_raw, *, now=None):
    """Facts/joins only; trusted protected issuance and live facts remain A5's job."""
    auth = parse_authorization(authorization_raw, now=now); review = decode(raw)
    fields(review, 'schema scope authorization_id authorization_sha256 authorization_commit cohort_id source run job environment reviewer expires_at response_bodies')
    need(review['schema'] == REVIEW_SCHEMA and review['scope'] == SCOPE)
    need(review['authorization_sha256'] == hashlib.sha256(authorization_raw).hexdigest()); digest(review['authorization_commit'], 40)
    for key in ('authorization_id', 'cohort_id', 'source', 'expires_at'):
        need(review[key] == auth[key])
    run = review['run']; fields(run, 'id attempt event workflow head tree actor created_at display_title status conclusion')
    integer(run['id']); integer(run['attempt'], 1, 1); need(run['event'] == 'workflow_dispatch' and run['workflow'] == WORKFLOW)
    need(run['status'] == 'in_progress' and run['conclusion'] is None)
    need(run['display_title'] == dispatch_title(review['authorization_sha256'], review['authorization_commit']))
    need(run['head'] == auth['source']['head'] and run['tree'] == auth['source']['tree']); text(run['actor'], r'[A-Za-z0-9-]{1,39}')
    need(timestamp(auth['issued_at']) <= timestamp(run['created_at']) < timestamp(auth['expires_at']))
    job = review['job']; fields(job, 'id name runner_id runner_name runner_label')
    integer(job['id']); integer(job['runner_id']); text(job['runner_name'], r'[A-Za-z0-9 _.-]{1,128}')
    need(job['name'] == auth['target']['job_name'] and job['runner_label'] == auth['target']['runner_label'])
    environment = review['environment']; fields(environment, 'id name required_reviewer_id')
    integer(environment['id']); integer(environment['required_reviewer_id']); need(environment['name'] == ENVIRONMENT)
    reviewer = review['reviewer']; fields(reviewer, 'id login'); integer(reviewer['id'])
    need(reviewer['id'] == environment['required_reviewer_id'] and reviewer['login'] == auth['approved_by'])
    bodies = review['response_bodies']; fields(bodies, 'authorization run commit jobs environment history')
    for receipt in bodies.values():
        fields(receipt, 'sha256 bytes'); digest(receipt['sha256']); integer(receipt['bytes'], 1, LIMIT)
    need(bodies['authorization'] == dict(sha256=hashlib.sha256(authorization_raw).hexdigest(), bytes=len(authorization_raw)))
    return review


def phase_id(review):
    name = str(review['run']['id'])+':'+str(review['job']['id'])
    return str(uuid.uuid5(uuid.UUID(review['authorization_id']), 'phase:'+name))


def capture_attempt_id(review):
    return str(uuid.uuid5(uuid.UUID(phase_id(review)), 'capture:1'))
