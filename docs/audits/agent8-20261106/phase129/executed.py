import sys,os,json,tempfile
from pathlib import Path
sys.path[:0]=sys.argv[1:3]+[sys.argv[1]+'/tests/coordination/assignment_v1/unqualified_registration']
import test_local_adapter as t
from unified_system.journal import Journal
from grid.authority_assignment_v1 import RootRegistrationCustody,RegistrationCustodyUnavailable
case=t.LocalAdapterTests();case.setUp()
with tempfile.TemporaryDirectory(prefix='a8-failed-entry-') as folder:
 path=Path(folder)/'owned.sqlite';sidecar=path.with_name(path.name+'-journal')
 owned=RootRegistrationCustody(Journal(path),original_intent_bytes=case.raw)
 try:
  owned.retain_original();sidecar.write_bytes(b'A8_OWNED_FAULT_BEFORE_WITH_ENTRY')
  try:
   with owned:raise AssertionError('BODY_MUST_NOT_RUN')
  except RegistrationCustodyUnavailable as exc:
   assert str(exc)=='SIDECAR_REQUIRES_EXPLICIT_OWNER_RECOVERY'
   error=str(exc)
  else:raise AssertionError('ENTRY_MUST_FAIL')
  assert owned._closed is False and owned._db_fd is not None and owned._lock_fd is not None
  os.fstat(owned._db_fd);os.fstat(owned._lock_fd)
  denied=case.child(path,'DENIED');assert denied['reason']=='EXCLUSIVE_ROOT_JOURNAL_OWNERSHIP_UNAVAILABLE'
  sidecar.unlink();owned.close()
  acquired=case.child(path,'ACQUIRED')
  print(json.dumps(dict(finding='A8-F28',exact_head='19fae71db66a24f7be7bfa8d1682e1831c4720c4',entry_error=error,with_body_executed=False,closed_after_failed_entry=False,both_owned_fds_still_open=True,contender_while_leaked=denied,after_explicit_owner_cleanup=acquired,manual_cleanup_required=True,native_rpc_calls=0,scope='OWN_LOCAL_ACTUAL_FAILED_ENTRY_REPRODUCTION_NOT_FULL12_RERUN')))
 finally:
  if sidecar.exists():sidecar.unlink()
  owned.close()
