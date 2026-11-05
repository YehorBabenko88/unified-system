"""Raw isolated protected-service entry; no application import before admission.

External service registration pins these exact bytes. This is owner admission
for LAB simulation, never publisher authentication or a readiness assertion.
"""
import sys

BOOTSTRAP_SHA256='a8012a04c4a0507a72bd6ba38c63ad0af855d5f25efea7669ea11db1386d8d45'


def main():
 try:
  args=sys.argv[1:]
  valid=args in ([],['--data-first'],['--data-first-worker']) or len(args)==2 and (args[0]=='--module-source' and args[1] in ('meta_analyse','strattester','terminan','grid') or args==['--verify-module-source','strattester'])
  if not (sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode and valid):raise ValueError()
  import ctypes,hashlib,importlib.util,os,stat
  from pathlib import Path
  entry=Path(__file__).absolute();helper=entry.with_name('service_bootstrap.py')
  if not entry.is_absolute() or str(entry).startswith(('//',chr(92))) or '..' in entry.parts:raise ValueError()
  if os.name!='nt':raise ValueError()
  drive=ctypes.WinDLL('kernel32',use_last_error=True).GetDriveTypeW;drive.argtypes=[ctypes.c_wchar_p];drive.restype=ctypes.c_uint
  if drive(str(entry)[:3])!=3:raise ValueError()
  for part in (*reversed(helper.parents),helper):
   info=part.lstat()
   if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&1024:raise ValueError()
  before=helper.stat()
  if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or not 0<before.st_size<=1048576:raise ValueError()
  with helper.open('rb') as stream:
   raw=stream.read(1048577);after=os.fstat(stream.fileno())
  fields=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_nlink)
  if fields(before)!=fields(after) or fields(before)!=fields(helper.stat()) or hashlib.sha256(raw).hexdigest()!=BOOTSTRAP_SHA256:raise ValueError()
  # Execute the admitted bytes, rather than reopening a path for an importer.
  namespace={'__name__':'_unified_protected_bootstrap','__file__':str(helper)}
  exec(compile(raw,str(helper),'exec'),namespace)
  grant=namespace['read_protected_activation'](entry.parents[4])
  if len(args)==2:return namespace['run_protected_module'](grant,args[1],verify_only=args[0]=='--verify-module-source')
  if args:return namespace['run_protected_data_first'](grant,worker=args[0]=='--data-first-worker')
  return namespace['run_protected_runtime'](grant)
 except Exception:
  print('BLOCKED_SERVICE_ACTIVATION')
  return 78


if __name__=='__main__':raise SystemExit(main())
