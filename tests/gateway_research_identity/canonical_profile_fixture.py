"""Canonical request DATA for disposable tests, never a commissioning API."""
import base64,hashlib,json
PROFILE_SCHEMA='unified.authority.canonical-research-profile.v3'
TARGET_SCHEMA_SHA='91a83569d749641966f974d61dcf1568704da1855940944bad3a9f137874850a'
INPUT_SHA='4a8b7be2fa7cfbf72399e4abf864287feb8b10a28977aea2970846b8fb97e7e9'
PRODUCER='75a906d36574bfdc19acd966e79a6c168dc71ad4'
MATH='a5868944bf1bae813403a32b22d329c1da6f8238'
def target_bytes(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def bind_profile(profile,*,request_id,job_id,generation,actor,quota_owner):
 target=dict(schema='unified.gateway.target-native-request.v2',request_id=request_id,target_kind='terminan',target_capability='terminan.ohlcv.untouched_levels.v1',target_version=PRODUCER,dataset_manifest_id='local-sha256:44639dea28a646d2a308655d7adc3f85e24a90bda22971632f88d1dd9760c938',dataset_revision='CANONICAL_FIXTURE_2',experiment_id='fixture.gateway.btc.levels',strategy_version=None,parameters_digest=INPUT_SHA,execution_mode='NATIVE_RESEARCH_ADMISSION_REQUEST_NOT_PERMISSION',resource_budget=dict(max_input_bytes=16384,max_output_bytes=16384,max_rows=3,max_executions=1),quota_owner=quota_owner,principal_id=actor,authority_generation=generation,assignment_revision=None,fencing_token=None,idempotency_key='native_original_2',result_schema='unified.gateway.native-target-observation.v2',result_artifact_ref=None)
 raw=target_bytes(target)
 profile.update(schema=PROFILE_SCHEMA,input_request_sha256=INPUT_SHA,producer_head=PRODUCER,math_head=MATH,target_binding=dict(target_request_schema_sha256=TARGET_SCHEMA_SHA,target_request_canonical_base64=base64.b64encode(raw).decode('ascii'),target_request_sha256=hashlib.sha256(raw).hexdigest(),request_id=request_id,job_id=job_id,idempotency_key=target['idempotency_key'],cluster_generation=generation,actor_principal_id=actor,quota_owner_id=quota_owner,producer_request_sha256=INPUT_SHA,producer_head=PRODUCER,math_head=MATH))
 return target
