"""NEW draft C3 scheduler command codec. Parsing grants no authority.

This profile is deliberately not an adapter for historical numeric Assignment v1.
Native authority keys, proof format and limits still require joint API approval.
"""
import json
import re
import uuid

SCHEMA = 'unified.scheduler.command.v1-c3.review1'
MAX_U63 = 9223372036854775807
SCOPE = frozenset(('cluster_id', 'cluster_generation', 'job_id', 'dataset_id', 'source_id', 'partition_id'))
RESOURCES = frozenset(('cpu_millicores', 'ram_bytes', 'scratch_bytes', 'disk_bytes_per_second', 'network_bytes_per_second'))
UNITS = 'LOGICAL_PROCESSOR_1000_MILLICORES_BYTES_BYTES_PER_SECOND'
FIELDS = frozenset(('schema', 'operation', 'request_id', 'idempotency_key', 'scope',
                    'node_id', 'worker_incarnation_id', 'assignment_id',
                    'expected_assignment_revision', 'resources', 'resource_units',
                    'storage_reservation_id', 'storage_budget_revision'))


def _id(value):
    if type(value) is not str or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}', value, flags=re.ASCII):
        raise ValueError('opaque identifier required')


def _uuid(value):
    if type(value) is not str:
        raise ValueError('canonical UUIDv4 required')
    try:
        parsed = uuid.UUID(value)
    except ValueError:
        raise ValueError('canonical UUIDv4 required') from None
    if str(parsed) != value or parsed.version != 4:
        raise ValueError('canonical UUIDv4 required')


def _u63(value):
    if (type(value) is not str or not re.fullmatch(r'0|[1-9][0-9]{0,18}', value, flags=re.ASCII)
            or int(value) > MAX_U63):
        raise ValueError('canonical u63 decimal string required')


def encode_command(value):
    if type(value) is not dict or set(value) != FIELDS:
        raise ValueError('closed command required')
    if value['schema'] != SCHEMA or value['operation'] != 'ASSIGN':
        raise ValueError('unsupported domain or operation')
    for key in ('request_id', 'worker_incarnation_id', 'assignment_id'):
        _uuid(value[key])
    for key in ('idempotency_key', 'node_id', 'storage_reservation_id'):
        _id(value[key])
    scope = value['scope']
    if type(scope) is not dict or set(scope) != SCOPE:
        raise ValueError('closed assignment revision scope required')
    for item in scope.values(): _id(item)
    resources = value['resources']
    if type(resources) is not dict or set(resources) != RESOURCES or value['resource_units'] != UNITS:
        raise ValueError('explicit exact units required')
    for item in resources.values(): _u63(item)
    if not any(int(item) for item in resources.values()):
        raise ValueError('empty resource request')
    _u63(value['expected_assignment_revision']); _u63(value['storage_budget_revision'])
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')


def decode_command(raw):
    # The finite closed schema yields <4096 bytes. This is a parser safety bound,
    # NOT a load-qualified Assignment/product limit. No metadata/batch is admitted.
    if type(raw) is not bytes or len(raw) > 4096:
        raise ValueError('bounded bytes required')
    try:
        value = json.loads(raw)
        canonical = encode_command(value)
    except (ValueError, TypeError, RecursionError, UnicodeError):
        raise ValueError('invalid command') from None
    if raw != canonical:
        raise ValueError('noncanonical C3 command')
    return value
