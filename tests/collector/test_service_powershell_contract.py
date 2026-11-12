"""PS parser/pure extracted functions only; no module import or native commands."""
import copy
import ctypes
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).absolute().parents[2]
sys.path.insert(0,str(ROOT))
from unified_system import collector_service_plan as policy

PWSH=Path(r'C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1111-574-0_26.1111.574.0_x64__3k8sg7r9htsxt/dependencies/native/powershell/pwsh.exe')
MODULE=ROOT/'scripts/UnifiedOwnedService.psm1'
PURE=('Hash-OwnedText','ConvertTo-OwnedCollectorString','ConvertTo-OwnedCollectorCanonical',
      'Assert-OwnedCollectorKeys','Assert-OwnedCollectorPlan','Get-OwnedCollectorExpected',
      'Invoke-OwnedCollectorService','Invoke-UnifiedOwnedService')
GIT=r'C:/Program Files/Git/bin/git.exe'
BASE='dde3d827afea7bff97ae044b5b4f7cf2cd214c25'

HARNESS=r'''
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$inputData=[Console]::In.ReadToEnd()|ConvertFrom-Json -Depth 16
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($inputData.module,[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'MODULE_PARSE_ERRORS'}
$names=@('Hash-OwnedText','ConvertTo-OwnedCollectorString','ConvertTo-OwnedCollectorCanonical','Assert-OwnedCollectorKeys','Assert-OwnedCollectorPlan','Get-OwnedCollectorExpected','Invoke-OwnedCollectorService','Invoke-UnifiedOwnedService')
$functions=@($ast.FindAll({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst]},$true))
foreach($name in $names){$found=@($functions|Where-Object Name -CEQ $name);if($found.Count -ne 1){throw 'MISSING_PURE_COLLECTOR_FUNCTION'};. ([scriptblock]::Create($found[0].Extent.Text))}
function Get-OwnedCollectorExecutorPin {return $inputData.executor_pin}
$script:effectCalls=0
foreach($name in @('Assert-OwnedAdmin','Assert-OwnedPath','Get-OwnedSid','Assert-OwnedFile','Set-OwnedAcl','Get-OwnedProof','Get-OwnedService','Invoke-OwnedNative')){Set-Item ('function:'+$name) { $script:effectCalls++;throw 'EFFECT_BOUNDARY_REACHED' }}
$result=@()
foreach($case in $inputData.cases){
 try{
  if($case.operation -ceq 'request'){$value=Invoke-UnifiedOwnedService $case.value}
  elseif($case.operation -ceq 'collector_request'){$value=Invoke-OwnedCollectorService $case.value}
  elseif($case.operation -ceq 'proof'){$value=Get-OwnedCollectorExpected $case.value}
  else{$null=Assert-OwnedCollectorPlan $case.value;$value='VALID'}
  $result+=@{id=$case.id;outcome='ACCEPTED';value=$value}
 }catch{$result+=@{id=$case.id;outcome=[string]$_.Exception.Message}}
}
[Console]::Out.Write((@{cases=$result;effect_calls=$script:effectCalls}|ConvertTo-Json -Compress -Depth 16))
'''

CUSTODY_HARNESS=r'''
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$data=[Console]::In.ReadToEnd()|ConvertFrom-Json
$tokens=$null;$errors=$null;$ast=[Management.Automation.Language.Parser]::ParseFile($data.module,[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'MODULE_PARSE_ERRORS'}
$function=@($ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq 'Get-OwnedCollectorExecutorPin'},$true))
if($function.Count -ne 1){throw 'GETTER_REQUIRED'}
$body=$function[0].Extent.Text
# Substitute only the external acquisition boundaries, not try/catch/finally or
# disposal logic. No module import, real stream, hash provider or file getter.
foreach($part in @('$module=$MyInvocation.MyCommand.Module','[IO.File]::OpenRead($module.Path)','[Security.Cryptography.SHA256]::Create()')){if(-not $body.Contains($part)){throw 'CUSTODY_SOURCE_DRIFT'}}
$body=$body.Replace('$module=$MyInvocation.MyCommand.Module','$module=[pscustomobject]@{Path="INERT"}')
$body=$body.Replace('[IO.File]::OpenRead($module.Path)','(Open-InertStream)').Replace('[Security.Cryptography.SHA256]::Create()','(New-InertHash)')
. ([scriptblock]::Create($body))
function Open-InertStream {
 $script:opens++
 if($script:mode -ceq 'open_failure'){throw 'OPEN_FAILURE'}
 $stream=[pscustomobject]@{Length=128}
 $stream|Add-Member ScriptMethod Dispose {$script:stream_disposes++;if($script:mode -in @('stream_dispose','factory_and_stream_dispose','compute_and_both_dispose')){throw 'STREAM_DISPOSE_FAILURE'}}
 return $stream
}
function New-InertHash {
 $script:factories++
 if($script:mode -in @('hash_factory','factory_and_stream_dispose')){throw 'HASH_FACTORY_FAILURE'}
 $hash=[pscustomobject]@{}
 $hash|Add-Member ScriptMethod ComputeHash {param($stream) if($script:mode -ceq 'compute_and_both_dispose'){throw 'COMPUTE_FAILURE'};return ,([byte[]](0..31))}
 $hash|Add-Member ScriptMethod Dispose {$script:hash_disposes++;if($script:mode -in @('hash_dispose','compute_and_both_dispose')){throw 'HASH_DISPOSE_FAILURE'}}
 return $hash
}
$results=@()
foreach($mode in $data.modes){
 $script:mode=$mode;$script:opens=0;$script:factories=0;$script:hash_disposes=0;$script:stream_disposes=0
 try{$value=Get-OwnedCollectorExecutorPin;$outcome='OK';$inner=@()}
 catch{$value=$null;$outcome=$_.Exception.Message;$inner=@();if($_.Exception -is [AggregateException]){$inner=@($_.Exception.InnerExceptions|ForEach-Object Message)}}
 $results+=@{mode=$mode;outcome=$outcome;value=$value;inner=$inner;opens=$script:opens;factories=$script:factories;hash_disposes=$script:hash_disposes;stream_disposes=$script:stream_disposes}
}
[Console]::Out.Write((@{results=$results}|ConvertTo-Json -Depth 8 -Compress))
'''

