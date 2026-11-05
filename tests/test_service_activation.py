"""Protected owner activation artifacts: model boundaries, never readiness proof."""
import copy,hashlib,json,stat,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tests import test_runtime_profile as profile_fixtures
from unified_system import lab_release
from unified_system.service_activation import publish_activation,revoke_activation
from unified_system.service_bootstrap import read_protected_activation,ActivationBlocked

SID='S-1-5-80-1-2-3-4-5'
class FakeKernel:
 def __init__(self):self.host='LABHOST';self.sid=SID;self.sealed=set();self.checks=0;self.user='S-1-5-19'
 def identity(self):return {'computer_name':self.host,'user_sid':self.user,'service_sid':self.sid}
 def require_readonly(self,path,sid,anchor):
  self.checks+=1
  if str(path) not in self.sealed or sid!=SID:raise ActivationBlocked('ACTIVATION_ACL_REJECTED')
  return True
class FakeBoundary:
 def __init__(self,kernel):self.kernel=kernel;self.calls=[]
 def computer_name(self):return self.kernel.host
 def prepare(self,plan):
  self.calls.append('prepare');root=Path(plan['service_plan']['root'])/'activation'
  if root.exists():
   if (root/'namespace.json').read_bytes()!=lab_release.canonical({'service_plan_sha256':plan['service_plan']['plan_sha256']}):raise ActivationBlocked('ACTIVATION_NAMESPACE_REJECTED')
  else:root.mkdir();(root/'namespace.json').write_bytes(lab_release.canonical({'service_plan_sha256':plan['service_plan']['plan_sha256']}))
  (root/'revisions').mkdir(exist_ok=True);revision=root/'revisions'/plan['revision_id'];revision.mkdir();(revision/'credentials').mkdir()
 def seal(self,plan):
  self.calls.append('seal');root=Path(plan['service_plan']['root']);self.kernel.sealed.add(str(root));self.kernel.sealed.update(str(p) for p in (root/'activation').rglob('*'));self.kernel.sealed.add(str(root/'activation'))
 def publish(self,plan,pointer):
  self.calls.append('publish');path=Path(plan['service_plan']['root'])/'activation/current.json';path.write_bytes(pointer);self.kernel.sealed.add(str(path))
class FakeResource:
 def __init__(self,plan):self.plan=plan
 def recorded(self):return copy.deepcopy({'plan':self.plan,'receipt_sha256':'d'*64,'proof':{'code_acl_sha256':'e'*64,'state_acl_sha256':'f'*64}})
 def inspect(self,guard):
  if guard('INSPECT',self.plan['plan_sha256']) is not True:raise ValueError('DENIED')
  return {'status':'STOPPED_RESOURCE_RECORDED'}

