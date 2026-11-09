"""Closed native broker record data; never a commissioning/authority tool."""
import hashlib,json
from pathlib import Path

OUT=Path(__file__).resolve().parent
def ref(name):return {'$ref':'#/$defs/'+name}
def closed(props):return dict(type='object',properties=props,required=sorted(props),additionalProperties=False)
def const(value):return {'const':value}
defs=dict(uuid4=dict(type='string',pattern=r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}(?![\s\S])'),
    native_session=dict(type='string',minLength=36,maxLength=36,pattern=r'^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}(?![\s\S])'),
    sha256=dict(type='string',pattern=r'^[0-9a-f]{64}(?![\s\S])'),
    id=dict(type='string',pattern=r'^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}(?![\s\S])'),
    utc=dict(type='string',pattern=r'^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z(?![\s\S])'),
    revision=dict(type='string',pattern=r'^[1-9][0-9]{0,18}(?![\s\S])'))
records=dict(
    profile=closed(dict(schema=const('unified.authority.research-lab-profile.v1-review1'),cluster_id=ref('uuid4'),realm_id=ref('uuid4'),
        principal_registry=dict(type='object',minProperties=1,maxProperties=32,propertyNames=ref('sha256'),additionalProperties=ref('uuid4')),
        input_request_sha256=const('c548e2ffcd542d5d741682303694b3c6d06507740f158a6e30089b2d5355f648'),
        producer_head=const('aed8a7c8a952f96803c207d5e90b133969a47f04'),resources=closed(dict(cpu_millicores=const('1000'),
            resident_memory_bytes=const('268435456'),max_artifact_bytes=const('1048576'))),
        expiry_semantics=const('NATIVE_SESSION_INVALIDATION_NOT_UTC_AT_COMMIT'),expires_utc=ref('utc'))),
    principal=closed(dict(schema=const('unified.authority.research-lab-principal.v1-review1'),actor_id=ref('uuid4'),service_id=ref('uuid4'),
        certificate_sha256=ref('sha256'),quota_owner_id=ref('id'),policy_id=ref('uuid4'),profile_sha256=ref('sha256'),state={'enum':['ACTIVE','REVOKED']})),
    policy=closed(dict(schema=const('unified.authority.research-lab-policy.v1-review1'),policy_id=ref('uuid4'),actor_id=ref('uuid4'),
        profile_sha256=ref('sha256'),revision=ref('revision'),state={'enum':['ACTIVE','REVOKED']},
        scopes=dict(type='array',minItems=1,maxItems=3,uniqueItems=True,items={'enum':['SUBMIT_RESEARCH','READ_RESEARCH','CANCEL_OWN_JOB']}),expires_utc=ref('utc'))),
    principal_session=closed(dict(schema=const('unified.authority.research-lab-principal-session.v1-review1'),actor_id=ref('uuid4'),service_id=ref('uuid4'),
        certificate_sha256=ref('sha256'),session_id=ref('native_session'),policy_id=ref('uuid4'),profile_sha256=ref('sha256'),quota_owner_id=ref('id'))))
members=[]
for name,body in records.items():
    value={'$schema':'https://json-schema.org/draft/2020-12/schema','$id':'urn:unified:research-identity:'+name+':v1-review1','$defs':defs,**body}
    raw=json.dumps(value,sort_keys=True,separators=(',',':')).encode()+b'\n'
    path=name+'.schema.json';(OUT/path).write_bytes(raw)
    members.append(dict(path=path,sha256=hashlib.sha256(raw).hexdigest()))
(OUT/'RECORD-MANIFEST.json').write_text(json.dumps(dict(scope='CLOSED_NATIVE_RECORD_DATA_NOT_ISSUED_AUTHORITY',members=members),indent=2)+'\n',encoding='utf-8')