def seal(value):return hashlib.sha256(policy.lab_release.canonical(value)).hexdigest()

class CollectorPowerShellContracts(unittest.TestCase):
 def setUp(self):
  native=patch.object(ctypes,'WinDLL',side_effect=AssertionError('REAL_DLL_REJECTED'),create=True)
  native.start();self.addCleanup(native.stop)
  self.temp=tempfile.TemporaryDirectory(prefix='collector-ps-source-');self.addCleanup(self.temp.cleanup)
  root=Path(self.temp.name).resolve();self.root=root
  code=root/'code';source=root.parent/(root.name+'-source')
  plan=dict(schema=policy.SCHEMA,installation_id='unit-install',node_id='unit-node',computer_name='UNIT-HOST',
   role='COLLECTOR',root=str(root),code=str(code),state=str(root/'state'),capsule_root=str(source),
   manifest_sha256='1'*64,service_sid='S-1-5-80-1-2-3-4-5',activation='BLOCKED',
   collector_bootstrap_sha256=policy.BOOTSTRAP_PIN,security_helper_sha256=policy.SECURITY_PIN,
   job_helper_sha256='2'*64,collector_profile_sha256='3'*64,source_manifest_sha256='4'*64,
   executor_sha256=policy.EXECUTOR_PIN,native_tools={n:dict(path=str(root/(n+'.exe')),sha256='5'*64) for n in ('sc','powershell')})
  plan['service_name']='UnifiedCollector_'+seal(dict(domain=policy.SCHEMA,installation_id=plan['installation_id'],node_id=plan['node_id']))[:24]
  pins=dict(python='6'*64,nssm=policy.NSSM_PIN,entry=policy.ENTRY_PIN,bootstrap=policy.BOOTSTRAP_PIN)
  for key,relative in policy.PATHS.items():plan[key]=str(code/relative);plan[key+'_sha256']=pins[key]
  plan['parameters']='-I -S -B "'+plan['entry']+'"';self.plan=self.reseal(plan)
 def reseal(self,value):
  value['plan_sha256']=seal({k:v for k,v in value.items() if k!='plan_sha256'});return value
 def run_cases(self,cases):
  process=subprocess.run([str(PWSH),'-NoLogo','-NoProfile','-NonInteractive','-Command',HARNESS],
   input=json.dumps(dict(module=str(MODULE),executor_pin=hashlib.sha256(MODULE.read_bytes()).hexdigest(),cases=cases)).encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20,check=False)
  self.assertEqual(process.returncode,0,process.stderr.decode(errors='replace'))
  result=json.loads(process.stdout);self.assertEqual(result['effect_calls'],0);return result['cases']
 def test_new_plan_is_accepted_as_data_and_expected_proof_matches(self):
  cases=self.run_cases([dict(id='valid',operation='plan',value=self.plan),dict(id='proof',operation='proof',value=self.plan)])
  self.assertEqual(cases[0]['outcome'],'ACCEPTED');self.assertEqual(cases[1]['outcome'],'ACCEPTED')
  proof=cases[1]['value'];self.assertEqual(proof['parameters'],self.plan['parameters']);self.assertEqual(proof['account'],'NT AUTHORITY\\LocalService')
  self.assertEqual(proof['sid_type'],1);self.assertEqual(proof['start_type'],3);self.assertEqual(proof['state'],1)
  self.assertEqual(proof['app_exit'],'Exit');self.assertIs(proof['execution_authority'],False)
  # Isolate expected-proof formatting; this double is not capsule admission.
  with patch.object(policy,'check_collector_service_plan',return_value={}):self.assertEqual(proof,policy.expected_collector_service(self.plan))
 def test_unknown_v1_and_drifting_collector_fields_reject(self):
  cases=[]
  for field,value in [('schema','unified.owned-stopped-service.v1'),('schema','unknown'),('role','WORKER'),('activation','READY'),
   ('entry',str(self.root/'service_entry.py')),('bootstrap',str(self.root/'owned_python.py')),('parameters','-m unified_system.collector_entry'),
   ('entry_sha256','0'*64),('security_helper_sha256','0'*64),('collector_bootstrap_sha256','0'*64),('nssm_sha256','0'*64),
   ('collector_profile_sha256',True),('source_manifest_sha256','bad'),('manifest_sha256','bad'),('job_helper_sha256','bad'),('executor_sha256','0'*64),
   ('service_sid','S-1-5-18'),('service_name','UnifiedLab_'+'a'*24),('state',str(self.root/'other'))]:
   plan=copy.deepcopy(self.plan);plan[field]=value;cases.append(dict(id=field+str(len(cases)),operation='plan',value=self.reseal(plan)))
  for result in self.run_cases(cases):self.assertNotEqual(result['outcome'],'ACCEPTED',result)
 def test_closed_keys_types_and_seal_reject(self):
  values=[]
  for field in policy.FIELDS:
   plan=copy.deepcopy(self.plan);plan.pop(field);values.append(plan)
  plan=copy.deepcopy(self.plan);plan['extra']='x';values.append(self.reseal(plan))
  plan=copy.deepcopy(self.plan);plan['plan_sha256']='0'*64;values.append(plan)
  plan=copy.deepcopy(self.plan);plan['native_tools']['sc']['extra']='x';values.append(self.reseal(plan))
  for result in self.run_cases([dict(id=str(i),operation='plan',value=p) for i,p in enumerate(values)]):self.assertNotEqual(result['outcome'],'ACCEPTED',result)
 def test_every_action_is_operationally_blocked_without_effect_calls(self):
  cases=[dict(id=action,operation='request',value=dict(action=action,plan=self.plan)) for action in ('BEGIN','SEAL','REGISTER','INSPECT')]
  for result in self.run_cases(cases):self.assertEqual(result['outcome'],'COLLECTOR_OPERATIONAL_ADAPTER_NOT_AVAILABLE')
 def test_request_extra_approval_hash_and_unknown_actions_never_admit(self):
  values=[dict(action='START',plan=self.plan),dict(action=True,plan=self.plan),
   dict(action='REGISTER',plan=self.plan,operational_admission_sha256='a'*64)]
  for result in self.run_cases([dict(id=str(i),operation='collector_request',value=value) for i,value in enumerate(values)]):
   self.assertNotIn(result['outcome'],('ACCEPTED','COLLECTOR_OPERATIONAL_ADAPTER_NOT_AVAILABLE'))
 def test_canonical_unicode_and_domain_separated_name_match_python(self):
  plan=copy.deepcopy(self.plan)
  # Unicode is valid in path metadata. Canonical JSON must match ensure_ascii
  # and UTF-16 surrogate pairs, not a culture-dependent ConvertTo-Json seal.
  for key in ('root','code','state','capsule_root','entry','bootstrap','python','nssm','parameters'):
   plan[key]=plan[key].replace(str(self.root),str(self.root)+'-é-😀')
  for tool in plan['native_tools'].values():tool['path']=tool['path'].replace(str(self.root),str(self.root)+'-é-😀')
  self.reseal(plan)
  self.assertEqual(self.run_cases([dict(id='unicode',operation='plan',value=plan)])[0]['outcome'],'ACCEPTED')
 def test_final_newline_digest_label_and_sid_aliases_reject(self):
  cases=[]
  for field in ('collector_profile_sha256','source_manifest_sha256','manifest_sha256','job_helper_sha256','python_sha256','computer_name','service_sid'):
   plan=copy.deepcopy(self.plan);plan[field]+='\n';cases.append(dict(id=field,operation='plan',value=self.reseal(plan)))
  for result in self.run_cases(cases):self.assertNotEqual(result['outcome'],'ACCEPTED',result)
 def test_python_path_input_bound_is_not_widened(self):
  plan=copy.deepcopy(self.plan);long_root='C:\\'+'\\'.join(['a'*240]*18)
  self.assertGreater(len(long_root),4096)
  for key in ('root','code','state','capsule_root','entry','bootstrap','python','nssm','parameters'):
   plan[key]=plan[key].replace(str(self.root),long_root)
  for tool in plan['native_tools'].values():tool['path']=tool['path'].replace(str(self.root),long_root)
  self.reseal(plan)
  self.assertNotEqual(self.run_cases([dict(id='long-path',operation='plan',value=plan)])[0]['outcome'],'ACCEPTED')
 def test_getter_factory_and_dispose_faults_preserve_independent_custody(self):
  modes=['none','open_failure','hash_factory','hash_dispose','stream_dispose','factory_and_stream_dispose','compute_and_both_dispose']
  result=subprocess.run([str(PWSH),'-NoLogo','-NoProfile','-NonInteractive','-Command',CUSTODY_HARNESS],
   input=json.dumps(dict(module=str(MODULE),modes=modes)).encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20,check=False)
  self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'))
  for row in json.loads(result.stdout)['results']:
   with self.subTest(mode=row['mode']):
    self.assertEqual(row['stream_disposes'],0 if row['mode']=='open_failure' else 1)
    self.assertEqual(row['hash_disposes'],0 if row['mode'] in ('open_failure','hash_factory','factory_and_stream_dispose') else 1)
    if row['mode']=='none':self.assertEqual(row['outcome'],'OK');self.assertEqual(row['value'],bytes(range(32)).hex())
    elif row['mode']=='hash_factory':self.assertIn('HASH_FACTORY_FAILURE',row['outcome'])
    elif row['mode']=='open_failure':self.assertIn('OPEN_FAILURE',row['outcome'])
    else:
     expected=3 if row['mode']=='compute_and_both_dispose' else 2 if row['mode']=='factory_and_stream_dispose' else 1
     self.assertEqual(len(row['inner']),expected)
     text=' '.join(row['inner'])
     if row['mode']=='factory_and_stream_dispose':self.assertIn('HASH_FACTORY_FAILURE',text);self.assertIn('STREAM_DISPOSE_FAILURE',text)
     if row['mode']=='compute_and_both_dispose':
      for marker in ('COMPUTE_FAILURE','HASH_DISPOSE_FAILURE','STREAM_DISPOSE_FAILURE'):self.assertIn(marker,text)
 def test_dispatch_precedes_existing_native_owner_branch(self):
  source=MODULE.read_text();start=source.index('function Invoke-UnifiedOwnedService(');body=source[start:]
  self.assertLess(body.index('Invoke-OwnedCollectorService'),body.index('Assert-OwnedAdmin'))
 def old_source(self):
  return subprocess.check_output([GIT,'--no-replace-objects','-C',str(ROOT),'show',BASE+':scripts/UnifiedOwnedService.psm1'])
 def test_existing_v1_prefix_and_action_tail_are_exact_primary_source(self):
  old=self.old_source().decode();new=MODULE.read_text()
  name='function Invoke-UnifiedOwnedService($Request){'
  added=" if($p.schema -is [string] -and $p.schema -ceq 'unified.owned-collector-stopped-service.v1'){return Invoke-OwnedCollectorService $Request}\n"
  self.assertEqual(new[:new.index('function Get-OwnedCollectorExecutorPin')],old[:old.index(name)])
  tail=new[new.index(name):];self.assertEqual(tail.count(added),1);self.assertEqual(tail.replace(added,''),old[old.index(name):])
 def test_old_saved_v1_plan_requires_its_exact_executor_cohort(self):
  from tests.test_installation_service import ServiceResourceTests
  from unified_system import installation_service as old_policy
  case=ServiceResourceTests('test_registered_command_uses_only_reviewed_protected_entry');case.setUp()
  try:
   old_file=self.root/'retained-v1-executor.psm1';old_file.write_bytes(self.old_source())
   old_hash=hashlib.sha256(old_file.read_bytes()).hexdigest();new_hash=hashlib.sha256(MODULE.read_bytes()).hexdigest()
   self.assertNotEqual(old_hash,new_hash)
   with patch.object(old_policy,'MODULE',old_file):
    saved=case.plan();self.assertEqual(saved['executor_sha256'],old_hash);old_policy._check_plan(saved)
   with self.assertRaises(ValueError):old_policy._check_plan(saved)
   fresh=case.plan();self.assertEqual(fresh['executor_sha256'],new_hash);old_policy._check_plan(fresh)
   self.assertEqual(saved['parameters'],fresh['parameters']);self.assertEqual(saved['schema'],fresh['schema'])
   with patch.object(old_policy,'MODULE',old_file):old_policy._check_plan(saved)
   self.assertEqual(case.backend.calls,[]) # Factory/checker only, no fake effects.
  finally:case.doCleanups()

if __name__=='__main__':unittest.main()
