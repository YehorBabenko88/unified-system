"""OUTPUT-ONLY closed schema proposal. No shared/runtime files or providers."""
import copy
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).parent
SOURCE=ROOT/'base-sync-v2.schema.json'


def artifact_bytes(v):
    return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')


def obj(fields):
    return dict(type='object',additionalProperties=False,properties=fields,required=list(fields))


def ref(name):return {'$ref':'#/$defs/'+name}
def const(v):return {'const':v}
def nullable(v):return {'anyOf':[v,{'type':'null'}]}


source=json.loads(SOURCE.read_bytes())
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()=='f41fc73c9e928048410a1f347f4266c95dfbe12d6b9f9e36db68cc9a777986fa'
defs=copy.deepcopy(source['$defs'])
defs['c3_value']={'oneOf':[
    {'type':'string','maxLength':16384,'pattern':r'^[ -~]*$'},
    {'type':'boolean'},{'type':'null'},
    {'type':'array','maxItems':32,'items':ref('c3_value')},
    {'type':'object','maxProperties':64,'propertyNames':{'pattern':r'^[ -~]{1,128}$'},
     'additionalProperties':ref('c3_value')}]}
defs['resource']['properties']['value']={'type':'object','maxProperties':64,
    'propertyNames':{'pattern':r'^[ -~]{1,128}$'},'additionalProperties':ref('c3_value')}
ID,UUID,HASH,U63,POS=[ref(n) for n in ('id','uuid','sha256','u63','positive')]
defs['headers']=obj(dict(request_id=nullable(UUID),idempotency_key=nullable(ID),
    expected_connection_epoch=nullable(POS),expected_subscription_epoch=nullable(POS),stream_attempt_id=nullable(UUID)))
defs['open_request']=obj(dict(schema=const('unified.control.connection-open.v3'),request_id=UUID,
    role={'enum':['NODE_CONTROL','OPERATOR_CONTROL']},app_instance_id=UUID,enrollment_revision=POS))
defs['subscribe_request']=obj(dict(schema=const('unified.control.subscription-open.v3'),request_id=UUID,
    kind={'enum':['CONTROL','DATASET']},selector=ref('scope'),expected_connection_epoch=POS))
defs['snapshot_ack_request']=obj(dict(schema=const('unified.control.snapshot-ack.v3'),request_id=UUID,
    snapshot_id=UUID,snapshot_body_sha256=HASH,cursor=ref('cursor'),expected_subscription_epoch=POS))
base_result=dict(request_id=UUID,command_digest=HASH)
defs['opened']=obj(dict(schema=const('unified.control.connection-opened.v3'),status=const('OPENED'),
    **base_result,connection_id=UUID,connection_epoch=POS,admitted_role={'enum':['NODE_CONTROL','OPERATOR_CONTROL']},
    quota_owner_ref=ID,profile_schema_sha256=HASH,csrf_policy_ref=ID,initial_mux_cursor=ref('cursor'),initial_mux_sequence=const('0')))
defs['subscribed']=obj(dict(schema=const('unified.control.subscribed.v3'),status=const('SUBSCRIBED'),**base_result,
    connection_id=UUID,connection_epoch=POS,subscription_id=UUID,subscription_epoch=POS,delivery_session_id=UUID,snapshot_id=UUID))
defs['snapshot_pending']=obj(dict(schema=const('unified.control.snapshot-pending.v3'),status=const('SNAPSHOT_PENDING'),
    subscription_id=UUID,snapshot_id=UUID,retry_after_ms=POS))
defs['draining']=obj(dict(schema=const('unified.control.draining.v3'),status=const('DRAINING'),**base_result,
    connection_id=UUID,connection_epoch=POS,subscription_id=nullable(UUID),subscription_epoch=nullable(POS)))
defs['command_unknown']=obj(dict(schema=const('unified.control.command-unknown.v3'),status=const('UNKNOWN'),
    **base_result,reason={'enum':['AUTHORITY_UNAVAILABLE','RECEIPT_UNVERIFIED','CONFLICTING_EVIDENCE']}))
