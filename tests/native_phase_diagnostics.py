"""Test-only, bounded static phases; never native service authorization."""
import re
import subprocess
import time

PHASES=frozenset({'ENTRY','IMPORT_BEGIN','IMPORT_END','MEMBER_BEGIN','MEMBER_END',
                 'COMPILE_BEGIN','COMPILE_END','CHILD_BEGIN','CHILD_END',
                 'CONTROL_LOOKUP_BEGIN','CONTROL_LOOKUP_END',
                 'SAFE_LOOKUP_BEGIN','SAFE_LOOKUP_END','DONE',
                 'OBJECT_BEGIN','OBJECT_END','FIRST_MEMBER_BEGIN','FIRST_MEMBER_END',
                 'PARSE_BEGIN','PARSE_END','UNICODE_BEGIN','UNICODE_END','CAP_BEGIN','CAP_END'})
PHASES=PHASES|frozenset({'OTHER_MEMBERS_BEGIN','OTHER_MEMBERS_END','SEED_BEGIN','SEED_END','FOREIGN_REJECT_BEGIN','FOREIGN_REJECT_END','LOOKUP_CALL_BEGIN','LOOKUP_CALL_END','LOOKUP_CATCH_BEGIN','LOOKUP_CATCH_END','LOOKUP_WRITE_BEGIN','LOOKUP_WRITE_END','CHILD_EXCEPTION','EXIT_FACT_BEGIN','EXIT_FACT_END','COMPILE_OUTPUT_BEGIN','COMPILE_OUTPUT_END','CHILD_SETUP_BEGIN','CHILD_SETUP_END'})


def phase(name):
 if name not in PHASES:raise ValueError('UNKNOWN_DIAGNOSTIC_PHASE')
 return "[Console]::Error.WriteLine('UNIFIED_PHASE:"+name+":'+[Diagnostics.Stopwatch]::GetTimestamp());"


def build_ps_probe(kind,command):
 """Only Console phase statements around existing calls; no resolver/import/policy.

 Closed templates fail if their source anchors change. No arbitrary replacement,
 environment selection, native execution or exception-success classification.
 Implicit command discovery versus cmdlet body still needs separate evidence.
 """
 if type(kind) is not str or kind not in ('NSSM_BOOTSTRAP','CHILD_EXIT','CONTROL_LOOKUP','SAFE_LOOKUP','MODULE_COMPILE') or type(command) is not str or not 0<len(command)<=65536 or 'UNIFIED_PHASE:' in command:raise ValueError('UNKNOWN_DIAGNOSTIC_PROBE')
 def replace(old,new,count=1):
  nonlocal command
  if command.count(old)!=count:raise ValueError('DIAGNOSTIC_PROBE_TEMPLATE_CHANGED')
  command=command.replace(old,new,1)
 if kind in ('CONTROL_LOOKUP','SAFE_LOOKUP'):
  expected="try{Get-UnifiedPoisonProbe -ErrorAction Stop}catch{Write-Output 'POISON_NOT_FOUND'}"
  if command!=expected:raise ValueError('DIAGNOSTIC_PROBE_TEMPLATE_CHANGED')
  replace('try{Get-UnifiedPoisonProbe','try{'+phase('LOOKUP_CALL_BEGIN')+'Get-UnifiedPoisonProbe')
  replace('-ErrorAction Stop}catch{','-ErrorAction Stop;'+phase('LOOKUP_CALL_END')+'}catch{'+phase('LOOKUP_CATCH_BEGIN')+phase('LOOKUP_WRITE_BEGIN'))
  replace("Write-Output 'POISON_NOT_FOUND'}","Write-Output 'POISON_NOT_FOUND';"+phase('LOOKUP_WRITE_END')+phase('LOOKUP_CATCH_END')+'}')
  prefix='CONTROL' if kind=='CONTROL_LOOKUP' else 'SAFE'
  return phase('ENTRY')+phase(prefix+'_LOOKUP_BEGIN')+command+';'+phase(prefix+'_LOOKUP_END')+phase('DONE')
 replace('$m=Import-Module',phase('IMPORT_BEGIN')+'$m=Import-Module')
 if kind=='NSSM_BOOTSTRAP':
  replace('$parameters=',phase('IMPORT_END')+phase('MEMBER_BEGIN')+phase('OBJECT_BEGIN')+'$parameters=')
  replace('$parameters|Add-Member',phase('OBJECT_END')+phase('FIRST_MEMBER_BEGIN')+'$parameters|Add-Member',5)
  replace('$parameters|Add-Member ScriptMethod GetValue ',phase('FIRST_MEMBER_END')+phase('OTHER_MEMBERS_BEGIN')+'$parameters|Add-Member ScriptMethod GetValue ')
  replace('\n& $m {param($key)','\n'+phase('OTHER_MEMBERS_END')+phase('MEMBER_END')+phase('SEED_BEGIN')+'& $m {param($key)')
  replace("} $parent\nif($parent.Creates", "} $parent\n"+phase('SEED_END')+'if($parent.Creates')
  replace('try{& $m {param($key)',phase('FOREIGN_REJECT_BEGIN')+'try{& $m {param($key)')
  replace('}catch{$rejected=$true}\nif(', '}catch{$rejected=$true}\n'+phase('FOREIGN_REJECT_END')+'if(')
  return phase('ENTRY')+command+phase('DONE')
 replace(';& $m {Add-Type',';'+phase('IMPORT_END')+'& $m {'+phase('COMPILE_BEGIN')+'Add-Type')
 if kind=='CHILD_EXIT':
  replace("$script:NativeStage='NSSM_SET_APPLICATION'",phase('COMPILE_END')+"$script:NativeStage='NSSM_SET_APPLICATION'")
  replace('try{$null=',phase('CHILD_BEGIN')+'try{$null=')
  replace('catch{};if(', 'catch{'+phase('CHILD_EXCEPTION')+'};'+phase('CHILD_END')+phase('EXIT_FACT_BEGIN')+'if(')
  replace(";Write-Output 'EXIT_FACT_VERIFIED'",';'+phase('EXIT_FACT_END')+"Write-Output 'EXIT_FACT_VERIFIED'")
  return phase('ENTRY')+command+';'+phase('DONE')
 replace('$null=[Management.Automation.Language.Parser]::ParseFile',phase('PARSE_BEGIN')+'$null=[Management.Automation.Language.Parser]::ParseFile')
 replace(';if($e.Count)',';'+phase('PARSE_END')+'if($e.Count)')
 replace(";Write-Output 'DECLARATIONS_COMPILED'",';'+phase('COMPILE_END')+phase('COMPILE_OUTPUT_BEGIN')+"Write-Output 'DECLARATIONS_COMPILED'")
 replace("Write-Output 'DECLARATIONS_COMPILED'}", "Write-Output 'DECLARATIONS_COMPILED';"+phase('COMPILE_OUTPUT_END')+'}')
 replace(';$ps=Join-Path',';'+phase('CHILD_SETUP_BEGIN')+'$ps=Join-Path')
 replace('$value=[UnifiedStoppedServiceNative]::Run',phase('CHILD_SETUP_END')+phase('UNICODE_BEGIN')+'$value=[UnifiedStoppedServiceNative]::Run')
 replace(';if($value -cne',';'+phase('UNICODE_END')+'if($value -cne')
 replace('try{$null=[UnifiedStoppedServiceNative]::Run',phase('CAP_BEGIN')+'try{$null=[UnifiedStoppedServiceNative]::Run')
 replace(';if(-not $limited)',';'+phase('CAP_END')+'if(-not $limited)')
 return phase('ENTRY')+command+';'+phase('DONE')


