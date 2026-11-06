"""Structural/canonical/lookup MODEL checks; never actual admission/proof."""
import copy
import hashlib
import json
from pathlib import Path
import runpy
import jsonschema

ROOT=Path(__file__).parent
schema=json.loads((ROOT/'control-mux-closed.schema.json').read_bytes())
PROFILE_SHA=hashlib.sha256((ROOT/'control-mux-closed.schema.json').read_bytes()).hexdigest()
vectors=json.loads((ROOT/'vectors.json').read_bytes())
jsonschema.Draft202012Validator.check_schema(schema)
validator=jsonschema.Draft202012Validator(schema)
matrix=json.loads((ROOT/'operation-result-matrix.json').read_bytes())
assert hashlib.sha256((ROOT/'operation-result-matrix.json').read_bytes()).hexdigest()==schema['x-operation-result-matrix-sha256']
bounds=json.loads((ROOT/'codec-bounds.json').read_bytes())
assert hashlib.sha256((ROOT/'codec-bounds.json').read_bytes()).hexdigest()==schema['x-c3-codec-bounds-sha256']
materialize=runpy.run_path(str(ROOT/'boundary_cases.py'))['materialize']
results=[]


def artifact_encode(value):
    # Schemas/reports contain numeric metadata and are NOT C3 transport messages.
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()


def encode(value):
    nodes=0;size=0;chunks=[]
    def count():
        nonlocal nodes
        nodes+=1
        if nodes>int(bounds['max_nodes']):raise ValueError('NODE_CAP')
    def emit(text):
        nonlocal size
        raw=text.encode('ascii');size+=len(raw)
        if size>int(bounds['max_raw_ascii_bytes']):raise ValueError('BYTE_CAP')
        chunks.append(raw)
    def write(x,parent_depth=0):
        count()
        if x is None:emit('null');return
        if type(x) is bool:emit('true' if x else 'false');return
        if type(x) is str:
            if len(x)>int(bounds['max_value_ascii_characters']) or any(not 32<=ord(c)<=126 for c in x):raise ValueError('STRING_CAP')
            emit(json.dumps(x,ensure_ascii=True));return
        if type(x) not in (dict,list):raise ValueError('UNSUPPORTED_OR_NUMERIC')
        depth=parent_depth+1
        if depth>int(bounds['max_container_depth']):raise ValueError('DEPTH_CAP')
        if type(x) is list:
            if len(x)>int(bounds['max_array_entries']):raise ValueError('ARRAY_CAP')
            emit('[')
            for i,v in enumerate(x):
                if i:emit(',')
                write(v,depth)
            emit(']');return
        if len(x)>int(bounds['max_object_members']):raise ValueError('MEMBER_CAP')
        for key in x:
            if type(key) is not str or not int(bounds['min_key_ascii_bytes'])<=len(key)<=int(bounds['max_key_ascii_bytes']) or any(not 32<=ord(c)<=126 for c in key):raise ValueError('KEY_CAP')
        emit('{')
        for i,key in enumerate(sorted(x)):
            count()
            if i:emit(',')
            emit(json.dumps(key,ensure_ascii=True));emit(':');write(x[key],depth)
        emit('}')
    write(value)
    return b''.join(chunks)


def sha(value):return hashlib.sha256(encode(value)).hexdigest()


def decode(raw):
    if type(raw) is not bytes or not 0<len(raw)<=int(bounds['max_raw_ascii_bytes']):raise ValueError('BYTE_CAP')
    # Bound depth BEFORE recursive JSON parsing; escaped strings are not delimiters.
    depth=0;quoted=False;escaped=False
    for b in raw:
        if quoted:
            if escaped:escaped=False
            elif b==92:escaped=True
            elif b==34:quoted=False
        elif b==34:quoted=True
        elif b in (91,123):
            depth+=1
            if depth>int(bounds['max_container_depth']):raise ValueError('DEPTH_CAP')
        elif b in (93,125):
            depth-=1
            if depth<0:raise ValueError('INVALID_JSON')
    def unique(pairs):
        out={}
        for k,v in pairs:
            if k in out:raise ValueError('DUPLICATE_KEY')
            out[k]=v
        return out
    def invalid(_):raise ValueError('NONFINITE')
    value=json.loads(raw.decode('ascii'),object_pairs_hook=unique,parse_constant=invalid,
                     parse_int=invalid,parse_float=invalid)
    if encode(value)!=raw:raise ValueError('NONCANONICAL')
    return value


