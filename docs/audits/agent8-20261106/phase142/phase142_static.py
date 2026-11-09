import subprocess,pathlib,io,ast,json,hashlib
r=pathlib.Path.cwd();p=r/'work/review-cleanup69-453';o=r/'outputs/phase142';rows=[]
def git(*args,data=None):return subprocess.check_output(['git','-C',str(p),*args],input=data)
assert git('show','-s','--format=%T','HEAD').decode().strip()=='31c70d248c5c1bd4ced335c8a1b437d592dc5b12'
for row in git('ls-tree','-rz','HEAD').split(b'\0'):
 if row:
  meta,name=row.split(b'\t',1);rows.append((name.decode(),meta.split()[2]))
s=io.BytesIO(git('cat-file','--batch',data=b''.join(oid+b'\n' for _,oid in rows)))
for name,oid in rows:
 actual,kind,size=s.readline().split();raw=s.read(int(size));assert s.read(1)==b'\n' and actual==oid
 (p/name).write_bytes(raw)
t=ast.parse((r/'work/phase121_qualify.py').read_text());fn=next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=='inventory');ns={};exec('import pathlib,subprocess,os,hashlib,json,io',ns);exec(compile(ast.Module(body=[fn],type_ignores=[]),'<inventory>','exec'),ns);inventory=ns['inventory'](p)
changes=git('diff','--name-only','461ee1d51f432dc1ccf419f22fd7c1cd41095a8e','HEAD').decode().splitlines();assert len(changes)==4
diff=git('diff','461ee1d51f432dc1ccf419f22fd7c1cd41095a8e','HEAD');(o/'exact-source-diff.patch').write_bytes(diff)
functions={};hashes={}
for file,names in [('ls5_smoke.py',['cleanup_seconds','retire_unassigned','Capture','execute']),('supervisor.py',['OwnWatchdog','WindowsSmokeJob'])]:
 raw=(p/'tools/physical_dev'/file).read_bytes();hashes[file]=hashlib.sha256(raw).hexdigest();tree=ast.parse(raw)
 for n in tree.body:
  if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names:functions[file+':'+n.name]=dict(line=n.lineno,source=ast.unparse(n))
for file in ['bootstrap.py','package.py','assembly.py','materialize.py','export_git.py']:
 raw=(p/'tools/physical_dev'/file).read_bytes();prior=git('show','461ee1d51f432dc1ccf419f22fd7c1cd41095a8e:tools/physical_dev/'+file);assert raw==prior;hashes[file]=hashlib.sha256(raw).hexdigest()
(o/'source-verification.json').write_text(json.dumps(dict(head='453cb6d60efbdb8a34a7237053d69b6d631ed488',tree='31c70d248c5c1bd4ced335c8a1b437d592dc5b12',changed_files=changes,hashes=hashes,functions=functions,primary_raw=inventory,noextras=True,helper_imports=0,app_or_fault_tests=0,physical_calls=0,result='SOURCE_ONLY_F32_CORRECTION_ACK_NOT_RUNTIME_PROOF'),indent=2));print('primary raw',len(inventory),'source review only')
