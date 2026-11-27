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


def phase(name):
 if name not in PHASES:raise ValueError('UNKNOWN_DIAGNOSTIC_PHASE')
 return "[Console]::Error.WriteLine('UNIFIED_PHASE:"+name+":'+[Diagnostics.Stopwatch]::GetTimestamp());"


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