for name,value in vectors['valid'].items():
    validator.validate(value);assert decode(encode(value))==value
    results.append(dict(case=name,result='STRUCTURE_CANONICAL_MATCH'))
for name,value in vectors['invalid'].items():
    assert list(validator.iter_errors(value)),name
    results.append(dict(case=name,result='STRUCTURAL_REJECTION'))

for name,raw in [('duplicate',b'{"x":1,"x":1}'),('whitespace',b' {}'),('old_order',b'{"z":null,"a":null}'),
                 ('nonfinite',b'{"x":NaN}'),('unicode_escape',b'{"x":"\\u0061"}'),
                 ('nonascii',b'{"x":"\\u00e9"}'),('too_deep',b'['*13+b']'*13)]:
    try:decode(raw)
    except (ValueError,UnicodeError):results.append(dict(case=name,result='CANONICAL_REJECTION'))
    else:raise AssertionError(name)
for raw in (b'{"x":1}',b'{"x":1.0}',b'{"x":-0.0}',b'{"x":1e-07}',b'{"x":0}',b'{"2":"b","10":"a"}'):
    try:decode(raw)
    except ValueError:results.append(dict(case='CROSS_LANGUAGE_REJECT_'+raw.decode(),result='CANONICAL_REJECTION'))
    else:raise AssertionError(raw)
assert decode(b'{"10":"a","2":"b","x":"1.0","y":"-0.0","z":"1e-07"}')=={'10':'a','2':'b','x':'1.0','y':'-0.0','z':'1e-07'}
results.append(dict(case='EXACT_NUMERIC_STRINGS_AND_ASCII_KEY_ORDER',result='NO_NUMERIC_COERCION'))
u63=jsonschema.Draft202012Validator({'$defs':schema['$defs'],'$ref':'#/$defs/u63'})
for x in ('0','9223372036854775807'):u63.validate(x)
for x in ('9223372036854775808','01',1,True):assert list(u63.iter_errors(x))
results.append(dict(case='EXACT_U63_BOUNDARIES',result='MATCH'))

pre=vectors['valid']['command_preimage'];keypre=vectors['valid']['key_preimage']
hashes=json.loads((ROOT/'hash-preimages.json').read_bytes())
assert sha(pre)==hashes['command_digest'] and sha(keypre)==hashes['command_key_sha256']
assert hashlib.sha256(hashes['canonical_body_ascii'].encode()).hexdigest()==hashes['canonical_body_sha256']
results.append(dict(case='EXACT_BODY_COMMAND_KEY_PREIMAGES',result='MATCH'))


def operation_result_compatible(original,state,status,result,body_ascii):
    rule=matrix['operations'].get(original['operation'])
    if rule is None or original['http_method']!=rule['method']:return False
    if any(original[k] is None for k in rule['required_nonnull']):return False
    if any(original[k] is not None for k in rule['required_null']):return False
    if original['canonical_path']!=rule['path'].format(**original):return False
    raw=body_ascii.encode('ascii')
    if hashlib.sha256(raw).hexdigest()!=original['canonical_body_sha256']:return False
    if rule['request_definition']=='EMPTY':
        if raw:return False
        body=None
    else:
        try:body=decode(raw)
        except ValueError:return False
        request_validator=jsonschema.Draft202012Validator({'$defs':schema['$defs'],'$ref':'#/$defs/'+rule['request_definition']})
        if list(request_validator.iter_errors(body)) or body['request_id']!=original['request_id']:return False
        if original['operation']=='OPEN_SUBSCRIPTION':
            if body['kind']!=body['selector']['kind'] or body['expected_connection_epoch']!=original['expected_connection_epoch']:return False
        if original['operation']=='ACK_SNAPSHOT':
            if body['snapshot_id']!=original['snapshot_id'] or body['expected_subscription_epoch']!=original['expected_subscription_epoch']:return False
    if original['http_method']=='DELETE' and original['canonical_body_sha256']!=hashlib.sha256(b'').hexdigest():return False
    if state=='DEFINITIVE_REJECTED':
        definition=matrix['definitive_rejected']['result_definition']
        allowed=matrix['definitive_rejected']['status_to_codes'].get(status,[])
        if result is None or result.get('code') not in allowed:return False
    elif state=='COMPLETED':
        definition=rule['completed'].get(status)
        if definition is None:return False
        if definition=='EMPTY':return result is None
    else:return False
    if list(jsonschema.Draft202012Validator({'$defs':schema['$defs'],'$ref':'#/$defs/'+definition}).iter_errors(result)):return False
    if state=='COMPLETED' and original['operation']=='OPEN_CONNECTION':
        if (result['profile_schema_sha256']!=original['profile_schema_sha256']
                or result['quota_owner_ref']!=original['quota_owner_id'] or result['admitted_role']!=body['role']):return False
    if state=='COMPLETED' and original['operation']!='OPEN_CONNECTION':
        if result['connection_id']!=original['connection_id'] or result['connection_epoch']!=original['expected_connection_epoch']:return False
        if original['operation'].startswith('CLOSE_'):
            if result['subscription_id']!=original['subscription_id'] or result['subscription_epoch']!=original['expected_subscription_epoch']:return False
    return True


