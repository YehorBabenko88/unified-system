"""Deterministic schema/binding fixtures; NOT a native authorization verifier."""
import copy
import hashlib
import json
from pathlib import Path
import jsonschema

HERE = Path(__file__).resolve().parent
records = json.loads((HERE / 'records.json').read_bytes())
names = dict(assignment='assignment', reservation='worker-resource-reservation', capacity='capacity-observation', ledger='node-resource-ledger')
validators = {k: jsonschema.Draft202012Validator(json.loads((HERE / (v + '.schema.json')).read_bytes())) for k, v in names.items()}


def validate_fixture_bindings(rows):
    for k, value in rows.items(): validators[k].validate(value)
    a, r, c, l = (rows[x] for x in ('assignment', 'reservation', 'capacity', 'ledger'))
    if a['execution_process_proof_ref'] is None: raise ValueError('ready fixture requires native proof reference; reference is still untrusted')
    def equal(*values):
        if any(value != values[0] for value in values): raise ValueError('binding mismatch')
    for k in ('scope', 'assignment_id', 'assignment_revision', 'node_id', 'worker_incarnation_id', 'lease', 'grant_revision', 'execution_attempt_id', 'execution_process_proof_ref', 'resources', 'resource_units'):
        equal(a[k], r[k])
    for k in ('cluster_id', 'cluster_generation'):
        equal(a['scope'][k], c[k], l[k])
    for k in ('node_id', 'worker_incarnation_id', 'resource_units'): equal(a[k], c[k], l[k])
    equal(a['worker_resource_reservation_id'], r['reservation_id'])
    equal(a['worker_resource_reservation_revision'], r['reservation_revision'])
    equal(a['issued_capacity_record_revision'], r['issued_capacity_record_revision'])
    if int(a['issued_capacity_record_revision']) > int(l['capacity_record_revision']): raise ValueError('ledger regressed')
    equal(a['issued_observation'], r['issued_observation'])
    for k, v in l['observation'].items(): equal(v, c[k])
    if int(a['issued_observation']['observation_revision']) > int(c['observation_revision']): raise ValueError('observation regressed')
    for k in ('policy_revision', 'schedule_revision'):
        if int(a['issued_'+k]) > int(l[k]): raise ValueError('policy revision regressed')
    for dimension in l['total']:
        if int(l['total'][dimension]) > int(c['capacity'][dimension]): raise ValueError('policy capacity exceeds measured capacity')
    if a['state'] not in ('ACTIVE', 'DRAINING') or r['state'] not in ('RESERVED', 'DRAINING') or c['freshness_state'] != 'ADMITTED':
        raise ValueError('inactive fixture')
    if l['admission_state'] != 'ACTIVE' or c['node_health'] != 'HEALTHY': raise ValueError('new assignment closed')
    if int(c['capacity']['cpu_millicores']) != int(c['logical_processor_count']) * 1000: raise ValueError('CPU units mismatch')
    b = c['cpu_benchmark']
    if int(b['score']) != int(b['completed_work_units']) * 1000000000 // int(b['elapsed_ns']): raise ValueError('benchmark ratio mismatch')
    for k in a['resources']:
        if not int(a['resources'][k]) <= int(l['reserved'][k]) <= int(l['total'][k]): raise ValueError('resource exhaustion')
    # This fixture is already reserved. Concurrent creation must CAS the native
    # ledger and add request to previous reserved, not add this fixture twice.


def mutate(path, value):
    result = copy.deepcopy(records); target = result
    for key in path[:-1]: target = target[key]
    target[path[-1]] = value
    return result