class ActivationTests(unittest.TestCase):
 def test_research_configuration_is_protected_but_never_self_authorizing(self):
  from tests.test_data_first_policy import PolicyTests
  case=PolicyTests();case.setUp();policy=case.value
  policy['source_commit']=self.fixture.manifest['sources']['strattester']['commit']
  lab_release.stage_capsule(self.fixture.base,self.resource.plan['code'],self.fixture.pin)
  self.profile['data_first']=policy
  with self.assertRaises(ActivationBlocked):self.publish(owner_phase=None)
  self.assertFalse((self.root/'activation').exists())
  original=policy['source_commit'];policy['source_commit']='f'*40
  with self.assertRaises(ActivationBlocked):self.publish()
  self.assertFalse((self.root/'activation').exists())
  policy['source_commit']=original;self.publish()
  grant=read_protected_activation(self.root,kernel=self.kernel)
  self.assertEqual(grant.profile['data_first'],policy)
  self.assertEqual(grant.profile['activation'],'BLOCKED')
 def setUp(self):
  self.fixture=profile_fixtures.RuntimeProfileTests('test_all_roles_are_pure_derived_data_never_execution_admission');self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
  self.root=self.fixture.root/'service';self.root.mkdir();self.kernel=FakeKernel();self.boundary=FakeBoundary(self.kernel);self.revision='revision-1'
  auth={'schema':'unified.lab.grid-auth.v3','node_id':'PC1','role':'WORKER','release_id':'lab-1','source_commit':'a'*40,'grid_shared_token':None,'node_credential':'C'*64,'postgres_password':None}
  self.auth=self.fixture.root/'source-auth.json';self.auth.write_bytes(lab_release.canonical(auth));auth_hash=hashlib.sha256(self.auth.read_bytes()).hexdigest()
  target=self.fixture.target();target.update(node_id='PC1',credential_root=str(self.root/'activation/revisions'/self.revision/'credentials'),auth_binding={'path':str(self.root/'activation/revisions'/self.revision/'credentials/auth.json'),'sha256':auth_hash})
  self.profile=self.fixture.derive(target)
  plan={'schema':'unified.owned-stopped-service.v1','plan_sha256':'b'*64,'root':str(self.root),'code':target['code_root'],'state':target['state_root'],'installation_id':'install-1','node_id':'PC1','computer_name':'LABHOST','role':'WORKER','service_name':'UnifiedLab_fixture','service_sid':SID,'manifest_sha256':self.fixture.pin}
  self.resource=FakeResource(plan);self.refs={'phase_id':'phase-1','source_evidence_sha256':'1'*64,'capacity_evidence_sha256':'2'*64,'database_evidence_sha256':None};self.grants=[]
 def owner(self,action,pin):self.grants.append((action,pin));return True
 def publish(self,**changes):
  args=dict(revision_id=self.revision,qualification_refs=self.refs,owner_phase=self.owner,qualify=lambda p,r:True,boundary=self.boundary)
  args.update(changes);return publish_activation(self.resource,self.profile,self.auth,**args)
 def test_roundtrip_protected_artifacts_are_not_runtime_readiness(self):
  receipt=self.publish();self.assertEqual(receipt['status'],'ACTIVATION_REVISION_PUBLISHED');self.assertEqual(receipt['readiness'],'NOT_PROVEN')
  grant=read_protected_activation(self.root,kernel=self.kernel);self.assertIs(grant.require_current(),True)
  self.assertEqual(grant.profile,self.profile);self.assertEqual(grant.manifest_sha256,self.fixture.pin);self.assertEqual(grant.auth_path.read_bytes(),self.auth.read_bytes())
  exposed=grant.profile;exposed['runtime_config']['node_id']='forged';self.assertEqual(grant.profile['runtime_config']['node_id'],'PC1')
  self.assertTrue(all(pin==receipt['activation_plan_sha256'] for _,pin in self.grants))
 def test_no_owner_or_external_qualification_means_no_effects(self):
  for changes in ({'owner_phase':None},{'qualify':None},{'owner_phase':lambda a,p:False},{'qualify':lambda p,r:False}):
   with self.subTest(changes=changes),self.assertRaises(ActivationBlocked):self.publish(**changes)
  self.assertEqual(self.boundary.calls,[]);self.assertFalse((self.root/'activation').exists())
 def test_missing_acl_wrong_host_token_or_extra_json_flag_never_authorizes(self):
  self.publish()
  for mutate in (lambda:setattr(self.kernel,'host','OTHER'),lambda:setattr(self.kernel,'sid','S-1-5-80-9-9-9-9-9'),lambda:self.kernel.sealed.clear()):
   mutate()
   with self.assertRaises(ActivationBlocked):read_protected_activation(self.root,kernel=self.kernel)
   self.kernel.host='LABHOST';self.kernel.sid=SID
  self.boundary.seal({'service_plan':self.resource.plan});self.kernel.sealed.add(str(self.root/'activation/current.json'))
  pointer=self.root/'activation/current.json';obj=json.loads(pointer.read_bytes());obj['approved']=True;pointer.write_bytes(lab_release.canonical(obj))
  with self.assertRaises(ActivationBlocked):read_protected_activation(self.root,kernel=self.kernel)
 def test_revocation_invalidates_existing_grant_without_deleting_history(self):
  self.publish();grant=read_protected_activation(self.root,kernel=self.kernel)
  revoke_activation(self.resource,owner_phase=self.owner,boundary=self.boundary)
  with self.assertRaises(ActivationBlocked):grant.require_current()
  self.assertTrue(grant.auth_path.exists());self.assertTrue((self.root/'activation/revisions'/self.revision/'profile.json').exists())
 def test_tampered_immutable_profile_or_auth_is_never_admitted(self):
  self.publish();path=self.root/'activation/revisions'/self.revision/'profile.json';path.write_bytes(b'{}')
  with self.assertRaises(ActivationBlocked):read_protected_activation(self.root,kernel=self.kernel)
 def test_cheap_continuation_does_not_hash_capsule_or_construct_runtime(self):
  self.publish();grant=read_protected_activation(self.root,kernel=self.kernel)
  with patch('unified_system.lab_release.verify_capsule',side_effect=AssertionError('NO FULL HASH ON TICK')),patch('unified_system.runtime_cli.make_runtime',side_effect=AssertionError('NO RUNTIME')):self.assertIs(grant.require_current(),True)
 def test_default_denied_revoke_makes_no_new_lock_or_pointer_write(self):
  self.publish();lock=self.root/'activation/publication.lock';lock.unlink();pointer=self.root/'activation/current.json';before=pointer.read_bytes()
  with self.assertRaises(ActivationBlocked):revoke_activation(self.resource,boundary=self.boundary)
  self.assertFalse(lock.exists());self.assertEqual(pointer.read_bytes(),before)
 def test_nonservice_identity_and_mutating_callback_do_not_rebind_artifacts(self):
  def qualifier(plan,refs):plan['service_plan']['root']=str(self.fixture.root/'outside');refs['phase_id']='mutated';return True
  self.publish(qualify=qualifier);self.assertFalse((self.fixture.root/'outside').exists())
  self.kernel.user='S-1-5-18'
  with self.assertRaises(ActivationBlocked):read_protected_activation(self.root,kernel=self.kernel)
 @unittest.skipUnless(__import__('os').name=='nt','Read-only actual current-token rejection')
 def test_actual_nonservice_token_cannot_admit_user_json_flags(self):
  from unified_system.service_bootstrap import WindowsActivationKernel
  kernel=WindowsActivationKernel()
  with self.assertRaises(ActivationBlocked) as rejected:kernel.identity()
  self.assertEqual(rejected.exception.code,'ACTIVATION_SERVICE_TOKEN_REQUIRED')

 def test_readonly_acl_policy_rejects_service_write_owner_or_foreign_ace(self):
  from unified_system.service_bootstrap import WindowsActivationKernel
  kernel=object.__new__(WindowsActivationKernel);anchor=self.root/'activation';anchor.mkdir();target=anchor/'data.json';target.write_bytes(b'{}')
  def security(path):
   inherited=path not in (self.root,anchor)
   return 'S-1-5-32-544',not inherited,[('S-1-5-18',0x1f01ff,16 if inherited else 3),('S-1-5-32-544',0x1f01ff,16 if inherited else 3),(SID,0x1200a9,16 if inherited else 3)]
  with patch.object(kernel,'_security',side_effect=security):self.assertIs(kernel.require_readonly(target,SID,anchor),True)
  for change in ('owner','service_write','foreign','inheritance'):
   def bad(path):
    owner,protected,rows=security(path)
    if change=='owner':owner=SID
    elif change=='service_write':rows[2]=(SID,0x1f01ff,rows[2][2])
    elif change=='foreign':rows[2]=('S-1-5-19',0x1200a9,rows[2][2])
    else:rows[2]=(SID,0x1200a9,rows[2][2]|64)
    return owner,protected,rows
   with self.subTest(change=change),patch.object(kernel,'_security',side_effect=bad),self.assertRaises(ActivationBlocked):kernel.require_readonly(target,SID,anchor)

 def test_error_codes_are_closed_and_never_echo_caller_text(self):
  self.assertEqual(str(ActivationBlocked('PRIVATE_SECRET_TOKEN')), 'ACTIVATION_REJECTED')

 def test_bootstrap_import_is_stdlib_only_and_inert_in_isolated_child(self):
  import subprocess,sys
  from unified_system import service_bootstrap
  source=str(Path(service_bootstrap.__file__).resolve())
  script="import runpy,sys;runpy.run_path(sys.argv[1]);assert not any(x.startswith(('unified_system','integration')) for x in sys.modules)"
  result=subprocess.run([sys.executable,'-I','-S','-B','-c',script,source],cwd=self.fixture.root,capture_output=True,timeout=10)
  self.assertEqual(result.returncode,0);self.assertEqual(result.stdout,b'');self.assertEqual(result.stderr,b'')
  self.assertFalse((self.root/'activation').exists())
 def test_bounded_regular_auth_source_rejects_before_revision_creation(self):
  self.auth.write_bytes(b'x'*8193)
  with self.assertRaises(ActivationBlocked):self.publish()
  self.assertEqual(self.boundary.calls,[]);self.assertFalse((self.root/'activation').exists())

 def test_control_and_single_pc_transit_credentials_use_role_context(self):
  for role in ('CONTROL','SINGLE_PC'):
   with self.subTest(role=role):
    self.revision='revision-'+role;self.resource.plan['role']=role;self.refs['database_evidence_sha256']='3'*64
    auth=dict(schema='unified.lab.grid-auth.v3',node_id='PC1',role='CONTROL',release_id='lab-1',source_commit='a'*40,grid_shared_token='c'*64,node_credential=None,postgres_password='d'*64)
    self.auth.write_bytes(lab_release.canonical(auth));target=self.fixture.target(role)
    target.update(node_id='PC1',credential_root=str(self.root/'activation/revisions'/self.revision/'credentials'),auth_binding={'path':str(self.root/'activation/revisions'/self.revision/'credentials/auth.json'),'sha256':hashlib.sha256(self.auth.read_bytes()).hexdigest()})
    self.profile=self.fixture.derive(target);self.assertEqual(self.publish()['readiness'],'NOT_PROVEN')
    self.assertEqual(read_protected_activation(self.root,kernel=self.kernel).profile['offline_context']['role'],role)
 def test_worker_transit_auth_never_admits_database_secrets(self):
  auth=json.loads(self.auth.read_bytes());auth['postgres_password']='d'*64;self.auth.write_bytes(lab_release.canonical(auth))
  self.profile['runtime_config']['programs']['grid']['env']['GRID_LAB_AUTH_SHA256']=hashlib.sha256(self.auth.read_bytes()).hexdigest()
  self.profile['derivation_receipt']['profile_sha256']=hashlib.sha256(lab_release.canonical(self.profile['runtime_config'])).hexdigest()
  with self.assertRaises(ActivationBlocked):self.publish()
  self.assertEqual(self.boundary.calls,[])
 def test_callback_directory_replacement_cannot_redirect_artifact_writes(self):
  foreign=self.fixture.root/'foreign';foreign.mkdir();(foreign/'keep').write_text('retained')
  def owner(action,pin):
   if action=='WRITE_ACTIVATION_ARTIFACT':
    revision=self.root/'activation/revisions'/self.revision
    revision.rename(revision.with_name('retained-original'));revision.mkdir()
    (revision/'credentials').mkdir();(revision/'foreign-marker').write_text('preserved')
   return True
  with self.assertRaises(ActivationBlocked):self.publish(owner_phase=owner)
  revision=self.root/'activation/revisions'/self.revision
  self.assertFalse((revision/'profile.json').exists());self.assertEqual((revision/'foreign-marker').read_text(),'preserved')
  self.assertEqual((foreign/'keep').read_text(),'retained')

 @unittest.skipUnless(__import__('os').name=='nt','Actual own-temp Windows junction')
 def test_callback_junction_replacement_cannot_follow_foreign_directory(self):
  import os,subprocess
  from unified_system.installation_service import _system_directory
  foreign=self.fixture.root/'foreign-junction-target';foreign.mkdir();(foreign/'keep').write_text('retained')
  junction=self.root/'activation/revisions'/self.revision
  def owner(action,pin):
   if action=='WRITE_ACTIVATION_ARTIFACT':
    junction.rename(junction.with_name('retained-original'))
    result=subprocess.run([str(_system_directory()/'cmd.exe'),'/d','/c','mklink','/J',str(junction),str(foreign)],capture_output=True,timeout=10,creationflags=subprocess.CREATE_NO_WINDOW)
    self.assertEqual(result.returncode,0)
    if getattr(self,'dangling_junction',False):foreign.rename(foreign.with_name('retained-junction-target'))
   return True
  try:
   with self.assertRaises(ActivationBlocked):self.publish(owner_phase=owner)
   target=foreign.with_name('retained-junction-target') if getattr(self,'dangling_junction',False) else foreign
   self.assertEqual((target/'keep').read_text(),'retained');self.assertFalse((target/'profile.json').exists())
  finally:
   try:info=junction.lstat()
   except FileNotFoundError:pass
   else:
    if (getattr(info,'st_file_attributes',0)&stat.FILE_ATTRIBUTE_REPARSE_POINT
        and getattr(info,'st_reparse_tag',None)==stat.IO_REPARSE_TAG_MOUNT_POINT):os.rmdir(junction)

 @unittest.skipUnless(__import__('os').name=='nt','Actual own-temp dangling Windows junction')
 def test_callback_dangling_junction_is_rejected_before_writes(self):
  self.dangling_junction=True;self.test_callback_junction_replacement_cannot_follow_foreign_directory()

 def test_reader_checks_profile_bindings_even_with_consistent_artifact_hashes(self):
  self.publish();revision=self.root/'activation/revisions'/self.revision
  descriptor=json.loads((revision/'descriptor.json').read_bytes());pointer=json.loads((self.root/'activation/current.json').read_bytes())
  for field in ('role','node_id','computer_name','release_sha256','auth_path','auth_hash'):
   profile=copy.deepcopy(self.profile)
   if field in ('role','node_id','computer_name'):profile['offline_context'][field]='OTHER'
   elif field=='release_sha256':profile['runtime_config'][field]='0'*64
   elif field=='auth_path':profile['runtime_config']['programs']['grid']['env']['GRID_LAB_AUTH_PATH']=str(self.auth)
   else:profile['runtime_config']['programs']['grid']['env']['GRID_LAB_AUTH_SHA256']='0'*64
   raw=lab_release.canonical(profile);(revision/'profile.json').write_bytes(raw);descriptor['profile_sha256']=hashlib.sha256(raw).hexdigest()
   raw=lab_release.canonical(descriptor);(revision/'descriptor.json').write_bytes(raw);pointer['descriptor_sha256']=hashlib.sha256(raw).hexdigest();(self.root/'activation/current.json').write_bytes(lab_release.canonical(pointer))
   with self.subTest(field=field),self.assertRaises(ActivationBlocked):read_protected_activation(self.root,kernel=self.kernel)
 def test_publication_lock_replacement_during_callback_prevents_commit(self):
  def owner(action,pin):
   if action=='COMMIT_ACTIVATION_POINTER':
    lock=self.root/'activation/publication.lock'
    try:lock.rename(lock.with_name('retained-lock'))
    except PermissionError:raise ActivationBlocked('ACTIVATION_CONCURRENT_UPDATE')
    lock.write_bytes(b'foreign')
   return True
  with self.assertRaises(ActivationBlocked):self.publish(owner_phase=owner)
  self.assertFalse((self.root/'activation/current.json').exists());self.assertIn((self.root/'activation/publication.lock').read_bytes(),(b'foreign',b'0'))

 def test_namespace_reuse_and_foreign_roots_are_never_adopted(self):
  self.publish()
  with self.assertRaises(ActivationBlocked):self.publish()
  self.assertTrue((self.root/'activation/revisions'/self.revision/'descriptor.json').exists())

if __name__=='__main__':unittest.main()
