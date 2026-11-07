import pathlib,subprocess,hashlib,io,json,sys,unittest,os
ROOT=pathlib.Path(__file__).resolve().parents[2];REPO=ROOT/'work/review-nativepeer-f58e';OUT=ROOT/'outputs/phase82';PRIVATE=ROOT/'work/nativepeer-a8-private';HEAD='f58e68b5893b353bd9a7438c0843cd68ec200b19'
def source():
 def g(*a,data=None):return subprocess.check_output(['git','--no-replace-objects','-C',str(REPO),*a],input=data)
 assert g('rev-parse','HEAD').decode().strip()==HEAD
 entries=[]
 for row in g('ls-tree','-rz','HEAD').split(b'\0'):
  if row:
   meta,name=row.split(b'\t',1);mode,kind,oid=meta.split();assert mode in (b'100644',b'100755') and kind==b'blob';entries.append((name.decode(),oid.decode()))
 stream=io.BytesIO(g('cat-file','--batch',data=''.join(oid+'\n' for _,oid in entries).encode()));files={}
 for name,oid in entries:
  actual,kind,size=stream.readline().split();b=stream.read(int(size));assert stream.read(1)==b'\n' and actual.decode()==oid and hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==oid
  path=REPO/name;assert path.read_bytes()==b and not path.is_symlink() and path.stat().st_nlink==1;files[name]=hashlib.sha256(b).hexdigest()
 for path in REPO.rglob('*'):
  rel=path.relative_to(REPO)
  if rel.parts[0]=='.git':continue
  assert not path.is_symlink() and not getattr(path.lstat(),'st_file_attributes',0)&1024 and path.suffix not in ('.pyc','.pyo')
  if path.is_file():assert rel.as_posix() in files
 return dict(head=HEAD,tree=g('rev-parse','HEAD^{tree}').decode().strip(),raw_files=files)
def main():
 assert sys.version_info[:3]==(3,12,10) and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode and sys.pycache_prefix is None
 OUT.mkdir(exist_ok=True);before=source();assert before['tree']=='c79f3e15a30fe3d4f1d94629fbcab2fd8c99fd18'
 sys.path[:0]=[str(REPO),str(REPO/'tests')];import test_native_peer_identity as tests
 suite=unittest.defaultTestLoader.loadTestsFromModule(tests)
 def ids(s):
  rows=[]
  for item in s:rows.extend(ids(item) if isinstance(item,unittest.TestSuite) else [item.id()])
  return rows
 selected=ids(suite);assert len(selected)==len(set(selected))==19
 with (PRIVATE/'tests19.original.log').open('w',encoding='utf-8') as log:result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
 failed={t.id() for t,_ in result.failures};errors={t.id() for t,_ in result.errors}
 (OUT/'tests19.log').write_text('\n'.join(('FAIL' if i in failed else 'ERROR' if i in errors else 'PASS')+' '+i for i in selected)+'\nRaw original log PRIVATE_LOCAL_ONLY\n',encoding='utf-8')
 after=source();assert before==after
 raw=(json.dumps(tests.NATIVE_RESULTS,indent=2)+'\n').encode();(PRIVATE/'native-results.original.json').write_bytes(raw)
 sanitized=[]
 for row in tests.NATIVE_RESULTS:
  allowed={k:v for k,v in row.items() if k in ['case','status','code','level','server_identity_restored','runtime_admission','owned_client_stopped','own_helper_failfast_exit']}
  ctx=row.get('context',{});allowed['handle_counts']={k:v for k,v in ctx.items() if k in ['capture_handles_before','capture_handles_after']};allowed['context_raw_private_only']=True;sanitized.append(allowed)
 report=dict(head=HEAD,tree=before['tree'],python=sys.version,source_before=before,source_after=after,tests=selected,count=result.testsRun,skips=len(result.skipped),errors=len(result.errors),failures=len(result.failures),native_cases=sanitized,raw_native_results_sha256=hashlib.sha256(raw).hexdigest(),raw_native_results_privacy='PRIVATE_LOCAL_ONLY',qualification='ISOLATED_OWNED_PIPE_OBSERVATION_ONLY',production_factory='BLOCKED',runtime_authentication=False,TLS_certificates='NOT_RUN',Gateway_runtime_matrix='UNCHANGED_BLOCKED',physical='NOT_RUN')
 (OUT/'source-bound.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(dict(count=result.testsRun,skips=len(result.skipped),errors=len(result.errors),failures=len(result.failures),raw_files=len(before['raw_files']),native_results=len(sanitized))))
 assert result.wasSuccessful() and result.testsRun==19 and not result.skipped
if __name__=='__main__':main()
