"""Separate Collector plan/synthetic entry; no service/provider fallthrough.

Finite offline composition is separate from a plan. This module does not
alter the old protected service argv or claim its caller has operational rights.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
from .collector_profile import decode_collector_profile,collector_plan
from .runtime_process import _safe_path

class CollectorEntryRejected(ValueError):
 def __init__(self):super().__init__('COLLECTOR_ENTRY_REJECTED')

def _need(ok):
 if not ok:raise CollectorEntryRejected()

def read_ordinary_source(value,limit):
 """Bounded read of an existing ordinary local file; no ACL/trust assertion."""
 try:
  _need(type(value) is str and 0<len(value)<=1024)
  _need(type(limit) is int and 0<limit<=262144)
  p=Path(value);_need(p.is_absolute() and '..' not in p.parts and not value.startswith(('//',chr(92))))
  if os.name=='nt':_need(':' not in value[2:])
  p=_safe_path(p);before=p.lstat()
  _need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and 0<before.st_size<=limit)
  fields=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_nlink)
  with p.open('rb') as stream:
   held=os.fstat(stream.fileno());_need(fields(held)==fields(before))
   raw=stream.read(limit+1);after=os.fstat(stream.fileno())
  _need(fields(before)==fields(after)==fields(_safe_path(p).lstat()) and held.st_ctime_ns==after.st_ctime_ns and len(raw)==before.st_size)
  return raw
 except CollectorEntryRejected:raise
 except (OSError,ValueError,TypeError):raise CollectorEntryRejected() from None

def main(argv=None):
 try:
  args=sys.argv[1:] if argv is None else argv
  _need(type(args) is list and len(args) in (4,6) and args[2]=='--manifest')
  plan_only=len(args)==4 and args[0]=='--plan-only'
  synthetic=len(args)==6 and args[0] in ('--synthetic-offline','--resume-synthetic') and args[4]=='--state'
  _need(plan_only or synthetic)
  _need(bool(sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode))
  manifest=read_ordinary_source(args[3],262144)
  profile=decode_collector_profile(read_ordinary_source(args[1],32768),manifest_sha256=hashlib.sha256(manifest).hexdigest())
  if plan_only:result=collector_plan(profile)
  else:
   from .collector_offline import collect_synthetic,synthetic_frames
   coro=collect_synthetic(profile,manifest_bytes=manifest,frames=synthetic_frames(),state_root=Path(args[5]),
    code_root=Path(__file__).absolute().parents[1],observed_at_ms=1794441600000,resume=args[0]=='--resume-synthetic')
   try:
    try:coro.send(None)
    except StopIteration as done:result=done.value
    else:raise CollectorEntryRejected() # No implicit loop/network fallback.
   finally:coro.close()
  print(json.dumps(result,sort_keys=True,separators=(',',':'),allow_nan=False))
  return 0
 except Exception:
  print('BLOCKED_COLLECTOR_ENTRY')
  return 78

if __name__=='__main__':raise SystemExit(main())
