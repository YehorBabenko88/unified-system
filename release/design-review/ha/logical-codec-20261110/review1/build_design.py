"""Pure design artifact builder. No application imports, network, Job or authority.

All IDs, native indices, receipts and sessions below are UNISSUED synthetic DATA.
Generated native-shaped JSON is NOT admitted input to any execution interface.
"""
import base64
import copy
import hashlib
import json
from pathlib import Path
from jsonschema import Draft202012Validator

OUT=Path(__file__).resolve().parent
PREV=OUT.parent
def raw(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def sha(v):return hashlib.sha256(v).hexdigest()
def c3(v):
    def walk(x,d=0):
        assert d<=12
        if x is None or type(x) is bool:return
        if type(x) is str:assert len(x)<=16384 and all(32<=ord(c)<=126 for c in x);return
        if type(x) is list:
            assert len(x)<=32
            for a in x:walk(a,d+1)
            return
        assert type(x) is dict and len(x)<=64
        for k,a in x.items():assert type(k) is str;walk(a,d+1)
    walk(v);b=raw(v);assert len(b)<=16384;return b
def save(name,v):
    p=OUT/name;assert not p.exists();p.write_bytes(raw(v)+b'\n')
old=json.loads((PREV/'RESEARCH-LAB-ADMISSION-REVIEW2/quota-ledger.schema.json').read_bytes())
defs={k:copy.deepcopy(old['$defs'][k]) for k in ('u63','positive','sha256','id','uuid4')}
defs['session']={'type':'string','pattern':'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[89ab][0-9a-f]{3}-[0-9a-f]{12}(?![\\s\\S])'}
def ref(s):return {'$ref':'#/$defs/'+s}
def const(v):return {'const':v}
def nullable(s):return {'oneOf':[ref(s),{'type':'null'}]}
def schema(name,props):
    p={'schema':const('unified.authority.logical-'+name+'.v1-review1'),**props}
    return {'$schema':'https://json-schema.org/draft/2020-12/schema','$id':'urn:unified:logical:'+name+':v1-review1','$defs':defs,'type':'object','additionalProperties':False,'properties':p,'required':list(p)}
schemas={}
schemas['rights']=schema('rights',dict(policy_id=ref('uuid4'),actor_id=ref('uuid4'),profile_sha256=ref('sha256'),revision=ref('positive'),state={'enum':['ACTIVE','REVOKED']},scopes={'type':'array','minItems':1,'maxItems':3,'uniqueItems':True,'items':{'enum':['QUEUE_RESEARCH','CANCEL_QUEUED_OWN_JOB','READ_QUEUED_OWN_JOB']}},expires_utc={'type':'string','maxLength':32,'pattern':'^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z(?![\\s\\S])'},expiry_requirement=const('STRICT_UTC_AT_RAFT_COMMIT_UNIMPLEMENTED')))
schemas['quota-policy']=schema('quota-policy',dict(cluster_id=ref('uuid4'),cluster_generation=ref('uuid4'),realm_id=ref('uuid4'),quota_owner_id=ref('id'),policy_revision=ref('positive'),max_queued_jobs={'enum':['0','1']},admission_mode=const('LOGICAL_ONLY'),enabled={'type':'boolean'},commissioning_receipt_id=ref('uuid4'),rights_schema_sha256=ref('sha256')))
schemas['quota-ledger']=schema('quota-ledger',dict(realm_id=ref('uuid4'),quota_owner_id=ref('id'),revision=ref('u63'),previous_revision=nullable('u63'),queued_jobs={'enum':['0','1']},active_jobs=const('0')))
jobprops=dict(job_id=ref('uuid4'),original_request_id=ref('uuid4'),original_intent_sha256=ref('sha256'),target_sha256=ref('sha256'),commissioned_profile_sha256=ref('sha256'),original_actor_principal_id=ref('uuid4'),quota_owner_id=ref('id'),original_actor_session_id=ref('session'),sequence=ref('positive'),previous_sequence=ref('u63'),state={'enum':['QUEUED_PRE_ADMISSION','CANCELLED_PRE_ADMISSION']},logical_quota_state={'enum':['HELD','RELEASED']},queue_receipt_id=ref('uuid4'),phase_kind={'enum':['QUEUE','CANCEL_QUEUE']},phase_ref=ref('uuid4'),assignment_id=const(None),resource_hold_id=const(None),worker_session_id=const(None),lease_id=const(None),dispatch_permission=const(False),publication=const('NOT_AUTHORIZED'))
schemas['job']=schema('job',jobprops)
schemas['job']['allOf']=[{'if':{'properties':{'state':const('QUEUED_PRE_ADMISSION')}},'then':{'properties':{'logical_quota_state':const('HELD'),'phase_kind':const('QUEUE'),'sequence':const('1'),'previous_sequence':const('0')}}},{'if':{'properties':{'state':const('CANCELLED_PRE_ADMISSION')}},'then':{'properties':{'logical_quota_state':const('RELEASED'),'phase_kind':const('CANCEL_QUEUE'),'sequence':const('2'),'previous_sequence':const('1')}}}]
schemas['phase-receipt']=schema('phase-receipt',dict(operation={'enum':['QUEUE','CANCEL_QUEUE']},request_id=ref('uuid4'),intent_sha256=ref('sha256'),original_submit_request_id=ref('uuid4'),original_submit_intent_sha256=ref('sha256'),job_id=ref('uuid4'),job_sequence=ref('positive'),quota_owner_id=ref('id'),quota_previous_revision=ref('u63'),quota_revision=ref('positive'),logical_quota_delta={'enum':['PLUS_ONE','MINUS_ONE']},leader_generation=ref('uuid4'),leader_lock_index=ref('positive'),actor_principal_id=ref('uuid4'),actor_session_id=ref('session'),previous_job_sequence=ref('u63'),effect_allowed=const(False),resource_reserved=const(False),dispatch_allowed=const(False),committed_at_utc=const(None),commit_time_status=const('UNKNOWN_COMMIT_INSTANT')))
for name,s in schemas.items():Draft202012Validator.check_schema(s);save(name+'.schema.json',s)
U=lambda n:'00000000-0000-4000-8000-'+str(n).zfill(12)
original=(PREV/'TARGET-NATIVE-MAPPING-REVIEW1-20261109/SAMPLE-NOT-ISSUED-lab-submit.canonical.json').read_bytes().rstrip(b'\n')
profile=(PREV/'TARGET-NATIVE-MAPPING-REVIEW1-20261109/SAMPLE-NOT-COMMISSIONED-profile.canonical.json').read_bytes().rstrip(b'\n')
intent=json.loads(original);P=json.loads(profile);S=sha(profile);assert intent['commissioned_profile_sha256']==S
T=base64.b64decode(P['target_binding']['target_request_canonical_base64'],validate=True);H=sha(T);assert P['target_binding']['target_request_sha256']==H
assert c3(intent)==original and c3(P)==profile
D=sha(original);cluster=intent['cluster_id'];realm=P['realm_id'];q=intent['quota_owner_id'];actor=intent['original_actor_principal_id'];sid=U(5)
N='unified/'+cluster;R=N+'/runtime-v1';L=R+'/research-lab-v1/'+realm;Q=L+'/quotas/'+q
index=2**63-1
def check(k):return {'KV':dict(Verb='check-index',Key=k,Index=index)}
def absent(k):return {'KV':dict(Verb='check-not-exists',Key=k)}
def session(k,s):return {'KV':dict(Verb='check-session',Key=k,Session=s)}
def cas(k,v,i):return {'KV':dict(Verb='cas',Key=k,Index=i,Value=base64.b64encode(c3(v)).decode('ascii'))}
def record(name,**kw):return dict(schema=schemas[name]['properties']['schema']['const'],**kw)
policy=record('quota-policy',cluster_id=cluster,cluster_generation=intent['cluster_generation'],realm_id=realm,quota_owner_id=q,policy_revision='1',max_queued_jobs='1',admission_mode='LOGICAL_ONLY',enabled=False,commissioning_receipt_id=U(44),rights_schema_sha256=sha((OUT/'rights.schema.json').read_bytes()))
ledger=record('quota-ledger',realm_id=realm,quota_owner_id=q,revision='1',previous_revision='0',queued_jobs='1',active_jobs='0')
job=record('job',job_id=intent['job_id'],original_request_id=intent['request_id'],original_intent_sha256=D,target_sha256=H,commissioned_profile_sha256=S,original_actor_principal_id=actor,quota_owner_id=q,original_actor_session_id=sid,sequence='1',previous_sequence='0',state='QUEUED_PRE_ADMISSION',logical_quota_state='HELD',queue_receipt_id=intent['request_id'],phase_kind='QUEUE',phase_ref=intent['request_id'],assignment_id=None,resource_hold_id=None,worker_session_id=None,lease_id=None,dispatch_permission=False,publication='NOT_AUTHORIZED')
receipt=record('phase-receipt',operation='QUEUE',request_id=intent['request_id'],intent_sha256=D,original_submit_request_id=intent['request_id'],original_submit_intent_sha256=D,job_id=intent['job_id'],job_sequence='1',quota_owner_id=q,quota_previous_revision='0',quota_revision='1',logical_quota_delta='PLUS_ONE',leader_generation=intent['cluster_generation'],leader_lock_index=str(index),actor_principal_id=actor,actor_session_id=sid,previous_job_sequence='0',effect_allowed=False,resource_reserved=False,dispatch_allowed=False,committed_at_utc=None,commit_time_status='UNKNOWN_COMMIT_INSTANT')
def keys(c):
    common=sha(c3(dict(schema='unified.authority.command-key.v1',cluster_id=cluster,quota_owner_id=q,original_actor_principal_id=actor,idempotency_key=c['idempotency_key'])))
    domain=sha(c3(dict(schema='unified.authority.research-lab-command-key.v1-review1',cluster_id=cluster,realm_id=realm,quota_owner_id=q,original_actor_principal_id=actor,idempotency_key=c['idempotency_key'])))
    return R+'/commands/'+domain,N+'/authority-v1/requests/'+c['request_id'],N+'/authority-v1/command-keys/'+common,R+'/receipts/'+c['request_id'],common,domain
def bindings(c,ks):
    command,request,commonkey,receiptkey,common,domain=ks
    v=dict(cluster_id=cluster,common_key_sha256=common,domain='GRID_AUTHORITY_RUNTIME_V1',original_actor_principal_id=actor,original_actor_session_id=sid,original_command_digest=sha(c3(c)),original_command_key_sha256=domain,profile_schema_sha256='19357891fc022a87831009f17c663304ab72d88ed6ea344bb65c6bc325a321cc',quota_owner_id=q,receipt_ref=c['request_id'],request_id=c['request_id'])
    return [cas(command,dict(schema='unified.authority.research-lab-logical-command.v1-review1',intent=c),0),cas(request,dict(schema='unified.authority.request-binding.v1',**v),0),cas(commonkey,dict(schema='unified.authority.command-key-binding.v1',**v),0)]
identity=[check(N+'/commands/generation'),session(N+'/leader',U(90)),check(N+'/leader'),check(L+'/profile-registry/'+S),check(L+'/principals/'+actor),check(L+'/policies/'+U(15)),check(L+'/principal-sessions/'+sid+'/lock'),session(L+'/principal-sessions/'+sid+'/lock',sid),check(N+'/authority-v1/profiles/19357891fc022a87831009f17c663304ab72d88ed6ea344bb65c6bc325a321cc'),check(Q+'/policy'),check(R+'/receipts/'+U(44))]
jkey=L+'/jobs/'+intent['job_id'];ks=keys(intent)
queue=identity+[absent(k) for k in (*ks[:4],jkey)]+bindings(intent,ks)+[cas(ks[3],receipt,0),cas(jkey,job,0),cas(Q+'/ledger',ledger,index)]
cancel=dict(schema='unified.gateway.lab-job-cancel.v1-review1',operation='CANCEL_OWN_JOB',cluster_id=cluster,cluster_generation=intent['cluster_generation'],request_id=U(51),job_id=intent['job_id'],original_actor_principal_id=actor,quota_owner_id=q,idempotency_key='cancel-format-only-1',commissioned_profile_sha256=S,original_submit_request_id=intent['request_id'],original_submit_intent_sha256=D)
ck=keys(cancel);canceljob={**job,'state':'CANCELLED_PRE_ADMISSION','logical_quota_state':'RELEASED','sequence':'2','previous_sequence':'1','phase_kind':'CANCEL_QUEUE','phase_ref':cancel['request_id']}
cancelreceipt={**receipt,'operation':'CANCEL_QUEUE','request_id':cancel['request_id'],'intent_sha256':sha(c3(cancel)),'job_sequence':'2','previous_job_sequence':'1','quota_previous_revision':'1','quota_revision':'2','logical_quota_delta':'MINUS_ONE'}
cancelledger={**ledger,'revision':'2','previous_revision':'1','queued_jobs':'0'}
cancelplan=identity+[check(k) for k in ks[:4]]+[absent(k) for k in ck[:4]]+bindings(cancel,ck)+[cas(ck[3],cancelreceipt,0),cas(jkey,canceljob,index),cas(Q+'/ledger',cancelledger,index)]
for name,v in [('quota-policy',policy),('quota-ledger',ledger),('job',job),('phase-receipt',receipt),('quota-ledger',cancelledger),('job',canceljob),('phase-receipt',cancelreceipt)]:Draft202012Validator(schemas[name]).validate(v)
negative=copy.deepcopy(ledger);negative['uncertain_jobs']='0';assert not Draft202012Validator(schemas['quota-ledger']).is_valid(negative)
negative=copy.deepcopy(job);negative['assignment_id']=U(70);assert not Draft202012Validator(schemas['job']).is_valid(negative)
measure={}
for name,ops in [('queue',queue),('cancel',cancelplan)]:
    assert all('/workers/' not in o['KV']['Key'] and '/assignments/' not in o['KV']['Key'] and '/resource-holds/' not in o['KV']['Key'] and '/leases/' not in o['KV']['Key'] for o in ops)
    b=raw(ops);save(name+'.FORMAT-ONLY.native-plan.json',ops)
    measure[name]={'operations':len(ops),'encoded_bytes_excluding_file_newline':len(b),'sha256_excluding_file_newline':sha(b),'under_candidate_64op_32768bytes_budget':len(ops)<=64 and len(b)<=32768,'operation_verb_counts':{v:sum(o['KV']['Verb']==v for o in ops) for v in sorted({o['KV']['Verb'] for o in ops})}}
save('measurement.json',dict(scope='PURE_FORMAT_ONLY_NOT_SENDABLE_NO_ISSUED_IDENTITIES_OR_VALID_AUTHORIZATION',plans=measure,raw_sizes=dict(target20=len(T),profile=len(profile),native13=len(original),queue_job=len(c3(job)),queue_receipt=len(c3(receipt))),strict_time_policy_satisfied=False,old_profile_expiry_semantics=P['expiry_semantics'],policy_enabled=False,measured_sample_only_not_worst_case=True,unmeasured=['maximum_accepted_profile_and_wire_envelope','native_response_wrapper_and_result_limit','actual_commissioning_receipt_schema','future_opaque_capture_observation_and_custody_limits'],schema_checks='5 schemas structurally valid;7 candidate records schema-checked;2 selected semantic-denial examples (not runtime contract tests)',application_imports=0,native_rpc=0,job_calls=0,physical_calls=0))
print(json.dumps(measure,indent=2));print('PURE_DESIGN_ONLY; STRICT_TIME_GATE_CLOSED; NO_APPLICATION_IMPORTS_OR_RPC')