def model_lookup(index_rows,command,receipt,result,context):
    """Supplied records are synthetic, NOT authenticated native reads."""
    if len(index_rows)!=1:return 'UNAVAILABLE_AMBIGUOUS' if index_rows else 'UNKNOWN'
    index=index_rows[0];validator.validate(index)
    if index['profile_schema_sha256']!=PROFILE_SHA:return 'UNAVAILABLE_CONFLICT'
    if index['quota_owner_id']!=context['owner']:return 'FORBIDDEN_REDACTED'
    if index['request_id']!=context['request_id'] or index['cluster_id']!=context['cluster_id']:return 'UNAVAILABLE_CONFLICT'
    if command is None or receipt is None:return 'UNKNOWN'
    validator.validate(command);validator.validate(receipt)
    if command['state']=='PENDING':return 'UNKNOWN'
    if result is None and receipt['http_status']!='204':return 'UNKNOWN'
    if result is not None:validator.validate(result)
    pairs=('request_id','command_key_sha256','command_digest','receipt_ref')
    if any(index[k]!=command[k] or command[k]!=receipt[k] for k in pairs):return 'UNAVAILABLE_CONFLICT'
    original=command['original_preimage']
    if original['profile_schema_sha256']!=PROFILE_SHA:return 'UNAVAILABLE_CONFLICT'
    if any(index[k]!=original[k] for k in ('profile_schema_sha256','quota_owner_id','original_actor_principal_id','original_actor_session_id','request_id')):return 'UNAVAILABLE_CONFLICT'
    descriptor=dict(namespace_schema='unified.control.command-key.v3',cluster_id=context['cluster_id'],
        quota_owner_id=original['quota_owner_id'],original_actor_principal_id=original['original_actor_principal_id'],
        idempotency_key=original['idempotency_key'])
    if sha(descriptor)!=index['command_key_sha256']:return 'UNAVAILABLE_CONFLICT'
    if sha(original)!=command['command_digest']:return 'UNAVAILABLE_CONFLICT'
    if receipt['http_status']=='204':
        actual_hash=hashlib.sha256(b'').hexdigest()
        if (result is not None or receipt['result_schema_sha256'] is not None
                or command['state']!='COMPLETED'):return 'UNAVAILABLE_CONFLICT'
    else:
        actual_hash=sha(result)
        if receipt['result_schema_sha256']!=original['profile_schema_sha256']:return 'UNAVAILABLE_CONFLICT'
        if result['request_id']!=index['request_id']:return 'UNAVAILABLE_CONFLICT'
        if 'command_digest' in result and result['command_digest']!=index['command_digest']:return 'UNAVAILABLE_CONFLICT'
    if command['result_sha256']!=actual_hash or receipt['canonical_response_sha256']!=actual_hash:return 'UNAVAILABLE_CONFLICT'
    if not operation_result_compatible(original,command['state'],receipt['http_status'],result,command['original_body_ascii']):return 'UNAVAILABLE_CONFLICT'
    if command['state']=='DEFINITIVE_REJECTED':
        if receipt['http_status'] in ('201','202','204') or result.get('schema')!='unified.control.error.v3':return 'UNAVAILABLE_CONFLICT'
        return 'HISTORICAL_MODEL_REJECTION_NOT_PERMISSION'
    if receipt['http_status'] not in ('201','202','204'):return 'UNAVAILABLE_CONFLICT'
    return 'HISTORICAL_MODEL_MATCH_NOT_PERMISSION'


