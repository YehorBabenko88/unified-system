"""Measure synthetic native JSON request bytes/counts, not a Consul producer."""
import base64
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
canonical = lambda value: json.dumps(value, sort_keys=True, separators=(',', ':')).encode('ascii')
rows = json.loads((HERE / 'records.json').read_bytes())
scope = json.loads((HERE / 'scope-key-vector.json').read_bytes())['partition_sha256']
prefix = 'PROPOSED-A2-NAMESPACE/authority-v1/clusters/cluster/'
scopekey = prefix + 'partitions/' + scope + '/'


def check(label, key, session=False):
    value = dict(Verb='check-session' if session else 'check-index', Key=key)
    if session: value['Session'] = '00000000-0000-4000-8000-000000000002'
    else: value['Index'] = 101
    return dict(label=label, operation={'KV': value})


def cas(label, key, record):
    return dict(label=label, operation={'KV': dict(Verb='cas', Key=key, Index=101,
                Value=base64.b64encode(canonical(record)).decode('ascii'))})


common = [check('leader_session', 'A2/leader', True), check('leader_index', 'A2/leader'),
          check('generation', 'A2/generation'), check('principal', 'A2/principal'),
          check('stable_partition_identity_registry', 'A3-A4/stable-partition-identity'),
          check('worker_registration', prefix+'nodes/node/registration'),
          check('worker_policy_schedule_drain', prefix+'nodes/node/policy')]
publication = common + [
    check('current_assignment', scopekey+'assignment'),
    check('execution_process_proof', prefix+'execution-attempts/'+rows['assignment']['execution_attempt_id']),
    check('execution_process_session', prefix+'execution-attempts/'+rows['assignment']['execution_attempt_id'], True),
    check('lease_session', 'A2/lease-binding', True), check('lease_binding', 'A2/lease-binding'),
    check('worker_resource_reservation', prefix+'reservations/'+rows['reservation']['reservation_id']),
    check('capacity_observation_head', prefix+'nodes/node/observation-current'),
    check('capacity_observation', prefix+'observations/'+rows['capacity']['observation_id']),
    check('capacity_freshness_session', prefix+'nodes/node/freshness', True),
    check('node_resource_ledger', prefix+'nodes/node/resource-ledger'),
    check('storage_reservation', 'A4/storage-reservation'),
]
# CAS checks are not redundantly added as check-index: they already compare.
publication_writes = [cas(label, 'A2-A4/'+label, dict(schema='FIXTURE_ONLY_NOT_ADMITTED', binding_sha256=hashlib.sha256(canonical(rows['assignment'])).hexdigest()))
                      for label in ('dataset_head', 'checkpoint_head', 'outbox_ref', 'allocation_debit', 'storage_budget', 'receipt', 'request_registry', 'idempotency_registry')]
supersession = common + [
    check('old_lease_binding_allow_already_invalid_session', 'A2/lease-binding'),
    check('new_worker_registration', prefix+'nodes/new-node/registration'),
    check('new_worker_policy', prefix+'nodes/new-node/policy'),
    check('new_capacity_observation_head', prefix+'nodes/new-node/observation-current'),
    check('new_capacity_observation', prefix+'observations/new-observation'),
    check('new_capacity_freshness_session', prefix+'nodes/new-node/freshness', True),
    check('new_storage_reservation', 'A4/new-storage-reservation'),
    check('new_storage_budget', 'A4/new-storage-budget')]
supersession_writes = [
    cas('persistent_scope_counter', scopekey+'revision-counter', dict(last_assignment_revision='4')),
    cas('current_assignment', scopekey+'assignment', dict(rows['assignment'], assignment_revision='4')),
    cas('old_worker_resource_reservation', prefix+'reservations/'+rows['reservation']['reservation_id'], dict(rows['reservation'], state='REVOKED', reservation_revision='3')),
    cas('old_node_resource_ledger', prefix+'nodes/node/resource-ledger', rows['ledger']),
    cas('new_node_resource_ledger', prefix+'nodes/new-node/resource-ledger', rows['ledger']),
    cas('new_worker_resource_reservation', prefix+'reservations/new-reservation', rows['reservation']),
    cas('new_lease_binding', 'A2/new-lease-binding', dict(schema='A2_PROPOSED_NOT_FROZEN')),
    cas('old_execution_attempt_revoke', prefix+'execution-attempts/'+rows['assignment']['execution_attempt_id'], dict(schema='A2_PROPOSED_NOT_FROZEN',state='REVOKED')),
    cas('new_execution_attempt_prepare', prefix+'execution-attempts/new-attempt', dict(schema='A2_PROPOSED_NOT_FROZEN',state='PREPARING')),
    *[cas(label, 'A2/'+label, dict(schema='FIXTURE_ONLY_NOT_ADMITTED')) for label in ('receipt', 'request_registry', 'idempotency_registry')]]

result = []
for operation, checks, writes in [('PUBLICATION', publication, publication_writes), ('SUPERSESSION_CROSS_NODE', supersession, supersession_writes)]:
    for n in (0, 1, 8, 32, 64):
        dependencies = [check('closure_dependency_'+str(i), 'A4/closure/'+str(i)) for i in range(n)]
        # Full closure is variable, never silently capped/truncated or replaced by
        # an unreviewed root. Oversized atomic requests are unavailable.
        measured = checks + dependencies + writes
        body = canonical([item['operation'] for item in measured])
        result.append(dict(operation=operation, variable_dependency_records=n, checks=len(checks)+n,
                           writes=len(writes), total_ops=len(measured), encoded_request_bytes=len(body),
                           documented_64op_ceiling_exceeded=len(measured)>64, request_sha256=hashlib.sha256(body).hexdigest()))
report = dict(status='MEASURED_SYNTHETIC_ENCODING_NOT_NATIVE_EXECUTION_OR_LOAD_LIMIT',
              source='https://developer.hashicorp.com/consul/api-docs/txn', documented_operation_ceiling=64,
              actual_server_version_config='PENDING_A2', native_payload_limit='NOT_INFERRED',
              record_bytes={k:len(canonical(v)) for k,v in rows.items()}, rows=result,
              publication_labels=[x['label'] for x in publication+publication_writes],
              supersession_labels=[x['label'] for x in supersession+supersession_writes],
              unresolved=['A2 actual native key layout/session locking/global request preparation',
                          'A4 complete closure/debit values and actual encoded maxima',
                          'same-node ledger coalescing and actual reservation delta',
                          'native race/overlimit/no-quorum tests and workload qualification'])
(HERE/'atomic-operation-ledger.json').write_bytes(canonical(report))
print(json.dumps(dict(record_bytes=report['record_bytes'],rows=result)))
