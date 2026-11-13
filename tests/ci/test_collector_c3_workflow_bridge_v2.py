"""Inert static-selector controls; no approval, HTTP or native qualification."""
import copy,hashlib,importlib.util,json,os,stat,sys,types,unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).absolute().parents[2]
sys.path.insert(0,str(ROOT))
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
bridge=load(ROOT/'scripts/ci_collector_c3_workflow_bridge_v2.py','static_bridge_under_test')
fixtures=load(Path(os.environ.get('C3_STATIC_SUPPLIER_ROOT',str(ROOT)))/'tests/test_ci_collector_operational_admission.py','frozen_v2_fixture_data')
from unified_system import collector_operational_review as codec

class StaticSelectorTests(unittest.TestCase):
    def setUp(self):
        parent=Path(os.environ['C3_STATIC_TEST_SCRATCH']);self.root=parent/self._testMethodName;self.root.mkdir()
        self.path=self.root/'integration/collector/v1/source-inputs.json';self.path.parent.mkdir(parents=True)
        self.manifest=b'{"source":"inert bounded manifest bytes"}\n';self.path.write_bytes(self.manifest)
        self.auth=fixtures.authorization();self.auth['source']['source_manifest_sha256']=hashlib.sha256(self.manifest).hexdigest()
        self.raw=codec.encode(self.auth)
        self.ctx=dict(event='workflow_dispatch',repository=codec.REPOSITORY,sha='a'*40,source_sha='a'*40,attempt='1',run_id='123',actor='actor',authorization_commit='e'*40,authorization_sha256=hashlib.sha256(self.raw).hexdigest(),job_name='collector-preflight',runner_name='GitHub Actions 1')
        pin={'bytes':len(self.manifest),'sha256':hashlib.sha256(self.manifest).hexdigest(),'oid':hashlib.sha1(b'blob '+str(len(self.manifest)).encode()+b'\0'+self.manifest).hexdigest()}
        self.snapshot={'head':'a'*40,'tree':'b'*40,'files':{'integration/collector/v1/source-inputs.json':pin},'directories':['integration','integration/collector','integration/collector/v1']}
    def call(self,raw=None,ctx=None,snapshot=None,now=fixtures.NOW):
        with patch.object(bridge,'_primary_source',return_value=copy.deepcopy(self.snapshot if snapshot is None else snapshot)) as acquire:
            value=bridge.select_static_authorization(self.raw if raw is None else raw,context=self.ctx if ctx is None else ctx,source_root=self.root,now=now)
        return value,acquire
    def blocked(self,raw=None,ctx=None,snapshot=None,code=None,now=fixtures.NOW):
        with self.assertRaises(bridge.StaticPreflightBlocked) as caught:self.call(raw,ctx,snapshot,now)
        if code:self.assertEqual(caught.exception.code,code)
        self.assertEqual(str(caught.exception),caught.exception.code)
    def test_valid_source_is_detached_static_data_not_admission(self):
        value,acquire=self.call();self.assertEqual(value['status'],'STATIC_VALID_NOT_ADMITTED');self.assertIs(value['selected'],False)
        self.assertEqual(value['source'],self.auth['source']);self.assertEqual(value['target'],self.auth['target']);self.assertEqual(value['source_evidence']['files'],1)
        self.assertIn('QUALIFIED_FACTORY_MISSING',value['missing_gates']);self.assertIn('QUALIFIED_ARTIFACT_SOURCE_CLOSURE_MISSING',value['missing_gates'])
        self.assertEqual(acquire.call_count,1);value['target']['runner_label']='fake';self.assertEqual(self.call()[0]['target'],self.auth['target'])
    def test_push_and_pull_request_deny_before_any_source_io(self):
        for event in ('push','pull_request','pull_request_target'):
            ctx=dict(self.ctx,event=event)
            with patch.object(bridge,'_primary_source',side_effect=AssertionError('IO')),patch.object(bridge,'_read_source_manifest',side_effect=AssertionError('IO')):
                with self.assertRaises(bridge.StaticPreflightBlocked):bridge.select_static_authorization(self.raw,context=ctx,source_root=self.root,now=fixtures.NOW)
    def test_context_fields_and_builtin_types_are_closed(self):
        for ctx in (dict(self.ctx,approved=True),dict(self.ctx,run_id=123),dict(self.ctx,actor=True),{k:v for k,v in self.ctx.items() if k!='runner_name'}):self.blocked(ctx=ctx,code='STATIC_CONTEXT_REJECTED')
    def test_context_key_alias_is_rejected_without_caller_comparison(self):
        touched=[]
        class Key(str):
            __hash__=str.__hash__
            def __eq__(self,other):touched.append('equality');return str.__eq__(self,other)
        ctx={k:v for k,v in self.ctx.items() if k!='event'};ctx[Key('event')]='workflow_dispatch'
        touched.clear()
        self.blocked(ctx=ctx,code='STATIC_CONTEXT_REJECTED')
        self.assertEqual(touched,[])
    def test_snapshot_key_and_identity_aliases_deny_without_caller_comparison(self):
        touched=[]
        class Key(str):
            __hash__=str.__hash__
            def __eq__(self,other):touched.append('equality');return str.__eq__(self,other)
        for position in ('root_key','pin_key','head','tree','file_name'):
            snapshot=copy.deepcopy(self.snapshot)
            if position=='root_key':snapshot[Key('head')]=snapshot.pop('head')
            elif position=='pin_key':
                pin=next(iter(snapshot['files'].values()));pin[Key('bytes')]=pin.pop('bytes')
            elif position=='file_name':
                name=next(iter(snapshot['files']));snapshot['files']={Key(name):snapshot['files'][name]}
            else:snapshot[position]=Key(snapshot[position])
            touched.clear()
            with self.subTest(position=position):
                with self.assertRaises(ValueError):bridge._snapshot(snapshot,self.auth['source'],self.manifest)
                self.assertEqual(touched,[])
    def test_attempt_run_and_static_job_identity_deny_aliases(self):
        for key,value in (('attempt','2'),('attempt','01'),('run_id','0'),('run_id','01'),('run_id','9'*40),('job_name','collector-c3'),('repository','other/repo'),('runner_name','bad\nname')):self.blocked(ctx=dict(self.ctx,**{key:value}),code='STATIC_CONTEXT_REJECTED')
    def test_source_sha_and_hash_commit_shapes_deny(self):
        for key,value in (('source_sha','f'*40),('sha','A'*40),('authorization_commit','e'*39),('authorization_sha256','F'*64)):self.blocked(ctx=dict(self.ctx,**{key:value}))
    def test_authorization_hash_mismatch_denies_before_acquisition(self):
        with patch.object(bridge,'_primary_source',side_effect=AssertionError('IO')):
            with self.assertRaises(bridge.StaticPreflightBlocked) as caught:bridge.select_static_authorization(self.raw,context=dict(self.ctx,authorization_sha256='f'*64),source_root=self.root,now=fixtures.NOW)
        self.assertEqual(caught.exception.code,'STATIC_AUTHORIZATION_REJECTED')
    def test_duplicate_noncanonical_and_nonfinite_actual_codec_denials(self):
        for raw in (b'{"schema":"x","schema":"y"}\n',self.raw.replace(b'\n',b'\r\n'),self.raw[:-1],b'{"x":NaN}\n'):
            self.blocked(raw=raw,ctx=dict(self.ctx,authorization_sha256=hashlib.sha256(raw).hexdigest()),code='STATIC_AUTHORIZATION_REJECTED')
    def test_cross_v1_record_is_not_v2_authorization(self):
        raw=codec.encode(dict(status='APPROVED',SourceKind='explicit_operator_record',repository=codec.REPOSITORY,source_sha='a'*40,attempt=1))
        self.blocked(raw=raw,ctx=dict(self.ctx,authorization_sha256=hashlib.sha256(raw).hexdigest()),code='STATIC_AUTHORIZATION_REJECTED')
    def test_numeric_bounds_and_expiry_are_checked_by_actual_codec(self):
        for key,value in (('workers',True),('workers',1.0),('frames',5),('duration_seconds','10')):
            auth=copy.deepcopy(self.auth);auth['bounds'][key]=value;raw=codec.encode(auth)
            self.blocked(raw=raw,ctx=dict(self.ctx,authorization_sha256=hashlib.sha256(raw).hexdigest()),code='STATIC_AUTHORIZATION_REJECTED')
        self.blocked(now=fixtures.NOW+7200,code='STATIC_AUTHORIZATION_REJECTED')
    def test_now_rejects_bool_nonfinite_and_callable_aliases(self):
        for now in (True,float('nan'),float('inf'),lambda:fixtures.NOW):self.blocked(now=now,code='STATIC_AUTHORIZATION_REJECTED')
    def test_actual_primary_head_and_tree_must_match_static_scope(self):
        for key in ('head','tree'):
            snapshot=copy.deepcopy(self.snapshot);snapshot[key]='f'*40;self.blocked(snapshot=snapshot,code='STATIC_SOURCE_VERIFICATION_FAILED')
    def test_source_manifest_raw_hash_and_primary_pin_must_match(self):
        self.path.write_bytes(b'changed owned DATA\n');self.blocked(code='STATIC_SOURCE_VERIFICATION_FAILED')
        self.path.write_bytes(self.manifest)
        for key,value in (('sha256','f'*64),('oid','f'*40),('bytes',True)):
            snapshot=copy.deepcopy(self.snapshot);snapshot['files']['integration/collector/v1/source-inputs.json'][key]=value
            self.blocked(snapshot=snapshot,code='STATIC_SOURCE_VERIFICATION_FAILED')
    def test_snapshot_missing_manifest_or_unknown_pin_fields_deny(self):
        snapshot=copy.deepcopy(self.snapshot);snapshot['files']={};self.blocked(snapshot=snapshot)
        snapshot=copy.deepcopy(self.snapshot);snapshot['files']['integration/collector/v1/source-inputs.json']['trusted']=True;self.blocked(snapshot=snapshot)
    def test_case_colliding_primary_directories_are_not_accepted(self):
        snapshot=copy.deepcopy(self.snapshot);pin=copy.deepcopy(next(iter(snapshot['files'].values())))
        snapshot['files'].update({'A/x':pin,'a/y':copy.deepcopy(pin)});snapshot['directories']=sorted(['A','a',*snapshot['directories']])
        self.blocked(snapshot=snapshot,code='STATIC_SOURCE_VERIFICATION_FAILED')
    def test_source_manifest_changed_during_acquisition_denies(self):
        def changed(*args):self.path.write_bytes(b'replaced owned DATA\n');return copy.deepcopy(self.snapshot)
        with patch.object(bridge,'_primary_source',side_effect=changed),self.assertRaises(bridge.StaticPreflightBlocked) as caught:bridge.select_static_authorization(self.raw,context=self.ctx,source_root=self.root,now=fixtures.NOW)
        self.assertEqual(caught.exception.code,'STATIC_SOURCE_VERIFICATION_FAILED')
    def test_missing_or_oversized_source_manifest_denies(self):
        self.path.unlink();self.blocked(code='STATIC_SOURCE_VERIFICATION_FAILED');self.path.write_bytes(b'x'*262145);self.blocked(code='STATIC_SOURCE_VERIFICATION_FAILED')
    def test_reparse_ancestor_denied_before_open_or_primary(self):
        original=Path.lstat
        def facts(path):
            if path==self.root:return types.SimpleNamespace(st_mode=stat.S_IFDIR,st_file_attributes=1024,st_reparse_tag=0)
            return original(path)
        with patch.object(Path,'lstat',facts),patch.object(Path,'open',side_effect=AssertionError('OPEN')),patch.object(bridge,'_primary_source',side_effect=AssertionError('GIT')):
            with self.assertRaises(bridge.StaticPreflightBlocked):bridge.select_static_authorization(self.raw,context=self.ctx,source_root=self.root,now=fixtures.NOW)
    def test_actual_owned_hardlink_source_manifest_is_not_adopted(self):
        os.link(self.path,self.root/'owned-alias.json');self.assertEqual(self.path.stat().st_nlink,2);self.blocked(code='STATIC_SOURCE_VERIFICATION_FAILED')
    def test_method_presence_and_caller_true_cannot_enable_selection(self):
        fake=types.ModuleType('unified_system.installation_service');fake.run_collector_raw_qualification=lambda *args,**kwargs:self.fail('NATIVE_CALL')
        with patch.dict(sys.modules,{'unified_system.installation_service':fake}):self.assertIs(self.call()[0]['selected'],False)
        with self.assertRaises(TypeError):bridge.select_static_authorization(self.raw,context=self.ctx,source_root=self.root,now=fixtures.NOW,qualified=True)
    def test_private_source_exception_has_only_closed_public_code(self):
        with patch.object(bridge,'_primary_source',side_effect=RuntimeError('Bearer-secret private/path')):
            with self.assertRaises(bridge.StaticPreflightBlocked) as caught:bridge.select_static_authorization(self.raw,context=self.ctx,source_root=self.root,now=fixtures.NOW)
        self.assertEqual(str(caught.exception),'STATIC_SOURCE_VERIFICATION_FAILED');self.assertNotIn('secret',str(caught.exception))
    def test_source_root_aliases_and_nonpath_types_deny(self):
        for root in ('relative',self.root/'..'/self.root.name,True):
            with patch.object(bridge,'_primary_source',side_effect=AssertionError('GIT')),self.assertRaises(bridge.StaticPreflightBlocked):bridge.select_static_authorization(self.raw,context=self.ctx,source_root=root,now=fixtures.NOW)



class EnvironmentConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.auth=fixtures.authorization();self.raw=codec.encode(self.auth)
        self.ctx=dict(event='workflow_dispatch',repository=codec.REPOSITORY,sha='a'*40,source_sha='a'*40,attempt='1',run_id='123',actor='actor',authorization_commit='e'*40,authorization_sha256=hashlib.sha256(self.raw).hexdigest(),job_name='collector-preflight',runner_name='GitHub Actions 1')
        self.env=dict(id=42,name='collector-c3-operational-v2',protection_rules=[dict(id=9,type='required_reviewers',prevent_self_review=False,reviewers=[dict(type='User',reviewer=dict(id=7,login='operator',type='User'))])],can_admins_bypass=True,metadata='permitted API metadata')
    def call(self,raw=None,ctx=None):
        from scripts import ci_service_operational_admission as legacy
        body=codec.encode(self.env) if raw is None else raw
        with patch.dict(os.environ,{'GITHUB_TOKEN':'inert-unit-token'},clear=False),patch.object(legacy,'get',return_value=body) as get:
            value=bridge.observe_protected_environment_config(self.raw,context=self.ctx if ctx is None else ctx,now=fixtures.NOW)
        return value,get
    def test_existing_config_is_observation_only_and_fixed_get(self):
        value,get=self.call();self.assertEqual(value['status'],'CONFIG_OBSERVED_NOT_ADMITTED');self.assertIs(value['selected'],False);self.assertIs(value['execution_authority'],False)
        self.assertIn('ACTUAL_PROTECTED_REVIEW_NOT_ACQUIRED',value['missing_gates']);self.assertEqual(value['environment']['required_reviewer'],dict(id=7,login='operator'))
        get.assert_called_once_with('https://api.github.com/repos/'+codec.REPOSITORY+'/environments/collector-c3-operational-v2','inert-unit-token')
        self.assertNotIn('inert-unit-token',json.dumps(value));self.assertEqual(value['response_body'],dict(sha256=hashlib.sha256(codec.encode(self.env)).hexdigest(),bytes=len(codec.encode(self.env))))
    def test_missing_environment_rule_or_team_never_admits(self):
        for field,value in [('id',0),('id',True),('name','missing'),('protection_rules',[])]:
            env=copy.deepcopy(self.env);env[field]=value
            with self.subTest(field=field),self.assertRaises(bridge.StaticPreflightBlocked):self.call(codec.encode(env))
        self.env['protection_rules'][0]['reviewers'][0]['type']='Team'
        with self.assertRaises(bridge.StaticPreflightBlocked):self.call()
    def test_duplicate_rule_unknown_meaning_and_bad_boolean_deny(self):
        rule=self.env['protection_rules'][0]
        for rules in ([rule,rule],[dict(id=10,type='unknown')],[dict(rule,prevent_self_review=0)]):
            env=dict(self.env,protection_rules=rules)
            with self.assertRaises(bridge.StaticPreflightBlocked):self.call(codec.encode(env))
        self.env['can_admins_bypass']=1
        with self.assertRaises(bridge.StaticPreflightBlocked):self.call()
    def test_reviewer_ids_logins_and_types_are_exact_unique(self):
        rule=self.env['protection_rules'][0]
        for user in (dict(id=True,login='operator',type='User'),dict(id=0,login='operator',type='User'),dict(id=7,login=7,type='User'),dict(id=7,login='operator',type='Bot')):
            rule['reviewers']=[dict(type='User',reviewer=user)]
            with self.assertRaises(bridge.StaticPreflightBlocked):self.call()
        for other in (dict(id=7,login='different',type='User'),dict(id=8,login='OPERATOR',type='User')):
            rule['reviewers']=[dict(type='User',reviewer=dict(id=7,login='operator',type='User')),dict(type='User',reviewer=other)]
            with self.assertRaises(bridge.StaticPreflightBlocked):self.call()
    def test_existing_self_review_policy_is_respected_without_second_person_requirement(self):
        self.ctx['actor']='operator';self.call()
        self.env['protection_rules'][0]['prevent_self_review']=True
        with self.assertRaises(bridge.StaticPreflightBlocked):self.call()
    def test_raw_subclass_duplicates_oversize_and_malformed_deny(self):
        class Bytes(bytes):pass
        for raw in (Bytes(codec.encode(self.env)),b'{"id":1,"id":2}',b' '*65537,b'not json'):
            with self.assertRaises(bridge.StaticPreflightBlocked):self.call(raw)
    def test_context_and_authorization_deny_before_get(self):
        from scripts import ci_service_operational_admission as legacy
        with patch.object(legacy,'get',side_effect=AssertionError('must not acquire')) as get:
            for ctx in (dict(self.ctx,event='push'),dict(self.ctx,authorization_sha256='f'*64)):
                with self.assertRaises(bridge.StaticPreflightBlocked):bridge.observe_protected_environment_config(self.raw,context=ctx,now=fixtures.NOW)
            self.assertEqual(get.call_count,0)
    def test_token_required_closed_and_never_leaks_errors(self):
        from scripts import ci_service_operational_admission as legacy
        for token in ('','a\nb','x'*4097):
            with patch.dict(os.environ,{'GITHUB_TOKEN':token}),patch.object(legacy,'get') as get:
                with self.assertRaises(bridge.StaticPreflightBlocked) as caught:bridge.observe_protected_environment_config(self.raw,context=self.ctx,now=fixtures.NOW)
                self.assertEqual(get.call_count,0);self.assertNotIn(token if token else 'secret',str(caught.exception))
        with patch.dict(os.environ,{'GITHUB_TOKEN':'secret'}),patch.object(legacy,'get',side_effect=RuntimeError('secret signed URL')):
            with self.assertRaises(bridge.StaticPreflightBlocked) as caught:bridge.observe_protected_environment_config(self.raw,context=self.ctx,now=fixtures.NOW)
            self.assertEqual(str(caught.exception),'CONFIG_ACQUISITION_REJECTED')
    def test_no_public_token_opener_facts_or_selection_override(self):
        for key in ('token','opener','facts','provider','selected'):
            with self.assertRaises(TypeError):bridge.observe_protected_environment_config(self.raw,context=self.ctx,**{key:True})

if __name__=='__main__':unittest.main()