index=vectors['valid']['request_index'];result=vectors['valid']['opened']
command=dict(schema='unified.control.stored-command.v3',command_key_sha256=sha(keypre),command_digest=sha(pre),
    request_id=index['request_id'],receipt_ref=index['receipt_ref'],original_preimage=pre,
    original_body_ascii=hashes['canonical_body_ascii'],state='COMPLETED',result_sha256=sha(result))
receipt=dict(schema='unified.control.stored-receipt.v3',receipt_ref=index['receipt_ref'],request_id=index['request_id'],
    command_key_sha256=sha(keypre),command_digest=sha(pre),http_status='201',
    result_schema_sha256=pre['profile_schema_sha256'],canonical_response_sha256=sha(result))
context=dict(owner=index['quota_owner_id'],request_id=index['request_id'],cluster_id=index['cluster_id'])
assert model_lookup([index],command,receipt,result,context)=='HISTORICAL_MODEL_MATCH_NOT_PERMISSION'
results.append(dict(case='ONE_INDEX_EXACT_ORIGINAL_RECEIPT',result='MODEL_MATCH_ONLY'))
for name,rows,c,r,v,ctx,expected in [
    ('missing_index',[],command,receipt,result,context,'UNKNOWN'),
    ('ambiguous_uuid_index',[index,index],command,receipt,result,context,'UNAVAILABLE_AMBIGUOUS'),
    ('other_owner',[index],command,receipt,result,dict(context,owner='other'),'FORBIDDEN_REDACTED'),
    ('missing_receipt',[index],command,None,result,context,'UNKNOWN'),
    ('pending_command',[index],dict(command,state='PENDING'),receipt,result,context,'UNKNOWN'),
    ('index_actor_changed',[dict(index,original_actor_principal_id='other')],command,receipt,result,context,'UNAVAILABLE_CONFLICT'),
    ('index_session_changed',[dict(index,original_actor_session_id='other')],command,receipt,result,context,'UNAVAILABLE_CONFLICT'),
    ('index_profile_changed',[dict(index,profile_schema_sha256='f'*64)],command,receipt,result,context,'UNAVAILABLE_CONFLICT'),
    ('forged_joined_key',[dict(index,command_key_sha256='f'*64)],dict(command,command_key_sha256='f'*64),dict(receipt,command_key_sha256='f'*64),result,context,'UNAVAILABLE_CONFLICT'),
    ('changed_digest',[index],dict(command,command_digest='f'*64),receipt,result,context,'UNAVAILABLE_CONFLICT'),
    ('changed_result',[index],command,receipt,dict(result,connection_epoch='2'),context,'UNAVAILABLE_CONFLICT'),
    ('changed_uuid',[index],command,receipt,result,dict(context,request_id='99999999-9999-4999-8999-999999999999'),'UNAVAILABLE_CONFLICT')]:
    assert model_lookup(rows,c,r,v,ctx)==expected,name
    results.append(dict(case=name,result=expected))

# Empty DELETE body alone cannot cause cross-target command identity equality.
d=copy.deepcopy(pre);d.update(http_method='DELETE',operation='CLOSE_CONNECTION',
    canonical_path='/control/v3/connections/'+result['connection_id'],connection_id=result['connection_id'],
    expected_connection_epoch='1',canonical_body_sha256=hashlib.sha256(b'').hexdigest())
other=copy.deepcopy(d);other.update(connection_id=index['request_id'],canonical_path='/control/v3/connections/'+index['request_id'])
assert sha(d)!=sha(other) and sha(dict(d,expected_connection_epoch='2'))!=sha(d)
results.append(dict(case='EMPTY_DELETE_TARGET_AND_EPOCH_CHANGE_DIGEST',result='MATCH'))

def body_for(original):
    operation=original['operation']
    if operation=='OPEN_CONNECTION':return hashes['canonical_body_ascii']
    if operation=='OPEN_SUBSCRIPTION':return encode(dict(schema='unified.control.subscription-open.v3',request_id=original['request_id'],
        kind='CONTROL',selector=dict(kind='CONTROL',dataset_id=None,source_id=None,partition_id=None),
        expected_connection_epoch=original['expected_connection_epoch'])).decode()
    if operation=='ACK_SNAPSHOT':return encode(dict(schema='unified.control.snapshot-ack.v3',request_id=original['request_id'],
        snapshot_id=original['snapshot_id'],snapshot_body_sha256='a'*64,cursor='MODEL_SNAPSHOT_CURSOR',
        expected_subscription_epoch=original['expected_subscription_epoch'])).decode()
    return ''