defs['error_v3']=obj(dict(schema=const('unified.control.error.v3'),request_id=nullable(UUID),
    code={'enum':['INVALID_REQUEST','UNAUTHENTICATED','FORBIDDEN','SESSION_EXPIRED','NOT_FOUND',
        'METHOD_NOT_ALLOWED','CONFLICT','RATE_LIMITED','AUTHENTICATION_UNAVAILABLE','AUTHORITY_UNAVAILABLE',
        'ADMISSION_UNAVAILABLE','PROTOCOL_ERROR','RESNAPSHOT_REQUIRED']},
    reason={'enum':['NONE','UNSUPPORTED_SCHEMA','REQUEST_ID_CONFLICT','IDEMPOTENCY_CONFLICT','EPOCH_MISMATCH',
        'ROLE_DENIED','DELEGATION_REVOKED','SLOT_LIMIT','BYTE_LIMIT','ENCODER_LIMIT','CURSOR_INVALID',
        'CURSOR_EXPIRED','MUX_GAP','CONFLICTING_DUPLICATE','OUTER_INVALID','INNER_INVALID',
        'CONTAINMENT_UNQUALIFIED','RECEIPT_AMBIGUOUS','PROVIDER_UNAVAILABLE']},
    retryable={'type':'boolean'},retry_after_ms=nullable(U63),
    evidence_refs={'type':'array','items':ID,'maxItems':16,'uniqueItems':True}))
defs['snapshot_ready']=obj(dict(schema=const('unified.control.snapshot-ready.v3'),context=ref('context'),
    snapshot_id=UUID,snapshot_body_sha256=HASH,snapshot_body_bytes=POS))
defs['connection_liveness']=obj(dict(schema=const('unified.control.connection-liveness.v3'),connection_id=UUID))
defs['command_preimage']=obj(dict(profile_schema_sha256=HASH,quota_owner_id=ID,original_actor_principal_id=ID,
    original_actor_session_id=ID,request_id=UUID,idempotency_key=ID,http_method={'enum':['POST','DELETE']},
    operation={'enum':['OPEN_CONNECTION','OPEN_SUBSCRIPTION','ACK_SNAPSHOT','CLOSE_SUBSCRIPTION','CLOSE_CONNECTION']},
    canonical_path={'type':'string','pattern':r'^/control/v3/[A-Za-z0-9/-]{1,240}$'},
    connection_id=nullable(UUID),subscription_id=nullable(UUID),snapshot_id=nullable(UUID),
    expected_connection_epoch=nullable(POS),expected_subscription_epoch=nullable(POS),canonical_body_sha256=HASH))
defs['idempotency_key_preimage']=obj(dict(namespace_schema=const('unified.control.command-key.v3'),
    cluster_id=UUID,quota_owner_id=ID,original_actor_principal_id=ID,idempotency_key=ID))
defs['request_index']=obj(dict(schema=const('unified.control.request-index.v3'),cluster_id=UUID,request_id=UUID,
    profile_schema_sha256=HASH,quota_owner_id=ID,original_actor_principal_id=ID,original_actor_session_id=ID,
    command_key_sha256=HASH,command_digest=HASH,receipt_ref=UUID))
defs['stored_command']=obj(dict(schema=const('unified.control.stored-command.v3'),
    command_key_sha256=HASH,command_digest=HASH,request_id=UUID,receipt_ref=UUID,
    original_preimage=ref('command_preimage'),
    original_body_ascii={'type':'string','maxLength':16384,'pattern':r'^[ -~]*$'},
    state={'enum':['PENDING','COMPLETED','DEFINITIVE_REJECTED']},
    result_sha256=nullable(HASH)))
defs['stored_receipt']=obj(dict(schema=const('unified.control.stored-receipt.v3'),receipt_ref=UUID,
    request_id=UUID,command_key_sha256=HASH,command_digest=HASH,http_status={'enum':['201','202','204','400','401','403','404','405','409','429','503']},
    result_schema_sha256=nullable(HASH),canonical_response_sha256=HASH))

framebase=dict(schema=const('unified.control.mux-frame.v3'),connection_id=UUID,connection_epoch=POS,
    mux_sequence=POS,subscription_id=UUID,subscription_epoch=POS,payload_schema_sha256=HASH)
kinds={'SNAPSHOT_READY':'snapshot_ready','CHANGE':'change','AUTHORITY_OBSERVATION':'authority_observation',
       'LIVENESS':'connection_liveness','SUBSCRIPTION_ERROR':'error_v3','CONNECTION_ERROR':'error_v3'}
variants=[]
for kind,payload in kinds.items():
    fields=dict(framebase,payload_kind=const(kind),payload=ref(payload))
    if kind in ('LIVENESS','CONNECTION_ERROR'):
        fields.update(subscription_id={'type':'null'},subscription_epoch={'type':'null'})
    variants.append(obj(fields))
