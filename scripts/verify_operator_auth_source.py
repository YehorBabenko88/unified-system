"""Explicit ephemeral-hosted negative qualification, never an auth factory."""
import argparse
import ctypes
import hashlib
import json
import os
import re
import stat
from pathlib import Path
import subprocess
import tempfile


def validate_receipt(value):
 expected=dict(schema='unified.native-subject-negative.v1',compile='PASS',invalid_context='REJECTED',
               subject_extraction_positive='NOT_RUN',tls_cbt='NOT_QUALIFIED',
               runtime_factory='DENY',authentication='NOT_QUALIFIED',
               negative_cases=['ABSENT_OWNER','OUTBOUND_OWNER','EMPTY_CONTEXT','NATIVE_INVALID_CONTEXT','EMPTY_GENERATION'],
               native_invalid_handle_observed=True)
 if type(value) is not dict or value!=expected or type(value.get('native_invalid_handle_observed')) is not bool:raise ValueError('NATIVE_SUBJECT_EVIDENCE_REJECTED')
 return dict(value)


def verify_source(root,expected):
 root=Path(root).resolve()
 if type(expected) is not str or re.fullmatch('[a-f0-9]{40}',expected) is None:raise ValueError('SOURCE_HEAD_INVALID')
 env=os.environ.copy()
 env.update(GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL=os.devnull,GIT_CONFIG_COUNT='0',GIT_NO_REPLACE_OBJECTS='1')
 for key in ('GIT_DIR','GIT_WORK_TREE','GIT_INDEX_FILE','GIT_OBJECT_DIRECTORY','GIT_ALTERNATE_OBJECT_DIRECTORIES'):env.pop(key,None)
 def git(*args):return subprocess.check_output(['git','-c','core.fsmonitor=false',*args],cwd=root,env=env,timeout=10)
 if git('rev-parse','HEAD').decode().strip()!=expected or git('rev-parse','--show-object-format').strip()!=b'sha1':
  raise ValueError('SOURCE_HEAD_MISMATCH')
 tracked=set();total=0
 for entry in filter(None,git('ls-tree','-r','-z','HEAD').split(b'\0')):
  meta,name=entry.split(b'\t',1);mode,kind,oid=meta.split();relative=Path(name.decode('utf-8'))
  if mode not in (b'100644',b'100755') or kind!=b'blob' or relative.is_absolute() or '..' in relative.parts:
   raise ValueError('SOURCE_ENTRY_INVALID')
  file=root/relative
  for item in (file,*file.parents):
   if item==root.parent:break
   info=item.lstat()
   if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&1024:raise ValueError('SOURCE_LINK_REJECTED')
  if not file.is_file() or file.stat().st_size>16*1024**2:raise ValueError('SOURCE_BOUND')
  data=file.read_bytes();total+=len(data);tracked.add(relative.as_posix())
  if total>256*1024**2 or len(tracked)>10000:raise ValueError('SOURCE_BOUND')
  if hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()!=oid.decode():
   raise ValueError('SOURCE_RAW_BLOB_MISMATCH')
 observed=0
 for folder,dirs,names in os.walk(root,followlinks=False):
  dirs[:]=[name for name in dirs if not (Path(folder)==root and name=='.git')]
  for name in (*dirs,*names):
   file=Path(folder)/name;relative=file.relative_to(root).as_posix();observed+=1
   if observed>20000:raise ValueError('SOURCE_SCAN_BOUND')
   info=file.lstat()
   if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&1024:raise ValueError('SOURCE_LINK_REJECTED')
   if stat.S_ISREG(info.st_mode) and relative!='.git' and relative not in tracked:raise ValueError('SOURCE_UNEXPECTED_FILE')
 return dict(head=expected,tree=git('rev-parse','HEAD^{tree}').decode().strip(),raw_blobs=len(tracked),raw_bytes=total)


def qualify(output,expected):
 if (os.name!='nt' or os.environ.get('GITHUB_ACTIONS')!='true'
     or os.environ.get('RUNNER_ENVIRONMENT')!='github-hosted'):
  raise ValueError('EPHEMERAL_HOSTED_WINDOWS_ONLY')
 # These environment checks restrict this test launcher. They confer no runtime
 # authority and do not attest a native authentication or TLS implementation.
 kernel=ctypes.WinDLL('kernel32',use_last_error=True)
 function=kernel.GetSystemDirectoryW;function.argtypes=[ctypes.c_wchar_p,ctypes.c_uint];function.restype=ctypes.c_uint
 buffer=ctypes.create_unicode_buffer(32768);length=function(buffer,len(buffer))
 if not 0<length<len(buffer):raise ValueError('SYSTEM_DIRECTORY_UNAVAILABLE')
 compiler=Path(buffer.value).resolve().parent/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
 root=Path(__file__).resolve().parents[1]
 output=Path(output).resolve()
 if root in output.parents:raise ValueError('EVIDENCE_OUTSIDE_SOURCE_REQUIRED')
 before_source=verify_source(root,expected)
 output.write_text(json.dumps(dict(scope='HOSTED_COMPILE_AND_INVALID_CONTEXT_ONLY',
     source_before=before_source,result='RUNNING',authentication='NOT_QUALIFIED'),indent=2))
 sources=[root/'native/operator-auth/CompletedContextSubject.cs',root/'native/operator-auth/CompletedContextSubject.Tests.cs']
 digest=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
 before={str(path.relative_to(root)):digest(path) for path in sources};compiler_pin=digest(compiler)
 report=dict(source_sha256=before,compiler_sha256=compiler_pin,
             scope='HOSTED_COMPILE_AND_INVALID_CONTEXT_ONLY',physical='NOT_RUN',
             source_before=before_source,authentication='NOT_QUALIFIED',result='RUNNING',
             run_id=os.environ.get('GITHUB_RUN_ID'),attempt=os.environ.get('GITHUB_RUN_ATTEMPT'))
 try:
  with tempfile.TemporaryDirectory(prefix='native-subject-negative-') as folder:
   executable=Path(folder).resolve()/'NativeSubjectNegative.exe'
   compiled=subprocess.run([str(compiler),'/nologo','/target:exe','/out:'+str(executable),*map(str,sources)],capture_output=True,timeout=30)
   if compiled.returncode!=0 or len(compiled.stdout)+len(compiled.stderr)>8192:
    raise ValueError('NATIVE_SUBJECT_COMPILE_FAILED')
   child=subprocess.run([str(executable)],capture_output=True,timeout=15)
   if child.returncode!=0 or child.stderr or len(child.stdout)>2048:raise ValueError('NATIVE_SUBJECT_NEGATIVE_FAILED')
   report['receipt']=validate_receipt(json.loads(child.stdout))
  if before!={str(path.relative_to(root)):digest(path) for path in sources} or compiler_pin!=digest(compiler):
   raise ValueError('NATIVE_SUBJECT_INPUT_CHANGED')
  report['result']='COMPILE_NEGATIVES_VERIFIED'
 except BaseException as error:
  report['result']='FAILED';report['failure_class']=type(error).__name__
  raise
 finally:
  try:report['source_after']=verify_source(root,expected)
  except BaseException:
   report['result']='FAILED';report['source_after_error']='SOURCE_VERIFICATION_FAILED'
   raise
  finally:output.write_text(json.dumps(report,indent=2))



if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--execute-ephemeral-hosted-negative-only',action='store_true',required=True)
 parser.add_argument('--output',required=True)
 parser.add_argument('--expected-source',required=True)
 args=parser.parse_args();qualify(args.output,args.expected_source)