def with_body_hash(original):
    return dict(original,canonical_body_sha256=hashlib.sha256(body_for(original).encode()).hexdigest())


def terminal_fixture(original,result_value,status,state):
    kp=dict(namespace_schema='unified.control.command-key.v3',cluster_id=context['cluster_id'],
        quota_owner_id=original['quota_owner_id'],original_actor_principal_id=original['original_actor_principal_id'],idempotency_key=original['idempotency_key'])
    raw=b'' if result_value is None else encode(result_value)
    digest=sha(original);kh=sha(kp);bodyhash=hashlib.sha256(raw).hexdigest()
    idx=dict(index,command_key_sha256=kh,command_digest=digest)
    cmd=dict(command,command_key_sha256=kh,command_digest=digest,original_preimage=original,original_body_ascii=body_for(original),state=state,result_sha256=bodyhash)
    rec=dict(receipt,command_key_sha256=kh,command_digest=digest,http_status=status,canonical_response_sha256=bodyhash,
        result_schema_sha256=None if status=='204' else original['profile_schema_sha256'])
    return idx,cmd,rec

rejection=dict(vectors['valid']['error'],code='CONFLICT',reason='ROLE_DENIED')
ri,rc,rr=terminal_fixture(pre,rejection,'409','DEFINITIVE_REJECTED')
assert model_lookup([ri],rc,rr,rejection,context)=='HISTORICAL_MODEL_REJECTION_NOT_PERMISSION'
results.append(dict(case='DEFINITIVE_REJECTION_RECONCILES_ORIGINAL_ERROR_RECEIPT',result='MODEL_MATCH_ONLY'))
ei,ec,er=terminal_fixture(d,None,'204','COMPLETED')
assert model_lookup([ei],ec,er,None,context)=='HISTORICAL_MODEL_MATCH_NOT_PERMISSION'
results.append(dict(case='EMPTY_204_RECONCILES_EXACT_NO_BODY_RECEIPT',result='MODEL_MATCH_ONLY'))
for name,bad in [('204_nonnull_schema',dict(er,result_schema_sha256=pre['profile_schema_sha256'])),
                 ('204_nonempty_body_hash',dict(er,canonical_response_sha256='f'*64))]:
    assert model_lookup([ei],ec,bad,None,context)=='UNAVAILABLE_CONFLICT'
    results.append(dict(case=name,result='UNAVAILABLE_CONFLICT'))

# A1-CLOSED-R1-01: hash-consistent semantic operation/result mismatches.
unknown_result=dict(schema='unified.control.command-unknown.v3',status='UNKNOWN',
    request_id=pre['request_id'],command_digest=sha(pre),reason='RECEIPT_UNVERIFIED')
wrongop=dict(pre,operation='OPEN_SUBSCRIPTION',canonical_path='/control/v3/connections/'+result['connection_id']+'/subscriptions',
    connection_id=result['connection_id'],expected_connection_epoch='1')
wrongop=with_body_hash(wrongop)
negative_cases=[('OPEN_COMPLETED_204',pre,None,'204'),
    ('OPEN_COMPLETED_201_UNKNOWN',pre,unknown_result,'201'),
    ('OPEN_COMPLETED_201_ERROR',pre,rejection,'201'),
    ('SUBSCRIBE_COMPLETED_201_OPENED',wrongop,dict(result,command_digest=sha(wrongop)),'201'),
    ('DELETE_COMPLETED_201_OPENED',d,dict(result,command_digest=sha(d)),'201')]
observed=[]
for name,original,value,status in negative_cases:
    ni,nc,nr=terminal_fixture(original,value,status,'COMPLETED')
    actual=model_lookup([ni],nc,nr,value,context)
    observed.append(dict(case=name,actual=actual,expected='UNAVAILABLE_CONFLICT'))
(ROOT/'operation-matrix-probes.json').write_bytes(artifact_encode(dict(qualification='SYNTHETIC_MODEL_ONLY',cases=observed)))
assert all(x['actual']==x['expected'] for x in observed),observed
results.extend(dict(case=x['case'],result=x['actual']) for x in observed)

