"""Generate PROPOSED records only. No authority client, writes or proof issuer."""
from pathlib import Path
import copy
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = json.loads((ROOT / 'scheduler_components/schemas/command-v1-c3-review1.schema.json').read_bytes())
DEFS = BASE['$defs']
DEFS['positive'] = {'allOf': [{'$ref': '#/$defs/u63'}, {'not': {'const': '0'}}]}
DEFS['sha256'] = {'type': 'string', 'pattern': '^[0-9a-f]{64}(?![\\s\\S])'}
DEFS['scope'] = BASE['properties']['scope']
DEFS['resources'] = copy.deepcopy(BASE['properties']['resources'])
UNITS = BASE['properties']['resource_units']['const']


def ref(name): return {'$ref': '#/$defs/' + name}
def enum(*values): return {'enum': list(values)}
def obj(props): return dict(type='object', properties=props, required=sorted(props), additionalProperties=False)
def nullable(value): return {'oneOf': [value, {'type': 'null'}]}
def canonical(value): return json.dumps(value, sort_keys=True, separators=(',', ':')).encode('ascii')
def save(name, value): (HERE / name).write_bytes(canonical(value))


DEFS['lease'] = obj(dict(lease_id=ref('uuid4'), lease_epoch=ref('positive'), lease_session_id=ref('uuid4'), fencing_token=ref('positive')))
DEFS['storage'] = obj(dict(storage_reservation_id=ref('id'), storage_budget_revision=ref('positive')))
DEFS['observation_ref'] = obj(dict(observation_id=ref('uuid4'), observation_revision=ref('positive'), freshness_session_id=ref('uuid4'), freshness_policy_revision=ref('positive')))
DEFS['benchmark'] = obj(dict(profile={'const': 'SHA256_1M_SINGLE_PROCESS_BYTES_PER_SECOND'},
                           run_id=ref('uuid4'), work_unit={'const': 'SHA256_BYTES'}, elapsed_ns=ref('positive'),
                           completed_work_units=ref('u63'), score_units={'const': 'BYTES_PER_SECOND_FLOOR'}, score=ref('u63')))


def schema(kind, props):
    result = obj(dict(schema={'const': 'unified.scheduler.' + kind + '.v1-c3.review1'}, **props))
    result.update({'$schema': 'https://json-schema.org/draft/2020-12/schema', '$id': 'urn:unified:scheduler:' + kind + ':v1-c3:review1',
                   '$defs': copy.deepcopy(DEFS), 'title': 'PROPOSED_UNTRUSTED_RECORD_NO_NATIVE_API_ACK'})
    save(kind + '.schema.json', result)


shared = dict(scope=ref('scope'), assignment_id=ref('uuid4'), assignment_revision=ref('positive'),
              node_id=ref('id'), worker_incarnation_id=ref('uuid4'), lease=ref('lease'),
              grant_revision=ref('positive'), execution_attempt_id=ref('uuid4'), execution_process_proof_ref=nullable(ref('id')), resources=ref('resources'), resource_units={'const': UNITS})
schema('assignment', dict(**shared, state=enum('PREPARING', 'ACTIVE', 'DRAINING', 'SUPERSEDED', 'CANCELLED', 'COMPLETED'),
                         owner_principal_id=ref('id'), worker_resource_reservation_id=ref('uuid4'),
                         worker_resource_reservation_revision=ref('positive'), issued_capacity_record_revision=ref('positive'),
                         issued_observation=ref('observation_ref'), storage=ref('storage'), issued_policy_revision=ref('positive'),
                         issued_schedule_revision=ref('positive'), source_request_id=ref('uuid4'),
                         instrument_id=nullable(ref('id'))))
schema('worker-resource-reservation', dict(**shared, reservation_id=ref('uuid4'), reservation_revision=ref('positive'),
                                         state=enum('RESERVED', 'DRAINING', 'REVOKED', 'RELEASED'),
                                         issued_capacity_record_revision=ref('positive'), issued_observation=ref('observation_ref')))
schema('capacity-observation', dict(cluster_id=ref('id'), cluster_generation=ref('id'), node_id=ref('id'),
                                   worker_incarnation_id=ref('uuid4'), producer_principal_id=ref('id'),
                                   observation_id=ref('uuid4'), observation_revision=ref('positive'),
                                   resource_units={'const': UNITS}, capacity=ref('resources'),
                                   logical_processor_count=ref('positive'), memory_pressure_ppm={'type': 'string', 'pattern': '^(?:0|[1-9][0-9]{0,5}|1000000)(?![\\s\\S])'},
                                   node_health=enum('HEALTHY', 'DEGRADED', 'UNAVAILABLE'),
                                   freshness_session_id=ref('uuid4'), freshness_policy_revision=ref('positive'),
                                   freshness_state=enum('ADMITTED', 'INVALIDATED'),
                                   producer_clock_id=ref('uuid4'), producer_monotonic_ns=ref('u63'),
                                   cpu_benchmark=ref('benchmark'), locality_snapshot_sha256=nullable(ref('sha256'))))
