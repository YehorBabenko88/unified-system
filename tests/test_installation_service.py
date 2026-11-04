"""Stopped service orchestration against isolated fake Windows boundaries only."""
import copy,hashlib,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tests.test_lab_release import fixture
from unified_system import lab_release
from unified_system.installation_service import ServiceResource,service_plan,parse_service_sid,WindowsServiceBoundary

class FakeWindows:
 def __init__(self):self.calls=[];self.service=None;self.fault=None;self.acl='a'*64;self.host='TEST-PC'
 def computer_name(self):return self.host
 def native_tools(self):return {'sc':{'path':str(Path(tempfile.gettempdir()).resolve()/'fixture-sc.exe'),'sha256':'a'*64},'powershell':{'path':str(Path(tempfile.gettempdir()).resolve()/'fixture-powershell.exe'),'sha256':'b'*64}}
 def sid(self,name):return 'S-1-5-80-1-2-3-4-5'
 def call(self,action,plan,guard):
  if guard is None or guard(action,plan['plan_sha256']) is not True:raise ValueError('approval')
  self.calls.append(action)
  if self.fault==action:raise OSError('INJECTED_PRIVATE_FAULT')
  base=Path(plan['root'])
  if action=='BEGIN':
   if self.service is not None or base.exists():raise ValueError('foreign')
   base.mkdir();(base/'ownership').mkdir();(base/'state').mkdir()
   return {'root_device':base.stat().st_dev,'root_inode':base.stat().st_ino}
  if action=='SEAL':return {'code_acl_sha256':self.acl,'state_acl_sha256':self.acl,'acl_policy':'EXACT_SERVICE_SID_V1'}
  if action=='REGISTER':
   if self.service is not None:raise ValueError('foreign')
   self.service=dict(service_name=plan['service_name'],service_sid=plan['service_sid'],account='NT AUTHORITY\\LocalService',start_type=3,sid_type=1,state=1,binary_path='"'+plan['nssm']+'"',application=plan['python'],parameters=plan['parameters'],directory=plan['code'],app_exit='Exit',marker=plan['plan_sha256'],code_acl_sha256=self.acl,state_acl_sha256=self.acl,acl_policy='EXACT_SERVICE_SID_V1')
  if action in ('REGISTER','INSPECT'):
   if self.service is None:raise ValueError('missing')
   return copy.deepcopy(self.service)
  raise AssertionError(action)

class ServiceResourceTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve()
  self.source=self.root/'capsule';self.source.mkdir();manifest=fixture(self.source)
  for name,raw in {'runtime/nssm/nssm.exe':b'INERT_WRAPPER','runtime/python/python.exe':b'INERT_PYTHON','sources/unified-system/unified_system/owned_python.py':b'INERT_BOOTSTRAP'}.items():
   path=self.source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
  entry=self.source/'sources/unified-system/unified_system/service_entry.py';entry.write_bytes((Path(__file__).resolve().parents[1]/'unified_system/service_entry.py').read_bytes().replace(b'\r\n',b'\n')) # LF Git-blob fixture, not production normalization
  from tests.test_lab_capsule_builder import builder
  manifest['files'],manifest['directories']=builder.inventory(self.source)
  raw=lab_release.canonical(manifest);(self.source/'lab-release.json').write_bytes(raw);self.pin=hashlib.sha256(raw).hexdigest()
  self.backend=FakeWindows();self.grants=[]
  self.policy=patch('unified_system.installation_service.NSSM_PIN',hashlib.sha256(b'INERT_WRAPPER').hexdigest());self.policy.start();self.addCleanup(self.policy.stop)
 def guard(self,action,pin):self.grants.append((action,pin));return True
 def plan(self):
  return service_plan(self.source,self.pin,self.root/'service','install','node','CONTROL',self.backend)
 def test_blocked_entry_never_imports_runtime_or_honors_caller_activation_claims(self):
  import subprocess,sys
  entry=Path(__file__).resolve().parents[1]/'unified_system/service_entry.py'
  poison=self.root/'poison';poison.mkdir();marker=self.root/'unexpected-import'
  (poison/'sitecustomize.py').write_text('from pathlib import Path;Path('+repr(str(marker))+').touch()')
  for arguments in ([],['--execute'],['--activation-ticket','owner-approved']):
   environment=dict(os.environ,PYTHONPATH=str(poison),UNIFIED_ACTIVATED='true')
   result=subprocess.run([sys.executable,'-I','-S','-B',str(entry),*arguments],env=environment,capture_output=True,timeout=10)
   self.assertEqual(result.returncode,78);self.assertEqual(result.stdout.replace(b'\r\n',b'\n'),b'BLOCKED_ACTIVATION_NOT_IMPLEMENTED\n');self.assertEqual(result.stderr,b'')
  self.assertFalse(marker.exists())
 def test_registered_command_uses_only_reviewed_blocked_entry(self):
  plan=self.plan();self.assertNotIn('--execute',plan['parameters']);self.assertNotIn('lab_runtime',plan['parameters'])
  self.assertIn('service_entry.py',plan['parameters'])

 def test_callback_mutating_original_plan_never_redirects_owned_effects(self):
  for trigger in ('BEGIN','STAGE'):
   with self.subTest(trigger=trigger):
    backend=FakeWindows();plan=service_plan(self.source,self.pin,self.root/('service-'+trigger),'install','node','CONTROL',backend)
    approved_code=Path(plan['code']);outside=self.root/('unapproved-'+trigger)
    def mutate(action,pin):
     if action==trigger:plan['code']=str(outside);plan['root']=str(outside/'also-unapproved')
     return True
    resource=ServiceResource.create(plan,backend,mutate)
    self.assertFalse(outside.exists(),'caller alias redirected owned writes')
    self.assertTrue(approved_code.exists());self.assertEqual(resource.plan['code'],str(approved_code))

 def test_exact_computer_binding_rejects_wrong_host_before_begin(self):
  plan=self.plan();self.assertEqual(plan['computer_name'],'TEST-PC')
  self.backend.host='OTHER-PC'
  with self.assertRaises(ValueError):ServiceResource.create(plan,self.backend,self.guard)
  self.assertFalse(Path(plan['root']).exists());self.assertEqual(self.backend.calls,[])
 @unittest.skipUnless(os.name=='nt','GetComputerNameW host identity independent of env')
 def test_computer_env_spoof_does_not_admit_wrong_host(self):
  import unified_system.installation_service as service
  from unified_system.contracts import seal
  actual=service.current_computer_name();plan=self.plan();plan['computer_name']='DefinitelyOtherHost'
  plan['plan_sha256']=seal({k:v for k,v in plan.items() if k!='plan_sha256'})
  with patch.dict(os.environ,{'COMPUTERNAME':'DefinitelyOtherHost'}),patch.object(service,'_run') as child:
   self.assertEqual(service.current_computer_name(),actual)
   with self.assertRaises(ValueError):WindowsServiceBoundary().call('BEGIN',plan,self.guard)
   child.assert_not_called()
  self.assertFalse(Path(plan['root']).exists())

 def republish_entry(self,raw):
  import json
  entry='sources/unified-system/unified_system/service_entry.py'
  (self.source/entry).write_bytes(raw)
  manifest=json.loads((self.source/'lab-release.json').read_bytes())
  manifest['files'][entry]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
  published=lab_release.canonical(manifest);(self.source/'lab-release.json').write_bytes(published);self.pin=hashlib.sha256(published).hexdigest()
 def test_crlf_operator_checkout_accepts_exact_reviewed_lf_capsule(self):
  import unified_system.installation_service as service
  raw=(self.source/'sources/unified-system/unified_system/service_entry.py').read_bytes();self.assertNotIn(b'\r\n',raw)
  operator=self.root/'crlf-operator';operator.mkdir();(operator/'service_entry.py').write_bytes(raw.replace(b'\n',b'\r\n'))
  self.assertNotEqual(hashlib.sha256((operator/'service_entry.py').read_bytes()).hexdigest(),hashlib.sha256(raw).hexdigest())
  manifest_before=(self.source/'lab-release.json').read_bytes()
  with patch.object(service,'__file__',str(operator/'installation_service.py')):
   plan=self.plan();resource=ServiceResource.create(plan,self.backend,self.guard)
   self.assertEqual(resource.inspect(self.guard)['status'],'STOPPED_RESOURCE_RECORDED')
  self.assertEqual((self.source/'sources/unified-system/unified_system/service_entry.py').read_bytes(),raw)
  self.assertEqual((self.source/'lab-release.json').read_bytes(),manifest_before)
 def test_crlf_candidate_and_executing_candidate_remain_unadmitted_even_resealed(self):
  raw=(self.source/'sources/unified-system/unified_system/service_entry.py').read_bytes();marker=self.root/'candidate-executed'
  executing=('from pathlib import Path\nPath('+repr(str(marker))+').write_text("EXECUTED")\n').encode()+raw
  for modified in (raw.replace(b'\n',b'\r\n'),executing):
   with self.subTest(crlf=modified!=executing):
    self.republish_entry(modified)
    self.assertEqual(lab_release.verify_capsule(self.source,self.pin)['manifest_sha256'],self.pin)
    with self.assertRaises(ValueError):self.plan()
    self.assertFalse(marker.exists());self.assertEqual(self.backend.calls,[]);self.assertFalse((self.root/'service').exists())

 def test_default_denial_precedes_mutation(self):
  plan=self.plan()
  with self.assertRaises(ValueError):ServiceResource.create(plan,self.backend)
  self.assertEqual(self.backend.calls,[]);self.assertFalse(Path(plan['root']).exists())
 def test_stopped_owned_resource_actual_capsule_staging_and_reopen(self):
  plan=self.plan();resource=ServiceResource.create(plan,self.backend,self.guard)
  snapshot=resource.inspect(self.guard)
  self.assertEqual(snapshot['status'],'STOPPED_RESOURCE_RECORDED');self.assertEqual(snapshot['readiness'],'NOT_PROVEN')
  self.assertEqual(lab_release.verify_capsule(plan['code'],self.pin)['manifest_sha256'],self.pin)
  self.assertEqual(ServiceResource.open(plan,self.backend).inspect(self.guard),snapshot)
  self.assertEqual(self.backend.service['state'],1);self.assertFalse(any(x in self.backend.calls for x in ('START','STOP','DELETE')))
  self.assertTrue(all(pin==plan['plan_sha256'] for _,pin in self.grants))
 def test_wrong_phase_grant_and_existing_service_never_adopted(self):
  plan=self.plan()
  with self.assertRaises(ValueError):ServiceResource.create(plan,self.backend,lambda a,p:p=='wrong')
  self.backend.service={'foreign':True}
  with self.assertRaises(ValueError):ServiceResource.create(plan,self.backend,self.guard)
  self.assertEqual(self.backend.service,{'foreign':True});self.assertFalse(Path(plan['root']).exists())
 def test_partial_failure_retains_and_never_adopts_unreceipted_service(self):
  plan=self.plan();self.backend.fault='REGISTER'
  with self.assertRaises(OSError):ServiceResource.create(plan,self.backend,self.guard)
  self.assertTrue(Path(plan['code']).exists())
  self.backend.fault=None
  with self.assertRaises(ValueError):ServiceResource.open(plan,self.backend).inspect(self.guard)
  with self.assertRaises(ValueError):ServiceResource.create(plan,self.backend,self.guard)
 def test_created_but_unreceipted_service_is_retained_and_not_adopted(self):
  plan=self.plan()
  def lost_receipt(action,pin):return not (action=='WRITE_RECEIPT' and self.backend.service is not None)
  with self.assertRaises(ValueError):ServiceResource.create(plan,self.backend,lost_receipt)
  self.assertIsNotNone(self.backend.service);before=copy.deepcopy(self.backend.service)
  incomplete=ServiceResource.open(plan,self.backend)
  with self.assertRaises(ValueError):incomplete.recorded()
  with self.assertRaises(ValueError):incomplete.inspect(self.guard)
  with self.assertRaises(ValueError):ServiceResource.create(plan,self.backend,self.guard)
  self.assertEqual(self.backend.service,before)
 @unittest.skipUnless(os.name=='nt','Native tool phase-pin failure before launch')
 def test_native_backend_wrong_tool_pins_fail_before_spawn(self):
  import unified_system.installation_service as service
  plan=self.plan()
  with patch.object(service,'_run') as child:
   with self.assertRaises(ValueError):WindowsServiceBoundary().call('INSPECT',plan,self.guard)
   child.assert_not_called()

 def test_live_identity_acl_or_configuration_drift_rejected(self):
  plan=self.plan();resource=ServiceResource.create(plan,self.backend,self.guard)
  original=copy.deepcopy(self.backend.service)
  for key,value in [('account','LocalSystem'),('state',4),('state',True),('start_type',2),('sid_type',0),('service_sid','S-1-5-19'),('application','foreign'),('directory','foreign'),('parameters','--arbitrary'),('marker','f'*64),('code_acl_sha256','b'*64),('acl_policy','GENERIC_LOCALSERVICE')]:
   with self.subTest(key=key):
    self.backend.service=copy.deepcopy(original);self.backend.service[key]=value
    with self.assertRaises(ValueError):resource.inspect(self.guard)
 def test_no_candidate_byte_or_receipt_admits_execution(self):
  plan=self.plan();resource=ServiceResource.create(plan,self.backend,self.guard)
  (Path(plan['code'])/'runtime/nssm/nssm.exe').write_bytes(b'changed')
  with self.assertRaises(ValueError):resource.inspect(self.guard)
 def test_stage_denial_and_resealed_arbitrary_arguments_rejected(self):
  from unified_system.contracts import seal
  plan=self.plan()
  with self.assertRaises(ValueError):ServiceResource.create(plan,self.backend,lambda action,pin:action!='STAGE')
  self.assertFalse(Path(plan['code']).exists());self.assertNotIn('SEAL',self.backend.calls)
  changed=copy.deepcopy(plan);changed['parameters']='--arbitrary';changed['plan_sha256']=seal({k:v for k,v in changed.items() if k!='plan_sha256'})
  with self.assertRaises(ValueError):ServiceResource.open(changed,self.backend)
 def test_private_recorded_copy_survives_partial_code_removal_no_authority(self):
  plan=self.plan();resource=ServiceResource.create(plan,self.backend,self.guard)
  recorded=resource.recorded();recorded['plan']['parameters']='changed';recorded['proof']['state']=4
  self.assertNotEqual(resource.recorded()['plan']['parameters'],'changed');self.assertEqual(resource.recorded()['proof']['state'],1)
  (Path(plan['code'])/'runtime/nssm/nssm.exe').unlink()
  self.assertEqual(resource.recorded()['plan']['plan_sha256'],plan['plan_sha256'])
  with self.assertRaises(ValueError):resource.inspect(self.guard)
 @unittest.skipUnless(os.name=='nt','Read-only isolated PowerShell module autoload boundary')
 def test_poisoned_parent_module_path_cannot_autoload_user_module(self):
  import subprocess
  import unified_system.installation_service as service
  modules=self.root/'poison-modules';module=modules/'UnifiedPoisonProbe';module.mkdir(parents=True);marker=self.root/'autoload-marker'
  escaped=str(marker).replace("'","''")
  (module/'evil.psm1').write_text("function Get-UnifiedPoisonProbe { [IO.File]::WriteAllText('"+escaped+"','loaded'); 'POISON' };Export-ModuleMember -Function Get-UnifiedPoisonProbe")
  (module/'UnifiedPoisonProbe.psd1').write_text("@{RootModule='evil.psm1';ModuleVersion='1.0.0';FunctionsToExport=@('Get-UnifiedPoisonProbe');CmdletsToExport=@();AliasesToExport=@()}")
  command="try{Get-UnifiedPoisonProbe -ErrorAction Stop}catch{Write-Output 'POISON_NOT_FOUND'}"
  executable=service._native_tools()['powershell']['path']
  control=service._environment();control['PSModulePath']=str(modules)
  result=subprocess.run([executable,'-NoProfile','-NonInteractive','-Command',command],env=control,capture_output=True,timeout=15)
  self.assertEqual(result.returncode,0);self.assertTrue(marker.exists(),'control must demonstrate actual poison autoload');marker.unlink()
  with patch.dict(os.environ,{'PSModulePath':str(modules)}):safe=service._environment()
  self.assertEqual(safe['PSModulePath'],str(service._system_directory()/'WindowsPowerShell/v1.0/Modules'))
  result=subprocess.run([executable,'-NoProfile','-NonInteractive','-Command',command],env=safe,capture_output=True,timeout=15)
  self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'));self.assertIn(b'POISON_NOT_FOUND',result.stdout);self.assertFalse(marker.exists())

 @unittest.skipUnless(os.name=='nt','GetSystemDirectoryW native path consistency')
 def test_env_redirect_does_not_select_native_tools(self):
  import unified_system.installation_service as service
  with patch.dict(os.environ,{'SYSTEMROOT':str(self.root/'redirected')}):
   with patch.object(service,'_run') as child:
    with self.assertRaises(ValueError):WindowsServiceBoundary().sid('UnifiedLab_ReadOnlyTest')
    child.assert_not_called()

 def test_documented_sid_parser_localized_strict_bounded(self):
  sid='S-1-5-80-1-2-3-4-4294967295'
  self.assertEqual(parse_service_sid('Dienstname: UnifiedLab_abc\nDienst-SID: '+sid+'\n',0),sid)
  for text,code in [(sid,1),(sid+' '+sid,0),('S-1-5-19',0),('S-1-5-80-01-2-3-4-5',0),('S-1-5-80-1-2-3-4-4294967296',0),(sid+'-6',0),('x'*65537,0),('prefix'+sid,0),(sid+'suffix',0),(sid,False)]:
   with self.subTest(text=text[:70]),self.assertRaises(ValueError):parse_service_sid(text,code)
 @unittest.skipUnless(os.name=='nt','Windows documented read-only sc.exe probe')
 def test_real_read_only_showsid_for_nonexistent_name_no_service_created(self):
  name='UnifiedLab_SidParserReadOnly_20261104'
  sid=WindowsServiceBoundary().sid(name)
  self.assertRegex(sid,r'^S-1-5-80-(?:[0-9]+-){4}[0-9]+$')
 @unittest.skipUnless(os.name=='nt','PowerShell parser and C# declaration compilation only')
 def test_real_module_parses_and_native_declarations_compile_without_api_calls(self):
  import subprocess
  module=Path(__file__).resolve().parents[1]/'scripts/UnifiedOwnedService.psm1'
  command="$ErrorActionPreference='Stop';$t=$null;$e=$null;$null=[Management.Automation.Language.Parser]::ParseFile($env:UNIFIED_TEST_MODULE,[ref]$t,[ref]$e);if($e.Count){throw 'PARSER_REJECTED'};$m=Import-Module -Name ([WildcardPattern]::Escape($env:UNIFIED_TEST_MODULE)) -PassThru;& $m {Add-Type -TypeDefinition $script:Native;Write-Output 'DECLARATIONS_COMPILED'}"
  import unified_system.installation_service as service
  env=service._environment();env['UNIFIED_TEST_MODULE']=str(module)
  # These child processes only emit known strings; no SCM/ACL API is called.
  command+=";$ps=Join-Path ([Environment]::SystemDirectory) 'WindowsPowerShell\\v1.0\\powershell.exe';$child=\"[Console]::OutputEncoding=[Text.Encoding]::GetEncoding([Globalization.CultureInfo]::CurrentCulture.TextInfo.OEMCodePage);[Console]::Write('C:\\LAB\\'+[char]0xdc+[char]0xe9)\";$enc=[Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($child));$value=[UnifiedStoppedServiceNative]::Run($ps,('-NoProfile -NonInteractive -EncodedCommand '+$enc));if($value -cne ('C:\\LAB\\'+[char]0xdc+[char]0xe9)){throw 'UNICODE_ROUNDTRIP_REJECTED'};$large=\"[Console]::Write(('x'*70000))\";$enc=[Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($large));$limited=$false;try{$null=[UnifiedStoppedServiceNative]::Run($ps,('-NoProfile -NonInteractive -EncodedCommand '+$enc))}catch{$limited=$true};if(-not $limited){throw 'OUTPUT_CAP_NOT_ENFORCED'};Write-Output 'UNICODE_AND_OUTPUT_BOUND_VERIFIED'"
  result=subprocess.run([service._native_tools()['powershell']['path'],'-NoProfile','-NonInteractive','-Command',command],env=env,capture_output=True,timeout=30)
  self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'));self.assertIn(b'DECLARATIONS_COMPILED',result.stdout);self.assertIn(b'UNICODE_AND_OUTPUT_BOUND_VERIFIED',result.stdout)

 def test_static_module_no_start_stop_delete_or_policy_bypass(self):
  module=Path(__file__).resolve().parents[1]/'scripts/UnifiedOwnedService.psm1';source=module.read_text()
  for forbidden in ('CreateServiceSid','RtlCreateServiceSid','Start-Service','Stop-Service','DeleteService','ExecutionPolicy','safe.directory=*'):self.assertNotIn(forbidden,source)
  self.assertIn('CreateServiceW',source);self.assertIn('QueryServiceConfig2W',source)
  self.assertIn('NT SERVICE\\',source)

if __name__=='__main__':unittest.main()