# Preserve every admitted operation's terminal success/rejection shape.
subscribe=wrongop
subscribed=dict(schema='unified.control.subscribed.v3',status='SUBSCRIBED',request_id=pre['request_id'],
    command_digest=sha(subscribe),connection_id=result['connection_id'],connection_epoch='1',
    subscription_id=index['request_id'],subscription_epoch='1',delivery_session_id=index['request_id'],snapshot_id=index['request_id'])
ack=dict(pre,operation='ACK_SNAPSHOT',canonical_path='/control/v3/subscriptions/'+index['request_id']+'/snapshot-acks',
    connection_id=result['connection_id'],subscription_id=index['request_id'],snapshot_id=index['request_id'],
    expected_connection_epoch='1',expected_subscription_epoch='1')
close_sub=dict(d,operation='CLOSE_SUBSCRIPTION',canonical_path='/control/v3/subscriptions/'+index['request_id'],
    subscription_id=index['request_id'],expected_subscription_epoch='1')
ack=with_body_hash(ack)
for name,original,value,status in [('SUBSCRIBE_201',subscribe,subscribed,'201'),('ACK_204',ack,None,'204'),
                                 ('CLOSE_SUB_204',close_sub,None,'204')]:
    ni,nc,nr=terminal_fixture(original,value,status,'COMPLETED')
    assert model_lookup([ni],nc,nr,value,context)=='HISTORICAL_MODEL_MATCH_NOT_PERMISSION'
    results.append(dict(case=name,result='ADMITTED_MODEL_TUPLE_MATCH'))
for name,original in [('CLOSE_CONNECTION_202',d),('CLOSE_SUBSCRIPTION_202',close_sub)]:
    draining=dict(schema='unified.control.draining.v3',status='DRAINING',request_id=pre['request_id'],command_digest=sha(original),
        connection_id=original['connection_id'],connection_epoch=original['expected_connection_epoch'],
        subscription_id=original['subscription_id'],subscription_epoch=original['expected_subscription_epoch'])
    ni,nc,nr=terminal_fixture(original,draining,'202','COMPLETED')
    assert model_lookup([ni],nc,nr,draining,context)=='HISTORICAL_MODEL_MATCH_NOT_PERMISSION'
    results.append(dict(case=name,result='ADMITTED_MODEL_TUPLE_MATCH_NOT_CONTAINMENT_PROOF'))
for name,original,value,status,state in [
    ('WRONG_METHOD_OPEN',dict(pre,http_method='DELETE'),dict(result,command_digest=sha(dict(pre,http_method='DELETE'))),'201','COMPLETED'),
    ('WRONG_DELETE_PATH',dict(d,canonical_path='/control/v3/subscriptions/'+d['connection_id']),None,'204','COMPLETED'),
    ('NONEMPTY_DELETE_BODY',dict(d,canonical_body_sha256='f'*64),None,'204','COMPLETED'),
    ('UNKNOWN_AS_DEFINITIVE_REJECTED',pre,unknown_result,'503','DEFINITIVE_REJECTED')]:
    ni,nc,nr=terminal_fixture(original,value,status,state)
    assert model_lookup([ni],nc,nr,value,context)=='UNAVAILABLE_CONFLICT',name
    results.append(dict(case=name,result='UNAVAILABLE_CONFLICT'))

for name,value in [('OPENED_WRONG_PROFILE',dict(result,profile_schema_sha256='f'*64)),
                   ('OPENED_WRONG_QUOTA_OWNER',dict(result,quota_owner_ref='different_owner'))]:
    ni,nc,nr=terminal_fixture(pre,value,'201','COMPLETED')
    assert model_lookup([ni],nc,nr,value,context)=='UNAVAILABLE_CONFLICT',name
    results.append(dict(case=name,result='UNAVAILABLE_CONFLICT'))
assert 'original_body_ascii' in schema['$defs']['stored_command']['required'],'DURABLE_ORIGINAL_POST_BODY_REQUIRED'