defs['mux_frame']={'oneOf':variants}
matrix=dict(schema='unified.control.operation-result-matrix.review2',
    operations={
        'OPEN_CONNECTION':dict(method='POST',request_definition='open_request',path='/control/v3/connections',
            required_nonnull=[],required_null=['connection_id','subscription_id','snapshot_id','expected_connection_epoch','expected_subscription_epoch'],
            completed={'201':'opened'}),
        'OPEN_SUBSCRIPTION':dict(method='POST',request_definition='subscribe_request',path='/control/v3/connections/{connection_id}/subscriptions',
            required_nonnull=['connection_id','expected_connection_epoch'],required_null=['subscription_id','snapshot_id','expected_subscription_epoch'],
            completed={'201':'subscribed'}),
        'ACK_SNAPSHOT':dict(method='POST',request_definition='snapshot_ack_request',path='/control/v3/subscriptions/{subscription_id}/snapshot-acks',
            required_nonnull=['connection_id','subscription_id','snapshot_id','expected_connection_epoch','expected_subscription_epoch'],
            required_null=[],completed={'204':'EMPTY'}),
        'CLOSE_SUBSCRIPTION':dict(method='DELETE',request_definition='EMPTY',path='/control/v3/subscriptions/{subscription_id}',
            required_nonnull=['connection_id','subscription_id','expected_connection_epoch','expected_subscription_epoch'],
            required_null=['snapshot_id'],completed={'202':'draining','204':'EMPTY'}),
        'CLOSE_CONNECTION':dict(method='DELETE',request_definition='EMPTY',path='/control/v3/connections/{connection_id}',
            required_nonnull=['connection_id','expected_connection_epoch'],required_null=['subscription_id','snapshot_id','expected_subscription_epoch'],
            completed={'202':'draining','204':'EMPTY'})},
    definitive_rejected=dict(result_definition='error_v3',status_to_codes={
        '400':['INVALID_REQUEST'],'401':['UNAUTHENTICATED','SESSION_EXPIRED'],'403':['FORBIDDEN'],
        '404':['NOT_FOUND'],'405':['METHOD_NOT_ALLOWED'],'409':['CONFLICT'],'429':['RATE_LIMITED'],
        '503':['AUTHENTICATION_UNAVAILABLE','AUTHORITY_UNAVAILABLE','ADMISSION_UNAVAILABLE']}),
    pending='No terminal receipt or historical match; unresolved UNKNOWN only',
    unknown_result='command_unknown is NEVER a terminal definitive receipt under any operation/status',
    zero_body='EMPTY means zero raw bytes, null result schema hash and SHA256(empty), never JSON null')
matrix_bytes=artifact_bytes(matrix)
(ROOT/'operation-result-matrix.json').write_bytes(matrix_bytes)
matrix_sha=hashlib.sha256(matrix_bytes).hexdigest()
codec_bounds=dict(schema='unified.control.c3-codec-bounds.review4',
    depth_rule='Count object/array containers only; root container1; primitive leaves add0',
    node_rule='Count every JSON value including containers/primitives, plus every object key as one string node',
    max_container_depth='12',max_nodes='32768',max_object_members='64',
    min_key_ascii_bytes='1',max_key_ascii_bytes='128',max_value_ascii_characters='16384',
    max_array_entries='1000',max_raw_ascii_bytes='2097152',
    numeric_literals='FORBIDDEN_IN_MESSAGES_NO_COERCION',
    direct_input_shapes='Plain JSON data only; dense own-index arrays; own enumerable string-keyed data properties; no holes/proxies/accessors/symbol or hidden fields; frozen plain data allowed',
    specific_message_domain_limits='Conjunctive smaller schema/route limits remain mandatory')
codec_bytes=artifact_bytes(codec_bounds)
(ROOT/'codec-bounds.json').write_bytes(codec_bytes)
codec_sha=hashlib.sha256(codec_bytes).hexdigest()
names=['open_request','subscribe_request','snapshot_ack_request','opened','subscribed','snapshot_pending',
       'draining','command_unknown','error_v3','snapshot','mux_frame','command_preimage',
       'idempotency_key_preimage','request_index','stored_command','stored_receipt']
schema={'$schema':'https://json-schema.org/draft/2020-12/schema',
    '$id':'urn:unified:control-mux:closed-review4',
    '$comment':'NEW OUTPUT-ONLY proposal; structures never authenticate providers or qualify runtime.',
    'x-operation-result-matrix-sha256':matrix_sha,
    'x-c3-codec-bounds-sha256':codec_sha,
    '$defs':defs,'oneOf':[ref(n) for n in names]}
schema_bytes=artifact_bytes(schema)
(ROOT/'control-mux-closed.schema.json').write_bytes(schema_bytes)
schema_sha=hashlib.sha256(schema_bytes).hexdigest()
registry=dict(schema='unified.control-mux.schema-registry.review4',profile_schema_sha256=schema_sha,
    operation_result_matrix_sha256=matrix_sha,
    c3_codec_bounds_sha256=codec_sha,
    schema_file='control-mux-closed.schema.json',payload_schemas={k:dict(schema_sha256=schema_sha,definition=v) for k,v in kinds.items()},
    domain_schema_registry='PENDING_A3_A4_A5_A7_EXACT_ACK_NO_DOMAIN_DATA_ADMISSION')
