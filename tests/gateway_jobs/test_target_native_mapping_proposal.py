"""PURE CONTRACT DATA tests, never broker/Consul/worker/target/admission calls.

All SAMPLE profile/native13 objects are uncommissioned/unissued format vectors.
Hash sensitivity mutations are INVALID admissions, not successful mapped jobs.
"""
import base64
import copy
import hashlib
import json
from pathlib import Path
import re
import unittest
from jsonschema import Draft202012Validator, ValidationError

FIX=Path(__file__).with_name('target_native_mapping_fixtures')
DOC=Path(__file__).parents[2]/'docs/intelligence/jobs/target-native-review1'

def load(name):return json.loads((FIX/name).read_bytes())
def sha(raw):return hashlib.sha256(raw).hexdigest()
def outer_bytes(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')
def c3(value):
    def check(x,depth=0):
        if depth>12:raise ValueError('C3_DEPTH')
        if type(x) is dict:
            if len(x)>64:raise ValueError('C3_OBJECT')
            for k,v in x.items():check(k,depth+1);check(v,depth+1)
        elif type(x) is list:
            if len(x)>32:raise ValueError('C3_ARRAY')
            for v in x:check(v,depth+1)
        elif type(x) is str:
            if len(x)>16384 or any(not 32<=ord(c)<=126 for c in x):raise ValueError('C3_STRING')
        elif x is not None and type(x) is not bool:raise ValueError('C3_NUMBER')
    check(value);raw=outer_bytes(value)
    if len(raw)>16384:raise ValueError('C3_BYTES')
    return raw

def validators():
    return {name:Draft202012Validator(load(file)) for name,file in dict(
        direct='target-v1-schema.source.json',outer='a2-native-outer.schema.source.json',
        profile='a2-profile-v2.schema.source.json',native='native13-v1.schema.source.json',
        old_profile='broker-profile-v1.schema.source.json',error='a2-admission-error.schema.source.json').items()}

def verify_format_triple(raw,profile,native):
    """Untrusted proposed-byte joins ONLY; returns no permission or native handle."""
    if type(raw) is not bytes or not 0<len(raw)<=16384:raise ValueError('OUTER_BYTES')
    q=json.loads(raw);v=validators()
    if q.get('schema')=='unified.gateway.target-request.v1':raise ValueError('DIRECT_PROFILE_NOT_ADMISSIBLE')
    v['outer'].validate(q)
    if outer_bytes(q)!=raw:raise ValueError('NONCANONICAL')
    if outer_bytes(q['resource_budget'])!=outer_bytes(load('target-v1-request.source.json')['resource_budget']):raise ValueError('PREFLIGHT_BUDGET_TYPES')
    if re.fullmatch(r'[A-Za-z0-9_-]{1,128}',q['idempotency_key']) is None:
        raise ValueError('MAPPING_NOT_REPRESENTABLE')
    v['profile'].validate(profile);v['native'].validate(native)
    binding=profile['target_binding']
    encoded=binding['target_request_canonical_base64']
    decoded=base64.b64decode(encoded,validate=True)
    if base64.b64encode(decoded).decode()!=encoded or decoded!=raw:raise ValueError('RAW_BINDING')
    if binding['target_request_sha256']!=sha(raw):raise ValueError('OUTER_SHA')
    if binding['target_request_schema_sha256']!=sha((FIX/'a2-native-outer.schema.source.json').read_bytes()):raise ValueError('OUTER_SCHEMA_SHA')
    for field,outer_key,native_key in [('request_id','request_id','request_id'),
        ('actor_principal_id','principal_id','original_actor_principal_id'),
        ('quota_owner_id','quota_owner','quota_owner_id'),
        ('cluster_generation','authority_generation','cluster_generation'),
        ('idempotency_key','idempotency_key','idempotency_key')]:
        if not binding[field]==q[outer_key]==native[native_key]:raise ValueError('IDENTITY_JOIN:'+field)
    if native['original_actor_principal_id'] not in profile['principal_registry'].values():raise ValueError('ACTOR_REGISTRY_JOIN')
    if native['cluster_id']!=profile['cluster_id'] or native['job_id']!=binding['job_id']:raise ValueError('JOB_SCOPE')
    if native['commissioned_profile_sha256']!=sha(c3(profile)):raise ValueError('PROFILE_SHA')
    input_raw=(FIX/'a7-v1-request.source.json').read_bytes();i=json.loads(input_raw)
    if not sha(input_raw)==q['parameters_digest']==profile['input_request_sha256']==native['input_request_sha256']==binding['producer_request_sha256']:raise ValueError('INPUT_JOIN')
    if q['dataset_manifest_id']!='local-sha256:'+sha(outer_bytes(i['payload'])):raise ValueError('PAYLOAD_JOIN')
    if q['experiment_id']!=i['experiment']['id']:raise ValueError('EXPERIMENT_JOIN')
    if native['resources']!=profile['resources']:raise ValueError('RESOURCE_DOMAIN')
    if not native['producer_head']==profile['producer_head']==binding['producer_head']=='aed8a7c8a952f96803c207d5e90b133969a47f04':raise ValueError('PRODUCER_JOIN')
    if q['target_version']!='f3c01a23fa5baaeeeb28eb8e9397e72b5ef4d5a1':raise ValueError('TARGET_JOIN')
    # No context/issuer/lease/actual registry checked here: NEVER authority.

class TargetNativeProposal(unittest.TestCase):
    def setUp(self):
        self.t=(FIX/'a2-native-outer.FORMAT_ONLY.json').read_bytes()
        self.p=load('a2-profile.FORMAT_ONLY.json');self.n=load('a2-native13.FORMAT_ONLY.json')

    def test_primary_sources_and_exact_twenty_field_mapping(self):
        self.assertEqual(sha((FIX/'a7-v1-request.source.json').read_bytes()),'c548e2ffcd542d5d741682303694b3c6d06507740f158a6e30089b2d5355f648')
        source=(FIX/'target-v1-request.source.json').read_bytes()
        self.assertEqual(hashlib.sha1(b'blob '+str(len(source)).encode()+b'\0'+source).hexdigest(),'1089db56cb949cce862162dae048a1f3c1300def')
        root_schema=load('target-v1-schema.source.json');mapping=json.loads((DOC/'mapping.json').read_bytes())
        self.assertEqual(len(root_schema['required']),20)
        self.assertEqual(set(mapping['field_mapping']),set(root_schema['required']))
        self.assertEqual(set(mapping['native13_mapping']),set(load('native13-v1.schema.source.json')['required']))
        for name,record in json.loads((DOC/'A2-REFERENCE.json').read_bytes())['fixtures'].items():
            self.assertEqual(sha((FIX/name).read_bytes()),record['sha256'])

    def test_owner_schemas_are_closed_valid_and_distinct(self):
        ids=[]
        for file in ['target-v1-schema.source.json','a2-native-outer.schema.source.json','a2-profile-v2.schema.source.json','native13-v1.schema.source.json','broker-profile-v1.schema.source.json','a2-admission-error.schema.source.json']:
            s=load(file);Draft202012Validator.check_schema(s);ids.append(s['$id'])
            self.assertFalse(s['additionalProperties'])
        self.assertEqual(len(ids),len(set(ids)))

    def test_uncommissioned_format_triple_preserves_frozen13(self):
        verify_format_triple(self.t,self.p,self.n)
        self.assertEqual(sha((FIX/'native13-v1.schema.source.json').read_bytes()),'19357891fc022a87831009f17c663304ab72d88ed6ea344bb65c6bc325a321cc')
        self.assertEqual(len(self.n),13)
        self.assertNotEqual(sha(self.t),self.n['input_request_sha256'])
        self.assertNotEqual(self.n['commissioned_profile_sha256'],sha(self.t))
        self.assertFalse(validators()['old_profile'].is_valid(self.p))

    def test_direct_profile_never_upgraded(self):
        original=load('target-v1-request.source.json');raw=outer_bytes(original);saved=bytes(raw)
        with self.assertRaisesRegex(ValueError,'DIRECT_PROFILE_NOT_ADMISSIBLE'):verify_format_triple(raw,self.p,self.n)
        self.assertEqual(raw,saved);self.assertIsNone(original['authority_generation'])
        self.assertFalse(validators()['direct'].is_valid(json.loads(self.t)))

    def test_all_twenty_mutations_are_bound_not_admitted(self):
        q=json.loads(self.t);base_native_digest=sha(c3(self.n))
        self.assertEqual(len(q),20)
        for key in q:
            with self.subTest(field=key):
                changed=copy.deepcopy(q);changed[key]={'INVALID_MUTATION_FOR_HASH_ONLY':key};raw=outer_bytes(changed)
                with self.assertRaises((ValueError,ValidationError)):verify_format_triple(raw,self.p,self.n)
                p=copy.deepcopy(self.p);p['target_binding']['target_request_canonical_base64']=base64.b64encode(raw).decode();p['target_binding']['target_request_sha256']=sha(raw)
                n=copy.deepcopy(self.n);n['commissioned_profile_sha256']=sha(c3(p))
                self.assertNotEqual(sha(c3(n)),base_native_digest)

    def test_dot_key_refuses_instead_of_rewriting(self):
        q=json.loads(self.t);q['idempotency_key']='original.key'
        self.assertTrue(validators()['outer'].is_valid(q))
        with self.assertRaisesRegex(ValueError,'MAPPING_NOT_REPRESENTABLE'):verify_format_triple(outer_bytes(q),self.p,self.n)
        self.assertEqual(q['idempotency_key'],'original.key')

    def test_preissued_fields_and_result_handle_refused(self):
        for key,value in [('assignment_revision','1'),('fencing_token',{'claimed':True}),('result_artifact_ref','caller://result')]:
            q=json.loads(self.t);q[key]=value
            self.assertFalse(validators()['outer'].is_valid(q))
        self.assertIsNone(json.loads(self.t)['strategy_version'])

    def test_identity_and_input_hash_domains_not_aliases(self):
        for field,value in [('original_actor_principal_id',self.n['job_id']),('input_request_sha256',sha(self.t)),('producer_head',json.loads(self.t)['target_version']),('job_id',self.n['request_id'])]:
            n=copy.deepcopy(self.n);n[field]=value
            with self.subTest(field=field),self.assertRaises((ValueError,ValidationError)):verify_format_triple(self.t,self.p,n)

    def test_raw_hash_and_base64_join_refuse_changed_bytes(self):
        for encoded in [base64.b64encode(self.t+b' ').decode(),self.p['target_binding']['target_request_canonical_base64']+'\n']:
            p=copy.deepcopy(self.p);p['target_binding']['target_request_canonical_base64']=encoded
            with self.assertRaises((ValueError,ValidationError)):verify_format_triple(self.t,p,self.n)
        q=json.loads(self.t);q['resource_budget']['max_rows']=3.0
        self.assertNotEqual(outer_bytes(q),self.t)  #3.0==3 is NOT byte identity.
        with self.assertRaises((ValueError,ValidationError)):verify_format_triple(outer_bytes(q),self.p,self.n)

    def test_profile_principal_registry_mismatch_is_refused(self):
        p=copy.deepcopy(self.p);p['principal_registry']={key:self.n['job_id'] for key in p['principal_registry']}
        n=copy.deepcopy(self.n);n['commissioned_profile_sha256']=sha(c3(p))
        with self.assertRaisesRegex(ValueError,'ACTOR_REGISTRY_JOIN'):verify_format_triple(self.t,p,n)

    def test_float_budget_alias_refuses_even_with_rebound_hashes(self):
        q=json.loads(self.t);q['resource_budget']['max_rows']=3.0;raw=outer_bytes(q)
        # JSON Schema integer/const can accept a numeric3.0. Policy/codec must not.
        self.assertTrue(validators()['outer'].is_valid(q))
        p=copy.deepcopy(self.p);p['target_binding']['target_request_canonical_base64']=base64.b64encode(raw).decode()
        p['target_binding']['target_request_sha256']=sha(raw)
        n=copy.deepcopy(self.n);n['commissioned_profile_sha256']=sha(c3(p))
        with self.assertRaisesRegex(ValueError,'PREFLIGHT_BUDGET_TYPES'):verify_format_triple(raw,p,n)

    def test_no_profile_self_hash_or_native_digest_cycle(self):
        forbidden={'commissioned_profile_sha256','lab_submit_sha256','native_intent_sha256','native13','publication_receipt'}
        def keys(value):
            result=set()
            if isinstance(value,dict):
                result.update(value)
                for v in value.values():result.update(keys(v))
            elif isinstance(value,list):
                for v in value:result.update(keys(v))
            return result
        self.assertFalse(keys(self.p)&forbidden)
        self.assertNotIn('commissioned_profile_sha256',json.loads(self.t))
        self.assertEqual(sha(c3(self.p)),self.n['commissioned_profile_sha256'])
        self.assertEqual(c3(self.p),(FIX/'a2-profile.FORMAT_ONLY.json').read_bytes())
        self.assertEqual(c3(self.n),(FIX/'a2-native13.FORMAT_ONLY.json').read_bytes())

    def test_encoding_overflow_refuses_without_truncation(self):
        p=copy.deepcopy(self.p);p['target_binding']['target_request_canonical_base64']='A'*21848
        self.assertTrue(validators()['profile'].is_valid(p))  #Structuralupperbound != C3bound.
        with self.assertRaisesRegex(ValueError,'C3_STRING'):c3(p)
        self.assertEqual(len(p['target_binding']['target_request_canonical_base64']),21848)

    def test_error_data_keeps_known_fact_and_forbids_permissions(self):
        schema=load('a2-admission-error.schema.source.json');props=schema['properties']
        error={key:(None if props[key].get('type')==['string','null'] else False) for key in props}
        error.update(schema=props['schema']['const'],code='NATIVE_OUTCOME_UNKNOWN',request_id=self.n['request_id'],
            target_request_sha256=sha(self.t),lab_submit_sha256=sha(c3(self.n)),this_attempt='UNCERTAIN',
            native_original_state='ADMITTED',execution_permitted=False,retry_permitted=False,hold_release_permitted=False)
        v=Draft202012Validator(schema);v.validate(error)
        for name in ('execution_permitted','retry_permitted','hold_release_permitted'):
            bad=dict(error);bad[name]=True;self.assertFalse(v.is_valid(bad))
        bad=dict(error,extra_claim='proof');self.assertFalse(v.is_valid(bad))
        self.assertEqual(error['native_original_state'],'ADMITTED')

if __name__=='__main__':unittest.main()