assert command['original_body_ascii']==hashes['canonical_body_ascii']
assert hashlib.sha256(command['original_body_ascii'].encode()).hexdigest()==command['original_preimage']['canonical_body_sha256']
results.append(dict(case='ORIGINAL_POST_BODY_RETAINED_AND_HASHED',result='MATCH'))
assert model_lookup([index],dict(command,original_body_ascii=' '+command['original_body_ascii']),receipt,result,context)=='UNAVAILABLE_CONFLICT'
results.append(dict(case='ORIGINAL_BODY_TAMPER_REJECTED',result='UNAVAILABLE_CONFLICT'))
body_changed=json.loads(hashes['canonical_body_ascii']);body_changed['role']='NODE_CONTROL'
original_changed=dict(pre,canonical_body_sha256=sha(body_changed))
value_changed=dict(result,command_digest=sha(original_changed))
ni,nc,nr=terminal_fixture(original_changed,value_changed,'201','COMPLETED')
nc['original_body_ascii']=encode(body_changed).decode()
assert model_lookup([ni],nc,nr,value_changed,context)=='UNAVAILABLE_CONFLICT'
results.append(dict(case='OPENED_ROLE_CONTRADICTS_DURABLE_ORIGINAL_BODY',result='UNAVAILABLE_CONFLICT'))

cross_input=json.loads((ROOT/'canonical-cross-language-vectors.json').read_bytes())
cross_observed=[]
for vector in cross_input['vectors']:
    raw=materialize(vector)
    try:decode(raw.encode('ascii'));accepted=True
    except ValueError:accepted=False
    try:written=encode(json.loads(raw));writer_accepted=True
    except ValueError:written=None;writer_accepted=False
    assert writer_accepted==vector['writer_accept']
    if writer_accepted:assert hashlib.sha256(written).hexdigest()==vector['writer_sha256_ascii']
    assert accepted==vector['accept']
    cross_observed.append(dict(id=vector.get('id'),raw_sha256=hashlib.sha256(raw.encode()).hexdigest(),
        raw_bytes=len(raw),accepted=accepted,sha256_ascii=hashlib.sha256(raw.encode()).hexdigest() if accepted else None,expected=vector['accept'],
        writer_accepted=writer_accepted,writer_sha256_ascii=hashlib.sha256(written).hexdigest() if writer_accepted else None))
node_report=json.loads((ROOT/'cross-language-node-validation.json').read_bytes())
assert node_report['cases']==cross_observed
(ROOT/'cross-language-python-validation.json').write_bytes(artifact_encode(dict(
    scope='PYTHON_NODE_MATCHED_EXACT_STRING_MODELS_ONLY',cases=cross_observed,runtime_ack=False)))

c3=jsonschema.Draft202012Validator({'$defs':schema['$defs'],'$ref':'#/$defs/c3_value'})
for number in (1,1.0,-0.0):assert list(c3.iter_errors(number))
for exact in ('1.0','-0.0','1e-07',True,False):c3.validate(exact)
assert len(schema['$defs']['command_preimage']['properties'])==15
results.append(dict(case='RESOURCE_C3_EXACT_STRINGS_BOOLEANS_NOT_NUMBERS',result='MATCH'))

validator.validate(json.loads((ROOT/'A1-DEPTH12-RAW.json').read_bytes()))
results.append(dict(case='A1_SCHEMA_VALID_DEPTH12_FRAME_CANONICAL_BOUNDARY',result='STRUCTURAL_MODEL_ONLY'))
validator.validate(json.loads((ROOT/'A6-NODECOUNT-RAW.json').read_bytes()))
try:decode((ROOT/'A6-NODECOUNT-RAW.json').read_bytes())
except ValueError as exc:assert str(exc)=='NODE_CAP'
else:raise AssertionError('ORIGINAL_A6_NODECOUNT_FRAME_MUST_REJECT')
results.append(dict(case='A6_SCHEMA_VALID_IN_BYTE_BOUNDS_FRAME_REJECTS_NODE_CAP',result='STRUCTURAL_MODEL_ONLY'))
report=dict(schema='unified.control-mux.closed-review4.validation',cases=results,
    result='SCHEMA_CANONICAL_LOOKUP_MODELS_MATCH',qualification='MODEL_ONLY_NOT_ENDPOINT_OR_AUTHORITY',
    provider_admission=False,load_qualified=False,runtime_ack=False,cross_language_vector_count=len(cross_observed))
(ROOT/'validation.json').write_bytes(artifact_encode(report))
print(json.dumps(dict(cases=len(results),result=report['result'],runtime_ack=False)))