def phase_summary(raw):
 if raw is None or raw==b'':return 'NO_PHASE_OBSERVED'
 if type(raw) is not bytes or len(raw)>4096:return 'PHASE_DATA_REJECTED'
 try:lines=raw.decode('ascii').splitlines()
 except UnicodeError:return 'PHASE_DATA_REJECTED'
 if not 0<len(lines)<=16:return 'PHASE_DATA_REJECTED'
 result=[]
 for line in lines:
  match=re.fullmatch(r'UNIFIED_PHASE:([A-Z_]{1,32}):([0-9]{1,19})',line)
  if not match or match[1] not in PHASES or int(match[2])>2**63-1:return 'PHASE_DATA_REJECTED'
  result.append(match[1]+'@'+match[2])
 return ','.join(result)


def run_phased(argv,*,env,timeout=15):
 """Existing fatal 15/30 second bounds; one attempt, no raw child data."""
 if type(timeout) is not int or timeout not in (15,30):raise ValueError('UNKNOWN_DIAGNOSTIC_BOUND')
 started=time.monotonic()
 try:result=subprocess.run(argv,env=env,capture_output=True,timeout=timeout)
 except subprocess.TimeoutExpired as error:
  summary=phase_summary(error.stderr)
  # Drop raw TimeoutExpired args/output from the displayed exception chain.
  raise AssertionError('NATIVE_PHASE_TIMEOUT_'+str(timeout)+'S elapsed_ms='+str(round((time.monotonic()-started)*1000))+' phases='+summary) from None
 summary=phase_summary(result.stderr)
 print('NATIVE_PHASE_RESULT elapsed_ms='+str(round((time.monotonic()-started)*1000))+' phases='+summary,flush=True)
 if result.returncode!=0:raise AssertionError('NATIVE_PHASE_EXIT_NONZERO phases='+summary)
 if summary=='PHASE_DATA_REJECTED':raise AssertionError('NATIVE_PHASE_DATA_REJECTED')
 return result


NODE_PHASES=frozenset({'ENTRY','STDIN_END','PARSED','VM_RETURN','FIRST_SETTLED','SECOND_SETTLED','DONE'})


def node_phase_summary(raw):
 if raw is None or raw in (b'',''):return 'NO_PHASE_OBSERVED'
 if type(raw) is str:
  try:raw=raw.encode('ascii')
  except UnicodeError:return 'PHASE_DATA_REJECTED'
 if type(raw) is not bytes or len(raw)>1024:return 'PHASE_DATA_REJECTED'
 try:lines=raw.decode('ascii').splitlines()
 except UnicodeError:return 'PHASE_DATA_REJECTED'
 if not 0<len(lines)<=8:return 'PHASE_DATA_REJECTED'
 phases=[]
 for line in lines:
  match=re.fullmatch(r'UNIFIED_NODE:([A-Z_]{1,32})',line)
  if not match or match[1] not in NODE_PHASES:return 'PHASE_DATA_REJECTED'
  phases.append(match[1])
 return ','.join(phases)


def run_node_phased(argv,*,input):
 started=time.monotonic()
 try:result=subprocess.run(argv,input=input,text=True,capture_output=True,timeout=15)
 except subprocess.TimeoutExpired as error:
  raise AssertionError('NODE_PHASE_TIMEOUT_15S elapsed_ms='+str(round((time.monotonic()-started)*1000))+' phases='+node_phase_summary(error.stderr)) from None
 summary=node_phase_summary(result.stderr)
 print('NODE_PHASE_RESULT elapsed_ms='+str(round((time.monotonic()-started)*1000))+' phases='+summary,flush=True)
 if summary=='PHASE_DATA_REJECTED':raise AssertionError('NODE_PHASE_DATA_REJECTED')
 return result