ledger_resources = copy.deepcopy(DEFS['resources']); ledger_resources.pop('not')
schema('node-resource-ledger', dict(cluster_id=ref('id'), cluster_generation=ref('id'), node_id=ref('id'),
                                   worker_incarnation_id=ref('uuid4'), capacity_record_revision=ref('positive'),
                                   resource_units={'const': UNITS}, observation=ref('observation_ref'),
                                   total=ref('resources'), reserved=ledger_resources,
                                   admission_state=enum('ACTIVE', 'STANDBY', 'DRAINING', 'MAINTENANCE'),
                                   policy_revision=ref('positive'), schedule_revision=ref('positive')))

scope = dict(cluster_id='cluster', cluster_generation='generation', job_id='job', dataset_id='dataset', source_id='source', partition_id='partition')
uid = lambda n: '00000000-0000-4000-8000-' + str(n).zfill(12)
resources = dict(cpu_millicores='1000', ram_bytes='4096', scratch_bytes='4096', disk_bytes_per_second='1024', network_bytes_per_second='1024')
lease = dict(lease_id=uid(1), lease_epoch='7', lease_session_id=uid(2), fencing_token='101')
observation = dict(observation_id=uid(3), observation_revision='11', freshness_session_id=uid(4), freshness_policy_revision='1')
values = dict(scope=scope, assignment_id=uid(5), assignment_revision='3', node_id='node', worker_incarnation_id=uid(6),
              lease=lease, grant_revision='5', execution_attempt_id=uid(11), execution_process_proof_ref='fixture-untrusted-native-proof-reference', resources=resources, resource_units=UNITS)
assignment = dict(schema='unified.scheduler.assignment.v1-c3.review1', **values, state='ACTIVE', owner_principal_id='principal',
                  worker_resource_reservation_id=uid(7), worker_resource_reservation_revision='2', issued_capacity_record_revision='13',
                  issued_observation=observation, storage=dict(storage_reservation_id='storage-reservation', storage_budget_revision='17'),
                  issued_policy_revision='1', issued_schedule_revision='1', source_request_id=uid(8), instrument_id=None)
reservation = dict(schema='unified.scheduler.worker-resource-reservation.v1-c3.review1', **values, reservation_id=uid(7),
                   reservation_revision='2', state='RESERVED', issued_capacity_record_revision='13', issued_observation=observation)
capacity = dict(schema='unified.scheduler.capacity-observation.v1-c3.review1', cluster_id='cluster', cluster_generation='generation',
                node_id='node', worker_incarnation_id=uid(6), producer_principal_id='principal', **observation,
                resource_units=UNITS, capacity=resources, logical_processor_count='1', memory_pressure_ppm='0', node_health='HEALTHY',
                freshness_state='ADMITTED', producer_clock_id=uid(9), producer_monotonic_ns='123',
                cpu_benchmark=dict(profile='SHA256_1M_SINGLE_PROCESS_BYTES_PER_SECOND', run_id=uid(10), work_unit='SHA256_BYTES',
                                   elapsed_ns='1000000000', completed_work_units='1048576', score_units='BYTES_PER_SECOND_FLOOR', score='1048576'),
                locality_snapshot_sha256=None)
ledger = dict(schema='unified.scheduler.node-resource-ledger.v1-c3.review1', cluster_id='cluster', cluster_generation='generation',
              node_id='node', worker_incarnation_id=uid(6), capacity_record_revision='13', resource_units=UNITS,
              observation=observation, total=resources, reserved=resources, admission_state='ACTIVE', policy_revision='1', schedule_revision='1')
save('records.json', dict(assignment=assignment, reservation=reservation, capacity=capacity, ledger=ledger))
partition = {k:scope[k] for k in ('cluster_id','dataset_id','source_id','partition_id')}
preimage = dict(schema='unified.scheduler.partition-key.v1-c3.review1', partition=partition)
save('scope-key-vector.json', dict(full_scope=scope, preimage=preimage, canonical_ascii=canonical(preimage).decode(), partition_sha256=hashlib.sha256(canonical(preimage)).hexdigest()))
save('schema-registry.json', {p.name: dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(), bytes=p.stat().st_size) for p in sorted(HERE.glob('*.schema.json'))})
print('PROPOSED schemas and fixtures generated; no native authority admission')
