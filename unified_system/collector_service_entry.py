"""Raw Collector service gate. No developer CLI or execution fallback."""
import sys

BOOTSTRAP_SHA256='6d3be096e0df7d7633b14b55ec9d049e25b537bb530ba17f995c10a357b85005'

def _load_bootstrap():
 import hashlib,os,stat,ctypes
 from pathlib import Path
 if os.name!='nt':raise ValueError()
 entry=Path(__file__).absolute();path=entry.with_name('collector_service_bootstrap.py')
 if not entry.is_absolute() or str(entry).startswith(('//',chr(92))) or '..' in entry.parts:raise ValueError()
 api=ctypes.WinDLL('kernel32',use_last_error=True);api.GetDriveTypeW.argtypes=[ctypes.c_wchar_p];api.GetDriveTypeW.restype=ctypes.c_uint
 if api.GetDriveTypeW(str(entry)[:3])!=3:raise ValueError()
 for item in (*reversed(path.parents),path):
  info=item.lstat()
  if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&1024:raise ValueError()
 before=path.stat()
 if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or not 0<before.st_size<=1048576:raise ValueError()
 with path.open('rb') as stream:raw=stream.read(1048577);after=os.fstat(stream.fileno())
 fields=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_nlink)
 if fields(before)!=fields(after) or fields(before)!=fields(path.stat()) or hashlib.sha256(raw).hexdigest()!=BOOTSTRAP_SHA256:raise ValueError()
 namespace={'__name__':'_collector_protected_bootstrap','__file__':str(path)}
 exec(compile(raw,str(path),'exec'),namespace);return namespace,entry.parents[4]

def main(argv=None):
 try:
  args=sys.argv[1:] if argv is None else argv
  if type(args) is not list or args not in ([],['--collector-worker']):raise ValueError()
  if not (sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode):raise ValueError()
  namespace,root=_load_bootstrap()
  grant=namespace['read_protected_collector_activation'](root)
  # Both accepted forms still deny until a real operational/runtime adapter is
  # reviewed. The worker spelling never reaches the developer offline CLI.
  return namespace['run_protected_collector'](grant)
 except Exception:
  print('BLOCKED_COLLECTOR_SERVICE_ACTIVATION');return 78

if __name__=='__main__':raise SystemExit(main())
