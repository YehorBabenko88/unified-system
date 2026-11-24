"""Generate closed record DATA from the current canonical source contracts.

No commissioning, broker, SourceFence, network or authority code is executed.
Importing this module never writes source. Inconsistent inputs refuse before
any generated file is written.
"""
import ast,hashlib,json,re
from pathlib import Path
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]

def _need(value):
    if not value:raise ValueError('CANONICAL_RECORD_INPUT_DRIFT')

def _read(path,limit=262144):
    with path.open('rb') as stream:raw=stream.read(limit+1)
    _need(len(raw)<=limit)
    return raw

def source_bindings(root):
    root=Path(root)
    cohort=json.loads(_read(root/'integration/four_owner/cohort.json'))
    _need(type(cohort) is dict and cohort.get('schema')=='unified.four-owner.source-cohort.v1'
          and cohort.get('release_status')=='NO_GO' and cohort.get('execution_authority') is False
          and cohort.get('trading_authorized') is False)
    sources=cohort.get('sources')
    _need(type(sources) is dict and set(sources)=={'unified_system','market_data','math','terminan'})
    _need(sources['unified_system']['commit']=='ENCLOSING_HEAD')
    heads={}
    for owner,repository,package in (('math','YehorBabenko88/math','market_math'),('terminan','YehorBabenko88/Terminan','terminan')):
        spec=sources[owner]
        _need(type(spec) is dict and spec.get('repository')==repository and spec.get('package')==package)
        value=spec.get('commit');_need(type(value) is str and re.fullmatch('[a-f0-9]{40}',value) is not None);heads[owner]=value
    raw_schema=_read(root/'docs/intelligence/canonical-native-profile/request.schema.json')
    schema=json.loads(raw_schema);props=schema['properties']
    _need(schema.get('additionalProperties') is False and props['schema']['const']=='unified.gateway.target-native-request.v2'
          and props['target_kind']['const']=='terminan' and props['target_capability']['const']=='terminan.ohlcv.untouched_levels.v1'
          and props['target_version']['const']==heads['terminan'])
    digest=props['parameters_digest']['const'];_need(type(digest) is str and re.fullmatch('[a-f0-9]{64}',digest) is not None)
    result=dict(producer_head=heads['terminan'],math_head=heads['math'],input_request_sha256=digest,target_request_schema_sha256=hashlib.sha256(raw_schema).hexdigest())
    manifest=json.loads(_read(root/'release/integration/native-negative-v2/manifest.json'))
    binding=manifest['canonical_native_binding']
    _need(binding['profile_schema']=='unified.authority.canonical-research-profile.v3'
          and binding['terminan_head']==result['producer_head'] and binding['math_head']==result['math_head']
          and binding['target_schema_sha256']==result['target_request_schema_sha256'])
    broker_raw=_read(root/'unified_system/gateway_research_identity.py')
    _need(manifest['root_modules_sha256']['unified_system/gateway_research_identity.py']==hashlib.sha256(broker_raw).hexdigest())
    expected={'_PRODUCER':result['producer_head'],'_MATH':result['math_head'],'_INPUT_SHA':result['input_request_sha256'],'_TARGET_SCHEMA_SHA':result['target_request_schema_sha256']}
    found={}
    for node in ast.parse(broker_raw).body:
        if isinstance(node,ast.Assign):
            for target in node.targets:
                if isinstance(target,ast.Name) and target.id in expected:
                    _need(target.id not in found and isinstance(node.value,ast.Constant) and type(node.value.value) is str)
                    found[target.id]=node.value.value
    _need(found==expected)
    return result

def ref(name):return {'$ref':'#/$defs/'+name}
def closed(props):return dict(type='object',properties=props,required=sorted(props),additionalProperties=False)
def const(value):return {'const':value}
defs=dict(uuid4=dict(type='string',pattern=r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}(?![\s\S])'),
    native_session=dict(type='string',minLength=36,maxLength=36,pattern=r'^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}(?![\s\S])'),
    sha256=dict(type='string',pattern=r'^[0-9a-f]{64}(?![\s\S])'),
    id=dict(type='string',pattern=r'^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}(?![\s\S])'),
    utc=dict(type='string',pattern=r'^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z(?![\s\S])'),
    revision=dict(type='string',pattern=r'^[1-9][0-9]{0,18}(?![\s\S])'))

