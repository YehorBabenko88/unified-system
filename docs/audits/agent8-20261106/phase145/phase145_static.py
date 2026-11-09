import pathlib,subprocess,io,ast,json,hashlib
r=pathlib.Path.cwd();p=r/'work/review-stand69-9f';o=r/'outputs/phase145';before='453cb6d60efbdb8a34a7237053d69b6d631ed488'
def git(*args,data=None):return subprocess.check_output(['git','-C',str(p),*args],input=data)
assert git('show','-s','--format=%T','HEAD').decode().strip()=='c928bffb862bcb557d8fb8312c7c1f2dde6559b8';rows=[]
for row in git('ls-tree','-rz','HEAD').split(b'\0'):
 if row:
  meta,name=row.split(b'\t',1);rows.append((name.decode(),meta.split()[2]))
s=io.BytesIO(git('cat-file','--batch',data=b''.join(oid+b'\n' for _,oid in rows)))
for name,oid in rows:
 actual,kind,size=s.readline().split();raw=s.read(int(size));assert s.read(1)==b'\n' and actual==oid;(p/name).write_bytes(raw)
t=ast.parse((r/'work/phase121_qualify.py').read_text());fn=next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=='inventory');ns={};exec('import pathlib,subprocess,os,hashlib,json,io',ns);exec(compile(ast.Module(body=[fn],type_ignores=[]),'<inventory>','exec'),ns);inventory=ns['inventory'](p)
changed=git('diff','--name-only',before,'HEAD').decode().splitlines();assert len(changed)==6
diff=git('diff',before,'HEAD');(o/'exact-source-diff.patch').write_bytes(diff);functions={};hashes={}
for file,names in [('bootstrap.py',['allocate_stand_root','main']),('ls5_smoke.py',['launch','execute']),('supervisor.py',['WindowsSmokeJob'])]:
 raw=(p/'tools/physical_dev'/file).read_bytes();hashes[file]=hashlib.sha256(raw).hexdigest();tree=ast.parse(raw)
 for n in tree.body:
  if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names:functions[file+':'+n.name]=dict(line=n.lineno,source=ast.unparse(n))
for file in ['package.py','assembly.py','materialize.py','export_git.py']:
 raw=(p/'tools/physical_dev'/file).read_bytes();assert raw==git('show',before+':tools/physical_dev/'+file);hashes[file]=hashlib.sha256(raw).hexdigest()
assert git('show','HEAD:unified_system/gateway_target_adapter.py')==git('show',before+':unified_system/gateway_target_adapter.py')
(o/'source-verification.json').write_text(json.dumps(dict(head='9f55260f1e3c0ff83512bbd307a6ccc3366a386e',tree='c928bffb862bcb557d8fb8312c7c1f2dde6559b8',changed_files=changed,hashes=hashes,functions=functions,primary_raw=inventory,noextras=True,unified_target_adapter_unchanged=True,helper_imports=0,A8_fixtures_or_tests=0,native_Job_SDK_browser_calls=0,result='F33_F34_SOURCE_CORRECTION_ACK_SCOPED_NOT_RUNTIME_PROOF'),indent=2));print(len(inventory),'raw primary matched; six-file static review only')