validate_fixture_bindings(records)
faults = [
    (('reservation', 'scope', 'job_id'), 'other-job'),
    (('reservation', 'assignment_revision'), '2'),
    (('reservation', 'lease', 'lease_epoch'), '8'),
    (('reservation', 'execution_attempt_id'), '00000000-0000-4000-8000-000000000098'),
    (('reservation', 'lease', 'fencing_token'), '102'),
    (('capacity', 'worker_incarnation_id'), '00000000-0000-4000-8000-000000000099'),
    (('capacity', 'freshness_state'), 'INVALIDATED'),
    (('capacity', 'observation_revision'), '12'),
    (('assignment', 'worker_resource_reservation_revision'), '3'),
    (('assignment', 'issued_capacity_record_revision'), '14'),
    (('ledger', 'admission_state'), 'STANDBY'),
    (('ledger', 'reserved', 'ram_bytes'), '4097'),
    (('ledger', 'total', 'ram_bytes'), '4097'),
    (('capacity', 'logical_processor_count'), '2'),
    (('capacity', 'cpu_benchmark', 'score'), '1000'),
    (('assignment', 'resources', 'cpu_millicores'), 1000),
    (('assignment', 'assignment_revision'), '01'),
    (('assignment', 'assignment_revision'), '9223372036854775808'),
    (('assignment', 'lease', 'lease_epoch'), '0'),
    (('assignment', 'resource_units'), 'CPU_BENCHMARK_SCORE'),
    (('assignment', 'storage', 'storage_budget_revision'), True),
    (('assignment', 'scope', 'job_id'), 'job\n'),
    (('capacity', 'memory_pressure_ppm'), '1000001'),
    (('assignment', 'state'), 'SUPERSEDED'),
]
for path, value in faults:
    try: validate_fixture_bindings(mutate(path, value))
    except (ValueError, jsonschema.ValidationError): pass
    else: raise AssertionError(('negative accepted', path))
extra = copy.deepcopy(records); extra['assignment']['native_modify_index'] = '999'
try: validate_fixture_bindings(extra)
except jsonschema.ValidationError: pass
else: raise AssertionError('embedded native self-index accepted')
# Ordinary B allocation/release and new telemetry must not rewrite/revoke A.
refresh = copy.deepcopy(records)
for k in refresh['capacity']['capacity']:
    refresh['capacity']['capacity'][k] = str(int(refresh['capacity']['capacity'][k]) * 2)
refresh['capacity']['logical_processor_count'] = '2'
refresh['capacity']['observation_id'] = '00000000-0000-4000-8000-000000000099'
refresh['capacity']['observation_revision'] = '12'
refresh['ledger']['observation']['observation_id'] = refresh['capacity']['observation_id']
refresh['ledger']['observation']['observation_revision'] = '12'
refresh['ledger']['total'] = copy.deepcopy(refresh['capacity']['capacity'])
refresh['ledger']['reserved'] = copy.deepcopy(refresh['capacity']['capacity'])
refresh['ledger']['capacity_record_revision'] = '14'
validate_fixture_bindings(refresh)  # B admitted, A still owns its original hold.
refresh['ledger']['reserved'] = copy.deepcopy(records['assignment']['resources'])
refresh['ledger']['capacity_record_revision'] = '15'
validate_fixture_bindings(refresh)  # B released, A remains valid.
assert refresh['assignment'] == records['assignment'] and refresh['reservation'] == records['reservation']
capped = copy.deepcopy(refresh)
capped['ledger']['total'] = copy.deepcopy(records['ledger']['total'])
validate_fixture_bindings(capped)  # Policy admits A while observation measures 2*A.
vector = json.loads((HERE / 'scope-key-vector.json').read_bytes())
for dimension in ('job_id','cluster_generation'):
    changed = copy.deepcopy(vector['full_scope']); changed[dimension] = 'other'
    partition = {k:changed[k] for k in ('cluster_id','dataset_id','source_id','partition_id')}
    preimage = dict(schema='unified.scheduler.partition-key.v1-c3.review1',partition=partition)
    raw = json.dumps(preimage,sort_keys=True,separators=(',',':')).encode('ascii')
    assert hashlib.sha256(raw).hexdigest() == vector['partition_sha256']
registry = json.loads((HERE / 'schema-registry.json').read_bytes())
for name, binding in registry.items():
    raw = (HERE / name).read_bytes(); assert len(raw) == binding['bytes'] and hashlib.sha256(raw).hexdigest() == binding['sha256']
result = dict(status='PASS_FIXTURES_ONLY_NOT_NATIVE_AUTHORITY', positive_records=4, unrelated_reservation_refresh_cases=2, stable_partition_key_cases=2, capped_capacity_cases=1, negative_cases=len(faults)+1, schema_hashes_checked=len(registry))
(HERE / 'validation-report.json').write_bytes((json.dumps(result, sort_keys=True, separators=(',', ':'))).encode('ascii'))
print(json.dumps(result))
