"""Test-only, bounded static phases; never native service authorization."""
import re
import subprocess
import time

PHASES=frozenset({'ENTRY','IMPORT_BEGIN','IMPORT_END','MEMBER_BEGIN','MEMBER_END',
                 'COMPILE_BEGIN','COMPILE_END','CHILD_BEGIN','CHILD_END',
                 'CONTROL_LOOKUP_BEGIN','CONTROL_LOOKUP_END',
                 'SAFE_LOOKUP_BEGIN','SAFE_LOOKUP_END','DONE'})


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


def run_phased(argv,*,env):
 """Same fatal 15 seconds and one child attempt; never expose raw child data."""
 started=time.monotonic()
 try:result=subprocess.run(argv,env=env,capture_output=True,timeout=15)
 except subprocess.TimeoutExpired as error:
  summary=phase_summary(error.stderr)
  # Drop raw TimeoutExpired args/output from the displayed exception chain.
  raise AssertionError('NATIVE_PHASE_TIMEOUT_15S elapsed_ms='+str(round((time.monotonic()-started)*1000))+' phases='+summary) from None
 summary=phase_summary(result.stderr)
 print('NATIVE_PHASE_RESULT elapsed_ms='+str(round((time.monotonic()-started)*1000))+' phases='+summary,flush=True)
 if result.returncode!=0:raise AssertionError('NATIVE_PHASE_EXIT_NONZERO phases='+summary)
 if summary=='PHASE_DATA_REJECTED':raise AssertionError('NATIVE_PHASE_DATA_REJECTED')
 return result
