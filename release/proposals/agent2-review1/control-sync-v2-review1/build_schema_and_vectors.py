"""Build an OUTPUT-ONLY proposed major-version schema; no production factory."""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).parent
def obj(properties):
    return {'type': 'object', 'additionalProperties': False,
            'properties': properties, 'required': list(properties)}
def ref(name):
    return {'$ref': '#/$defs/' + name}
def nullable(value):
    return {'anyOf': [value, {'type': 'null'}]}
maximum = '9223372036854775807'
parts = [r'[1-9][0-9]{0,17}']
for i, digit in enumerate(maximum):
    low, high = (1 if i == 0 else 0), int(digit) - 1
    if high >= low:
        prefix = maximum[:i]
        smaller = str(low) if low == high else '[' + str(low) + '-' + str(high) + ']'
        tail = '[0-9]{' + str(len(maximum) - i - 1) + '}' if i < len(maximum) - 1 else ''
        parts.append(prefix + smaller + tail)
parts.append(maximum)
positive = '(?:' + '|'.join(parts) + ')'
defs = {
    'u63': {'type': 'string', 'pattern': '^(?:0|' + positive + ')$'},
    'positive': {'type': 'string', 'pattern': '^' + positive + '$'},
    'uuid': {'type': 'string', 'pattern': '^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'},
    'id': {'type': 'string', 'pattern': '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$'},
    'sha256': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'},
    'cursor': {'type': 'string', 'pattern': '^[A-Za-z0-9_-]{1,2048}$'},
}
scope = obj({'kind': {'enum': ['CONTROL', 'DATASET']}, 'dataset_id': nullable(ref('uuid')),
             'source_id': nullable(ref('id')), 'partition_id': nullable(ref('id'))})
scope['allOf'] = [{'if': {'properties': {'kind': {'const': 'CONTROL'}}},
    'then': {'properties': {key: {'type': 'null'} for key in ('dataset_id', 'source_id', 'partition_id')}},
    'else': {'properties': {'dataset_id': ref('uuid')}}}]
defs['scope'] = scope
defs['context'] = obj({key: ref('uuid') for key in ('cluster_id', 'cluster_generation', 'stream_id')} |
    {'view_id': ref('id'), 'scope': ref('scope')})
defs['resource'] = obj({'resource_type': ref('id'), 'resource_id': ref('id'),
    'domain_schema_sha256': ref('sha256'), 'domain_revision': ref('u63'),
    'value': {'type': 'object', 'maxProperties': 64}})
observation = obj({'schema': {'const': 'unified.control.authority-observation.v2'},
    'context': ref('context'), 'observation_id': ref('uuid'),
    'status': {'enum': ['QUORUM_CONFIRMED', 'NO_QUORUM', 'UNKNOWN']},
    'metadata_revision': ref('u63'), 'change_sequence': ref('u63'), 'state_root': ref('sha256'),
    'authority_read_ref': nullable(ref('id')), 'no_quorum_evidence_ref': nullable(ref('id')),
    'read_started_at_ms': nullable(ref('u63')), 'read_finished_at_ms': nullable(ref('u63')),
    'valid_until_ms': nullable(ref('u63')), 'clock_uncertainty_ms': nullable(ref('u63'))})
observation['allOf'] = [
    {'if': {'properties': {'status': {'const': 'QUORUM_CONFIRMED'}}},
     'then': {'properties': {'authority_read_ref': ref('id'), 'no_quorum_evidence_ref': {'type': 'null'},
        **{key: ref('u63') for key in ('read_started_at_ms', 'read_finished_at_ms', 'valid_until_ms', 'clock_uncertainty_ms')}}},
     'else': {'properties': {'valid_until_ms': {'type': 'null'}}}},
    {'if': {'properties': {'status': {'const': 'NO_QUORUM'}}},
     'then': {'properties': {'no_quorum_evidence_ref': ref('id')}}}
]
defs['authority_observation'] = observation
defs['snapshot'] = obj({'schema': {'const': 'unified.control.snapshot.v2'},
    'context': ref('context'), 'metadata_revision': ref('u63'), 'change_sequence': ref('u63'),
    'cursor': ref('cursor'), 'state_root': ref('sha256'),
    'resources': {'type': 'array', 'maxItems': 1000, 'items': ref('resource')},
    'retention': obj({'minimum_seconds': {'const': '600'}, 'earliest_available_sequence': ref('u63')}),
    'authority_observation': {'allOf': [ref('authority_observation'), {'properties': {'status': {'const': 'QUORUM_CONFIRMED'}}}]}})
defs['change'] = obj({'schema': {'const': 'unified.control.change.v2'},
    'context': ref('context'), 'event_id': ref('uuid'), 'change_sequence': ref('positive'),
    'previous_sequence': ref('u63'), 'metadata_revision': ref('u63'), 'cursor': ref('cursor'),
    'previous_state_root': ref('sha256'), 'state_root': ref('sha256'),
    'upserts': {'type': 'array', 'maxItems': 100, 'items': ref('resource')},
    'deletes': {'type': 'array', 'maxItems': 100, 'items': ref('id')}})
defs['liveness'] = obj({'schema': {'const': 'unified.control.liveness.v2'},
    'context': ref('context'), 'connection_id': ref('uuid')})
