import hashlib,io,json,os,pathlib,stat,subprocess,threading,time
root=pathlib.Path('C:/Users/LS-5/.codex/terminan-disposal-aa9b4e9-red-qualified')
out=pathlib.Path('C:/Users/LS-5/.codex/terminan-disposal-red-evidence-20261110');out.mkdir(exist_ok=False)
head='aa9b4e9328382c885ca3cf0cc9b66e6abf1ffe74'
node=pathlib.Path('C:/Program Files/nodejs/node.exe')
for path in [*reversed(node.parents),node]:
 info=path.lstat();assert not path.is_symlink() and not getattr(info,'st_file_attributes',0)&1024
 assert (stat.S_ISREG(info.st_mode) and info.st_nlink==1) if path==node else stat.S_ISDIR(info.st_mode)
assert hashlib.sha256(node.read_bytes()).hexdigest()=='d702daa815eabbff763c7d3808e235cf031cf2ca70211b56847bc72f51e240e5'
def git(*args,data=None):
 return subprocess.check_output(['C:/Program Files/Git/cmd/git.exe','--no-replace-objects','--no-optional-locks','-c','core.fsmonitor=false',*args],input=data,cwd=root,timeout=30)
assert git('rev-parse','HEAD').decode().strip()==head
def snapshot():
 entries=[];dirs=set();result={}
 for row in git('ls-tree','-rz','--full-tree',head).split(b'\0'):
  if row:
   meta,name=row.split(b'\t');mode,kind,oid=meta.split();assert kind==b'blob' and mode in (b'100644',b'100755');entries.append((name.decode(),oid.decode()))
 for name,oid in entries:dirs.update(str(x) for x in pathlib.PurePosixPath(name).parents if str(x)!='.')
 for name in sorted(dirs,key=lambda x:x.count('/')):
  path=root/name;s=path.lstat();assert stat.S_ISDIR(s.st_mode) and not path.is_symlink() and not getattr(s,'st_file_attributes',0)&1024
 stream=io.BytesIO(git('cat-file','--batch',data=''.join(oid+'\n' for _,oid in entries).encode()))
 for name,oid in entries:
  actual,kind,size=stream.readline().split();raw=stream.read(int(size));assert actual.decode()==oid and kind==b'blob' and stream.read(1)==b'\n'
  path=root/name;s=path.lstat();assert stat.S_ISREG(s.st_mode) and s.st_nlink==1 and not path.is_symlink() and not getattr(s,'st_file_attributes',0)&1024 and path.read_bytes()==raw
  result[name]=hashlib.sha256(raw).hexdigest()
 assert not stream.read()
 for path in root.rglob('*'):
  rel=path.relative_to(root)
  if rel.parts[0]=='.git':continue
  s=path.lstat();assert not path.is_symlink() and not getattr(s,'st_file_attributes',0)&1024
  assert rel.as_posix() in (result if path.is_file() else dirs)
 return result
before=snapshot()
assert before['tests/test_preview_benchmark_disposal.cjs']=='0ad02bc7f756300de21aac34036be27881cc23038a3f6e2500318ebace81d57a'
expected={
 'terminan/r2_preview.js':'dd9853da97b0533e34c6bc0e7b3d7d252e71c46613f57f4045a989d14726c0e3',
 'terminan/r4_preview.js':'c3ab606cfcffdfb87d8e2a7fada6aa15f5bf4082f114fb10c87ff03b6947eb7d',
 'terminan/r4_protocol.js':'99b4f3f31710594637f005034ff36f655ce89c12a0e33a2ad218545bbf73eb54'}
assert all(before[k]==v for k,v in expected.items())
argv=[str(node),'--no-addons','--test','--test-isolation=none','--test-concurrency=1','--test-reporter=tap','tests/test_preview_benchmark_disposal.cjs']
env={k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR','SYSTEMDRIVE','TEMP','TMP','USERPROFILE','LOCALAPPDATA','APPDATA'}}
pieces=[];reader_errors=[];overflow=threading.Event();started=time.monotonic()
child=subprocess.Popen(argv,cwd=root,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
def consume():
 size=0
 try:
  while True:
   chunk=child.stdout.read(4096)
   if not chunk:break
   size+=len(chunk)
   if size>256*1024:
    overflow.set();child.kill();break
   pieces.append(chunk)
 except BaseException as error:reader_errors.append(type(error).__name__)
thread=threading.Thread(target=consume,daemon=True);thread.start();timed_out=False
try:code=child.wait(timeout=15)
except subprocess.TimeoutExpired:
 timed_out=True;child.kill();code=child.wait(timeout=5)
thread.join(timeout=2)
retired=child.poll() is not None and not thread.is_alive()
node_elapsed=time.monotonic()-started
if retired:child.stdout.close()
raw=b''.join(pieces);(out/'node-original.tap').write_bytes(raw)
after=snapshot();text=raw.decode('utf-8')
ids=[kind+'_'+name for kind in ('r2','r4') for name in ('metrics_count_held_benchmark_raf','dispose_settles_held_benchmark_without_frame','seek_settles_superseded_benchmark_without_frame')]
record=dict(scope='LOCAL_ACTUAL_JS_FAKE_DOM_RAF_OLD_SOURCE_RED_ONLY',head=head,tree=git('rev-parse','HEAD^{tree}').decode().strip(),source_before=before,source_after=after,node_sha256=hashlib.sha256(node.read_bytes()).hexdigest(),node_version_metadata='24.22.1',argv=argv,pid=child.pid,returncode=code,node_elapsed_seconds=node_elapsed,node_timeout=timed_out,output_overflow=overflow.is_set(),reader_errors=reader_errors,direct_node_and_reader_retired=retired,expected_ids=ids,actual_test_summary=[line for line in text.splitlines() if line.startswith(('# tests','# pass','# fail','# skipped','ok ','not ok '))],log_sha256=hashlib.sha256(raw).hexdigest(),test_isolation='none',unit_source_spawns_no_children=True,global_os_process_custody_claim=False,native_authority=False,physical_acceptance=False,provider_sends=False,public_submit='DENY')
(out/'receipt.json').write_bytes((json.dumps(record,indent=2)+'\n').encode())
assert before==after and retired and not timed_out and not overflow.is_set() and not reader_errors
assert '# tests 6' in text and '# skipped 0' in text
assert all(('# Subtest: '+name) in text for name in ids)
print(json.dumps({k:record[k] for k in ('head','returncode','node_elapsed_seconds','direct_node_and_reader_retired','actual_test_summary','log_sha256')}))
