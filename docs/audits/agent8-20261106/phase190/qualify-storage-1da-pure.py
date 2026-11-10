import hashlib, io, json, pathlib, subprocess, sys, threading, unittest
root=pathlib.Path('C:/Users/LS-5/.codex/storage-1da106-qualified')
expected='1da10616a2b8217930f354e17caaa6fcea22dac4'
def git(*args,data=None):
 return subprocess.check_output(['C:/Program Files/Git/cmd/git.exe','--no-replace-objects','--no-optional-locks','-c','core.fsmonitor=false',*args],cwd=root,input=data,timeout=30)
assert git('rev-parse','HEAD').decode().strip()==expected
def snapshot():
 entries=[]
 for row in git('ls-tree','-rz','--full-tree',expected).split(b'\0'):
  if row:
   meta,name=row.split(b'\t',1);mode,kind,oid=meta.split();assert kind==b'blob' and mode in (b'100644',b'100755');entries.append((name.decode(),oid.decode()))
 stream=io.BytesIO(git('cat-file','--batch',data=''.join(oid+'\n' for _,oid in entries).encode()));result={};dirs=set()
 for name,oid in entries:
  actual,kind,size=stream.readline().split();raw=stream.read(int(size));assert actual.decode()==oid and kind==b'blob' and stream.read(1)==b'\n'
  p=root/name;s=p.lstat();assert s.st_nlink==1 and not p.is_symlink() and not getattr(s,'st_file_attributes',0)&1024 and p.read_bytes()==raw
  result[name]=hashlib.sha256(raw).hexdigest();dirs.update(x.as_posix() for x in pathlib.PurePosixPath(name).parents if x.as_posix()!='.')
 assert not stream.read()
 for path in root.rglob('*'):
  rel=path.relative_to(root)
  if rel.parts[0]=='.git':continue
  assert not path.is_symlink() and not getattr(path.lstat(),'st_file_attributes',0)&1024
  assert rel.as_posix() in (result if path.is_file() else dirs)
 return result
b=pathlib.Path('C:/Users/LS-5/.codex/ci-boundary-evidence-20261110')
before=snapshot();import os,runpy
out=b/'storage-1da-pure-owned-output';assert not out.exists();os.environ['A4_RESULT_EVIDENCE']=str(out)
namespace=runpy.run_path(str(root/'tests/storage/native_publication/qualify.py'),run_name='root_a4_qualifier_pure_only')
controls=runpy.run_path(str(root/'tests/storage/native_publication/inventory_controls.py'),run_name='root_a4_inventory_controls_only')
suite=controls['make_suite'](namespace['validate_inventory'],(namespace['ORIGINAL_REQUIRED'],namespace['FIXED_PACKET_REQUIRED']));assert suite.countTestCases()==6
r=unittest.TextTestRunner(verbosity=2).run(suite);after=snapshot();threads=[t.name for t in threading.enumerate() if t is not threading.main_thread()]
assert r.wasSuccessful() and not r.skipped and before==after and not threads
receipt=dict(head=expected,tree=git('rev-parse','HEAD^{tree}').decode().strip(),scope='FRESH_SOURCE_6_STORAGE_INVENTORY_CONTROLS_ONLY',tests=r.testsRun,skips=len(r.skipped),source_before=before,source_after=after,threads_alive=threads,actual_22_storage_fixture_cases_executed=False,source_checking_git_subprocesses_used=True,native_authority=False,physical_execution=False,public_submit='DENY')
path=pathlib.Path('C:/Users/LS-5/.codex/ci-boundary-evidence-20261110/storage-1da-pure-receipt.json');path.write_bytes((json.dumps(receipt,sort_keys=True,indent=2)+'\n').encode())
print(json.dumps(dict(head=expected,tests=6,files=len(before),source_equal=before==after,receipt_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),scope=receipt['scope'])))
