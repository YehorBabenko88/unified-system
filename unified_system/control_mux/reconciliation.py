"""Pinned GET review2 data semantics, not authentication or receipt authority.

Only MuxAuthority's captured consistent native records may supply a returned
HTTP document. Pure encoding/preflight neither observes an index nor grants work.
"""
import hashlib,json
from pathlib import Path
import jsonschema
from .codec import encode,decode,validate,PROFILE_SHA,matrix
from .commands import validate_original
SCHEMA_SHA='a7c9730c6125320c537bd41ddb0d364cfc08eb92ec05d9eb20e73c956868c64e'
_path=Path(__file__).resolve().parents[2]/'docs/control-mux/contracts/reconciliation-v3-review2.schema.json'
_raw=_path.read_bytes()
if hashlib.sha256(_raw).hexdigest()!=SCHEMA_SHA:raise RuntimeError('RECONCILIATION_CONTRACT_PIN')
schema=json.loads(_raw)
jsonschema.Draft202012Validator.check_schema(schema)

def _checked_document(value):
    wrapper_raw=encode(value)
    if len(wrapper_raw)>16384:raise ValueError('WRAPPER_CAP')
    value=decode(wrapper_raw)
    if list(jsonschema.Draft202012Validator(schema).iter_errors(value)):raise ValueError('RECONCILIATION_SCHEMA')
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
    validate_original(pre,body)  # A6-GET-R1-01: every duplicated binding, before204
    status=receipt['http_status']
    if status=='204':
        if op['completed'].get(status)!='EMPTY' or raw or receipt['result_schema_sha256'] is not None:raise ValueError('EMPTY_204')
        return wrapper_raw
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

    return wrapper_raw

def encode_document(value):
    try:return _checked_document(value)
    except (KeyError,TypeError,jsonschema.ValidationError) as exc:raise ValueError('RECONCILIATION_BINDING') from exc


def build_document(cluster_id,query_request_id,preimage,body,receipt,response,receipt_index):
    if type(receipt_index) is not int or not 0<receipt_index<2**63:raise ValueError('OBSERVED_INDEX')
    if type(body) is not bytes or type(response) is not bytes:raise ValueError('ORIGINAL_BYTES')
    return encode_document(dict(schema='unified.control.command-reconciliation.v3',status='DEFINITIVE',
        cluster_id=cluster_id,profile_schema_sha256=PROFILE_SHA,request_id=preimage['request_id'],query_request_id=query_request_id,
        original_preimage=preimage,original_body_ascii=body.decode('ascii'),receipt=receipt,
        original_result_ascii=response.decode('ascii'),receipt_modify_index=str(receipt_index)))


def require_fit(cluster_id,preimage,body,receipt,response):
    """Discard worst-index-size document; this does not observe/store any index."""
    query='00000000-0000-4000-8000-000000000001'
    if query==preimage['request_id']:query='00000000-0000-4000-8000-000000000002'
    build_document(cluster_id,query,preimage,body,receipt,response,2**63-1)