(ROOT/'registry.json').write_bytes(artifact_bytes(registry))
uid='11111111-1111-4111-8111-111111111111';cid='22222222-2222-4222-8222-222222222222'
owner='owner1';actor='operator1';session='session1';key='command1'
body=dict(schema='unified.control.connection-open.v3',request_id=uid,role='OPERATOR_CONTROL',app_instance_id=cid,enrollment_revision='1')
body_sha=hashlib.sha256(artifact_bytes(body)).hexdigest()
preimage=dict(profile_schema_sha256=schema_sha,quota_owner_id=owner,original_actor_principal_id=actor,
    original_actor_session_id=session,request_id=uid,idempotency_key=key,http_method='POST',operation='OPEN_CONNECTION',
    canonical_path='/control/v3/connections',connection_id=None,subscription_id=None,snapshot_id=None,
    expected_connection_epoch=None,expected_subscription_epoch=None,canonical_body_sha256=body_sha)
keypre=dict(namespace_schema='unified.control.command-key.v3',cluster_id=cid,quota_owner_id=owner,
    original_actor_principal_id=actor,idempotency_key=key)
digest=hashlib.sha256(artifact_bytes(preimage)).hexdigest();keyhash=hashlib.sha256(artifact_bytes(keypre)).hexdigest()
opened=dict(schema='unified.control.connection-opened.v3',status='OPENED',request_id=uid,command_digest=digest,
    connection_id=cid,connection_epoch='1',admitted_role='OPERATOR_CONTROL',quota_owner_ref=owner,
    profile_schema_sha256=schema_sha,csrf_policy_ref='MODEL_POLICY',initial_mux_cursor='MODEL_CURSOR_0',initial_mux_sequence='0')
index=dict(schema='unified.control.request-index.v3',cluster_id=cid,request_id=uid,profile_schema_sha256=schema_sha,
    quota_owner_id=owner,original_actor_principal_id=actor,original_actor_session_id=session,
    command_key_sha256=keyhash,command_digest=digest,receipt_ref=uid)
liveness=dict(schema='unified.control.mux-frame.v3',connection_id=cid,connection_epoch='1',mux_sequence='1',
    subscription_id=None,subscription_epoch=None,payload_schema_sha256=schema_sha,payload_kind='LIVENESS',
    payload=dict(schema='unified.control.connection-liveness.v3',connection_id=cid))
error=dict(schema='unified.control.error.v3',request_id=uid,code='AUTHORITY_UNAVAILABLE',reason='PROVIDER_UNAVAILABLE',
    retryable=False,retry_after_ms=None,evidence_refs=[])
valid={'open_body':body,'command_preimage':preimage,'key_preimage':keypre,'opened':opened,'request_index':index,'liveness':liveness,'error':error}
invalid={}
for name,value in [('extra_field',dict(body,principal=True)),('numeric_revision',dict(body,enrollment_revision=1)),
                   ('unknown_tag',dict(opened,status='COMMIT_CONFIRMED')),
                   ('liveness_cursor',dict(liveness,cursor='FORBIDDEN'))]:invalid[name]=value
x=copy.deepcopy(liveness);x['payload']['authority']='CURRENT';invalid['liveness_authority']=x
x=copy.deepcopy(liveness);x['payload']['connection_id']={'actor':'forged'};invalid['liveness_nested_identity']=x
(ROOT/'vectors.json').write_bytes(artifact_bytes(dict(qualification='SYNTHETIC_STRUCTURE_HASH_MODELS_ONLY',valid=valid,invalid=invalid)))
vectors=dict(schema='unified.control-mux.hash-preimages.review4',qualification='SYNTHETIC_NO_RUNTIME_ADMISSION',
    canonical_body_ascii=artifact_bytes(body).decode(),canonical_body_sha256=body_sha,
    command_preimage_ascii=artifact_bytes(preimage).decode(),command_digest=digest,
    command_key_preimage_ascii=artifact_bytes(keypre).decode(),command_key_sha256=keyhash,
    empty_delete_body_sha256=hashlib.sha256(b'').hexdigest(),
    example_namespace_keys=dict(request_index='N/control-v3/requests/'+uid,command='N/control-v3/commands/'+keyhash,
                               receipt='N/control-v3/receipts/'+uid))
(ROOT/'hash-preimages.json').write_bytes(artifact_bytes(vectors))
print(json.dumps(dict(schema_sha256_raw=schema_sha,proposal_only=True)))
