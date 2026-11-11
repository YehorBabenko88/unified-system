import pathlib,json,hashlib,os,stat,subprocess,io,time,collections
r=pathlib.Path.cwd();o=r/'outputs/phase157';o.mkdir(exist_ok=True);base=pathlib.Path('C:/Users/LS-5/.codex/native-e2e-evidence-20261109');root=base/'ls5-package-1d923f6-g'
def sha(b):return hashlib.sha256(b).hexdigest()
refs={}
for name,expected in [('ls5-package-1d9-g.manifest.json','3e05c5251d0bd84e073dc0545c95c903424654690942bd77313175ae493b0a5a'),('ls5-package1d9-g.activation-plan.json','de66e55609af940649803c8fd2f5aeadd7a10a7d7c85b0e351845e861f2e68fd'),('ls5-package-1d9-g.copy-receipt.json','e58a1c26ab399c73762e6672e13d1df13780f6138903f6d37c8b6a8ea4c159c7')]:
 raw=(base/name).read_bytes();assert sha(raw)==expected;refs[name]=dict(bytes=len(raw),sha256=sha(raw));(o/name).write_bytes(raw)
m=json.loads((base/'ls5-package-1d9-g.manifest.json').read_bytes());a=json.loads((base/'ls5-package1d9-g.activation-plan.json').read_bytes());files=m['files'];assert len(files)==m['file_count']==19300
start=time.monotonic();actual={};total=0;directories=0
for current,dirs,names in os.walk(root,followlinks=False):
 for name in dirs+names:
  p=pathlib.Path(current)/name;s=p.lstat();assert not (getattr(s,'st_file_attributes',0)&1024) and not stat.S_ISLNK(s.st_mode)
  if stat.S_ISDIR(s.st_mode):directories+=1;continue
  assert stat.S_ISREG(s.st_mode) and s.st_nlink==1;rel=p.relative_to(root).as_posix();assert rel in files
  h=hashlib.sha256()
  with p.open('rb') as stream:
   before=os.fstat(stream.fileno());assert before.st_ino==s.st_ino and before.st_dev==s.st_dev
   for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
   after=os.fstat(stream.fileno())
  final=p.lstat();assert (before.st_ino,before.st_size,before.st_mtime_ns)==(after.st_ino,after.st_size,after.st_mtime_ns)==(final.st_ino,final.st_size,final.st_mtime_ns)
  assert files[rel]==dict(bytes=s.st_size,sha256=h.hexdigest());actual[rel]=files[rel];total+=s.st_size
assert set(actual)==set(files) and total==m['total_bytes']==1008702257
source_results=[]
clones={'runtime-unified':r/'work/review-ci-b144','harness':r/'work/review-ci-b144','strattester':r/'work/review7-strattester','meta_analyse':r/'work/review7-meta_analyse','terminan':r/'work/review-render77-161'}
for ref in m['source_metadata']['sources']:
 clone=clones[ref['name']];commit=ref['commit'];prefix='sources/'+ref['name']+'/'
 def git(*args,data=None):return subprocess.check_output(['git','--no-replace-objects','-C',str(clone),*args],input=data)
 assert git('show','-s','--format=%T',commit).decode().strip()==ref['tree'];rows=[]
 for row in git('ls-tree','-rz',commit).split(b'\0'):
  if row:
   meta,name=row.split(b'\t',1);mode,kind,oid=meta.split();assert kind==b'blob';rows.append((name.decode(),oid))
 stream=io.BytesIO(git('cat-file','--batch',data=b''.join(oid+b'\n' for _,oid in rows)))
 for name,oid in rows:
  obj,kind,size=stream.readline().split();raw=stream.read(int(size));assert stream.read(1)==b'\n' and obj==oid and hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest().encode()==oid
  assert files[prefix+name]==dict(bytes=len(raw),sha256=sha(raw))
 extras=[k[len(prefix):] for k in files if k.startswith(prefix) and k[len(prefix):] not in {n for n,_ in rows}];assert all(x.startswith('.git/') for x in extras)
 source_results.append(dict(**ref,primary_files=len(rows),extra_git_metadata_files=len(extras),primary_raw_matches=True))
assert a['manifest_sha256']==refs['ls5-package-1d9-g.manifest.json']['sha256'] and a['shell'] is False and a['argv'][-1]=='--execute'
controller=pathlib.Path(a['argv'][4]);assert controller.read_bytes()==(root/'sources/harness/tools/physical_dev/ls5_smoke.py').read_bytes();assert sha(pathlib.Path(a['argv'][0]).read_bytes())==a['parent_python_sha256'];assert not pathlib.Path(a['state_path']).exists()
sdkmap={k.removeprefix('tooling/node_modules/'):v['sha256'] for k,v in files.items() if k.startswith('tooling/node_modules/')};sdksha=sha(json.dumps(sdkmap,sort_keys=True,separators=(',',':')).encode())
result=dict(scope='READ_ONLY_STDLIB_HASH_GIT_OBJECT_SOURCE_REVIEW_NO_PROJECT_IMPORT_OR_HELPER_JOB_SDK_PHYSICAL_CALL',references=refs,file_count=len(actual),total_bytes=total,directories=directories,ordinary_single_link_no_reparse=True,elapsed_seconds=time.monotonic()-start,sources=source_results,controller_matches_packaged_harness=True,parent_python_file_pin_matches=True,state_absent=True,sdk_file_count=len(sdkmap),sdk_map_sha256=sdksha,cleanup_budget='SOURCE_1D9_TERM2AB_RESOLVER_REVIEWED_RUNTIME_NOT_RUN',execution_admission=False)
(o/'read-only-package-verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