def render_records(root=ROOT):
    pin=source_bindings(root)
    records=dict(
        profile=closed(dict(schema=const('unified.authority.canonical-research-profile.v3'),cluster_id=ref('uuid4'),realm_id=ref('uuid4'),
            principal_registry=dict(type='object',minProperties=1,maxProperties=1,propertyNames=ref('sha256'),additionalProperties=ref('uuid4')),
            input_request_sha256=const(pin['input_request_sha256']),
            producer_head=const(pin['producer_head']),math_head=const(pin['math_head']),target_binding=closed(dict(target_request_schema_sha256=const(pin['target_request_schema_sha256']),target_request_canonical_base64=dict(type='string',minLength=1,maxLength=21848),target_request_sha256=ref('sha256'),request_id=ref('uuid4'),job_id=ref('uuid4'),idempotency_key=dict(type='string',minLength=1,maxLength=128,pattern=r'^[A-Za-z0-9_-]+(?![\s\S])'),cluster_generation=ref('uuid4'),actor_principal_id=ref('uuid4'),quota_owner_id=dict(type='string',minLength=1,maxLength=128,pattern=r'^[A-Za-z0-9_-]+(?![\s\S])'),producer_request_sha256=const(pin['input_request_sha256']),producer_head=const(pin['producer_head']),math_head=const(pin['math_head']))),resources=closed(dict(cpu_millicores=const('1000'),
                resident_memory_bytes=const('268435456'),max_artifact_bytes=const('1048576'))),
            expiry_semantics=const('NATIVE_SESSION_INVALIDATION_NOT_UTC_AT_COMMIT'),expires_utc=ref('utc'))),
        principal=closed(dict(schema=const('unified.authority.research-lab-principal.v1-review1'),actor_id=ref('uuid4'),service_id=ref('uuid4'),
            certificate_sha256=ref('sha256'),quota_owner_id=ref('id'),policy_id=ref('uuid4'),profile_sha256=ref('sha256'),state={'enum':['ACTIVE','REVOKED']})),
        policy=closed(dict(schema=const('unified.authority.research-lab-policy.v1-review1'),policy_id=ref('uuid4'),actor_id=ref('uuid4'),
            profile_sha256=ref('sha256'),revision=ref('revision'),state={'enum':['ACTIVE','REVOKED']},
            scopes=dict(type='array',minItems=1,maxItems=3,uniqueItems=True,items={'enum':['SUBMIT_RESEARCH','READ_RESEARCH','CANCEL_OWN_JOB']}),expires_utc=ref('utc'))),
        principal_session=closed(dict(schema=const('unified.authority.research-lab-principal-session.v1-review1'),actor_id=ref('uuid4'),service_id=ref('uuid4'),
            certificate_sha256=ref('sha256'),session_id=ref('native_session'),policy_id=ref('uuid4'),profile_sha256=ref('sha256'),quota_owner_id=ref('id'))))
    output={}
    for name,record in records.items():
        value={'$schema':'https://json-schema.org/draft/2020-12/schema','$id':'urn:unified:research-identity:'+name+(':v3' if name=='profile' else ':v1-review1'),'$defs':defs,**record}
        output[name+'.schema.json']=json.dumps(value,sort_keys=True,separators=(',',':')).encode()+b'\n'
    return output

def render_manifest(records):
    members=[dict(path=name,sha256=hashlib.sha256(raw).hexdigest()) for name,raw in records.items()]
    return (json.dumps(dict(scope='CLOSED_NATIVE_RECORD_DATA_NOT_ISSUED_AUTHORITY',members=members),indent=2)+'\n').encode('utf8')

def main():
    records=render_records()
    manifest=render_manifest(records)
    for name,raw in records.items():(OUT/name).write_bytes(raw)
    (OUT/'RECORD-MANIFEST.json').write_bytes(manifest)

if __name__=='__main__':main()