defs['error'] = obj({'schema': {'const': 'unified.control.error.v2'},
    'request_id': nullable(ref('id')), 'code': {'enum': [
        'INVALID_REQUEST', 'UNAUTHENTICATED', 'SESSION_EXPIRED', 'FORBIDDEN', 'REAUTH_REQUIRED',
        'CONFIRMATION_REQUIRED', 'REVISION_CONFLICT', 'IDEMPOTENCY_CONFLICT', 'OUTCOME_UNKNOWN',
        'NOT_LEADER', 'NO_QUORUM', 'RESYNC_REQUIRED', 'RATE_LIMITED', 'AUTHENTICATION_UNAVAILABLE',
        'AUTHORITY_UNAVAILABLE', 'SAFETY_GATE_CLOSED', 'UNAVAILABLE']},
    'reason': {'enum': ['NONE', 'PROVIDER_NOT_ADMITTED', 'STRICT_TIME_GATE', 'CLOSURE_GATE',
        'DISPATCH_GATE', 'CURSOR_EXPIRED', 'SEQUENCE_GAP', 'GENERATION_CHANGED', 'VIEW_CHANGED',
        'CURSOR_INVALID', 'BUFFER_OVERFLOW', 'UNSUPPORTED_SCHEMA', 'SNAPSHOT_TOO_LARGE',
        'PROJECTION_BEHIND', 'RETENTION_UNQUALIFIED']},
    'retryable': {'type': 'boolean'}, 'retry_after_ms': nullable(ref('u63')),
    'evidence_refs': {'type': 'array', 'maxItems': 64, 'items': ref('id')}})
schema = {'$schema': 'https://json-schema.org/draft/2020-12/schema',
    '$id': 'urn:unified:control-sync:v2-review1',
    '$comment': 'OUTPUT-ONLY PROPOSAL; semantic/auth/barrier/domain validation mandatory; no endpoint admission.',
    'oneOf': [ref(name) for name in ('snapshot', 'change', 'liveness', 'authority_observation', 'error')],
    '$defs': defs}

context = {'cluster_id': '11111111-1111-4111-8111-111111111111',
    'cluster_generation': '22222222-2222-4222-8222-222222222222',
    'stream_id': '33333333-3333-4333-8333-333333333333', 'view_id': 'model-view-1',
    'scope': {'kind': 'CONTROL', 'dataset_id': None, 'source_id': None, 'partition_id': None}}
obs = dict(schema='unified.control.authority-observation.v2', context=context,
    observation_id='44444444-4444-4444-8444-444444444444', status='QUORUM_CONFIRMED',
    metadata_revision='25', change_sequence='10', state_root='1'*64,
    authority_read_ref='MODEL_ONLY_READ', no_quorum_evidence_ref=None,
    read_started_at_ms='1700000000000', read_finished_at_ms='1700000000010',
    valid_until_ms='1700000010000', clock_uncertainty_ms='10')
snapshot = dict(schema='unified.control.snapshot.v2', context=context, metadata_revision='25',
    change_sequence='10', cursor='MODEL_ONLY_CURSOR_10', state_root='1'*64, resources=[],
    retention={'minimum_seconds':'600','earliest_available_sequence':'0'}, authority_observation=obs)
change = dict(schema='unified.control.change.v2', context=context,
    event_id='55555555-5555-4555-8555-555555555555', change_sequence='11', previous_sequence='10',
    metadata_revision='30', cursor='MODEL_ONLY_CURSOR_11', previous_state_root='1'*64, state_root='2'*64,
    upserts=[dict(resource_type='fixture_state',resource_id='model-resource',domain_schema_sha256='5'*64,
                  domain_revision='1',value={'status':'MODEL_ONLY'})], deletes=[])
liveness = dict(schema='unified.control.liveness.v2', context=context,
    connection_id='66666666-6666-4666-8666-666666666666')
error = dict(schema='unified.control.error.v2',request_id=None,code='AUTHENTICATION_UNAVAILABLE',
    reason='PROVIDER_NOT_ADMITTED',retryable=False,retry_after_ms=None,evidence_refs=[])
bad_liveness = dict(liveness, cursor='MUST_NOT_ADVANCE')
numeric = dict(change, change_sequence=11)
bad_obs = copy.deepcopy(obs); bad_obs.update(status='NO_QUORUM',no_quorum_evidence_ref='MODEL_ONLY_DIAG')
vectors = {'qualification': 'SCHEMA_MODEL_ONLY_NO_REAL_AUTHORITY_ROOT_OR_ENDPOINT',
    'valid': {'snapshot': snapshot, 'metadata_jump_change': change, 'liveness': liveness,
              'authority_observation': obs, 'error': error},
    'invalid': {'liveness_with_cursor':bad_liveness,'numeric_sequence_alias':numeric,
                'no_quorum_with_live_expiry':bad_obs,
                'old_v1_error':dict(schema_version='1.0',request_id='old',code='UNAVAILABLE',reason='NONE',retry_after_ms=0,evidence_refs=[])}}
for name, data in [('control-sync-v2.schema.json', schema), ('golden-vectors.json', vectors)]:
    (ROOT / name).write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print('Built output-only schema and explicit MODEL vectors.')
