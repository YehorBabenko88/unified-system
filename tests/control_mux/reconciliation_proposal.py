"""Offline additive GET proposal vectors only; no authority or endpoint wiring."""
import copy,hashlib,json,sys
from pathlib import Path
import jsonschema
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from unified_system.control_mux.codec import encode,decode,validate,PROFILE_SHA,matrix
CONTRACT=ROOT/'docs/control-mux/contracts'
schema=json.loads((CONTRACT/'reconciliation-v3-review1.schema.json').read_bytes())

def check(value):
    jsonschema.Draft202012Validator(schema).validate(value)
    if len(encode(value))>16384:raise ValueError('WRAPPER_CAP')
    pre=value['original_preimage'];receipt=value['receipt'];request=value['request_id']
    if value['query_request_id']==request:raise ValueError('QUERY_ORIGINAL_ALIAS')
    if request!=pre['request_id'] or request!=receipt['request_id']:raise ValueError('REQUEST_LINK')
    if value['profile_schema_sha256']!=pre['profile_schema_sha256']:raise ValueError('PROFILE_LINK')
    if hashlib.sha256(encode(pre)).hexdigest()!=receipt['command_digest']:raise ValueError('COMMAND_HASH')
    key=dict(namespace_schema='unified.control.command-key.v3',cluster_id=value['cluster_id'],quota_owner_id=pre['quota_owner_id'],original_actor_principal_id=pre['original_actor_principal_id'],idempotency_key=pre['idempotency_key'])
    if hashlib.sha256(encode(key)).hexdigest()!=receipt['command_key_sha256']:raise ValueError('KEY_HASH')
    body=value['original_body_ascii'].encode('ascii');raw=value['original_result_ascii'].encode('ascii')
    if hashlib.sha256(body).hexdigest()!=pre['canonical_body_sha256'] or hashlib.sha256(raw).hexdigest()!=receipt['canonical_response_sha256']:raise ValueError('BODY_RESULT_HASH')
    op=matrix['operations'][pre['operation']]
    if pre['http_method']!=op['method'] or pre['canonical_path']!=op['path'].format(**pre):raise ValueError('ROUTE')
    if any(pre[k] is not None for k in op['required_null']) or any(pre[k] is None for k in op['required_nonnull']):raise ValueError('TARGET_EPOCH')
    if op['request_definition']=='EMPTY':
        if body:raise ValueError('DELETE_BODY')
        request_body=None
    else:
        request_body=validate(op['request_definition'],decode(body))
        if request_body['request_id']!=request:raise ValueError('ORIGINAL_BODY_UUID')
    status=receipt['http_status']
    if status=='204':
        if op['completed'].get(status)!='EMPTY' or raw or receipt['result_schema_sha256'] is not None:raise ValueError('EMPTY_204')
        return
    if not raw or receipt['result_schema_sha256']!=PROFILE_SHA:raise ValueError('RESULT_PROFILE')
    result=decode(raw)
    if status in op['completed']:
        validate(op['completed'][status],result)
        if result['request_id']!=request or result['command_digest']!=receipt['command_digest']:raise ValueError('RESULT_LINK')
        if pre['operation']=='OPEN_CONNECTION':
            if result['admitted_role']!=request_body['role'] or result['quota_owner_ref']!=pre['quota_owner_id'] or result['profile_schema_sha256']!=PROFILE_SHA:raise ValueError('OPENED_BINDING')
        else:
            if result['connection_id']!=pre['connection_id'] or result['connection_epoch']!=pre['expected_connection_epoch']:raise ValueError('CONNECTION_BINDING')
            if op['completed'][status]=='draining' and (result['subscription_id'],result['subscription_epoch'])!=(pre['subscription_id'],pre['expected_subscription_epoch']):raise ValueError('SUBSCRIPTION_BINDING')
    else:
        validate('error_v3',result)
        if result['request_id']!=request or result['code'] not in matrix['definitive_rejected']['status_to_codes'].get(status,[]):raise ValueError('REJECTED_MATRIX')

if __name__=='__main__':
    vectors=json.loads((CONTRACT/'reconciliation-v3-review1.vectors.json').read_bytes());observed=[]
    for case in vectors['cases']:
        accepted=True
        try:check(case['value'])
        except (ValueError,KeyError,jsonschema.ValidationError):accepted=False
        assert accepted==case['accepted'],case['name']
        observed.append(dict(name=case['name'],accepted=accepted))
    print(json.dumps(dict(cases=len(observed),result='MODEL_MATCH_ONLY_NOT_ENDPOINT_OR_AUTHORITY',schema_sha256=hashlib.sha256((CONTRACT/'reconciliation-v3-review1.schema.json').read_bytes()).hexdigest(),observed=observed)))
