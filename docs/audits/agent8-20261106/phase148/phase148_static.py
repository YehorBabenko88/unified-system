import pathlib,subprocess,io,ast,json,hashlib
r=pathlib.Path.cwd();p=r/'work/review-audit69-e203';o=r/'outputs/phase148';o.mkdir(exist_ok=True);before='9f55260f1e3c0ff83512bbd307a6ccc3366a386e'
def git(*args,data=None):return subprocess.check_output(['git','-C',str(p),*args],input=data)
assert git('show','-s','--format=%T','HEAD').decode().strip()=='7ca3b471eb7ee2411eb83da68f8e068ee42c803c';rows=[]
for row in git('ls-tree','-rz','HEAD').split(b'\0'):
 if row:
  meta,name=row.split(b'\t',1);rows.append((name.decode(),meta.split()[2]))
s=io.BytesIO(git('cat-file','--batch',data=b''.join(oid+b'\n' for _,oid in rows)))
for name,oid in rows:
 actual,kind,size=s.readline().split();raw=s.read(int(size));assert s.read(1)==b'\n' and actual==oid;(p/name).write_bytes(raw)
t=ast.parse((r/'work/phase121_qualify.py').read_text());fn=next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=='inventory');ns={};exec('import pathlib,subprocess,os,hashlib,json,io',ns);exec(compile(ast.Module(body=[fn],type_ignores=[]),'<inventory>','exec'),ns);inventory=ns['inventory'](p)
changes=git('diff','--name-only',before,'HEAD').decode().splitlines();assert set(changes)=={'tools/physical_dev/bootstrap.py','tests/physical_dev/test_bootstrap_contract.py','docs/physical-dev/LS5-SMOKE-SOURCE-REVIEW.md'};(o/'exact-source-diff.patch').write_bytes(git('diff',before,'HEAD'))
raw=(p/'tools/physical_dev/bootstrap.py').read_bytes();tree=ast.parse(raw);functions={n.name:dict(line=n.lineno,source=ast.unparse(n)) for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['source_git_argv','validate_source_git_audit','main']};hashes={'bootstrap.py':hashlib.sha256(raw).hexdigest()}
old=ast.parse(git('show',before+':tools/physical_dev/bootstrap.py'));priorfn=next(n for n in old.body if isinstance(n,ast.FunctionDef) and n.name=='source_git_argv');nowfn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='source_git_argv');assert ast.dump(priorfn,include_attributes=False)==ast.dump(nowfn,include_attributes=False)
for f in ['ls5_smoke.py','supervisor.py','package.py','assembly.py','materialize.py','export_git.py']:
 raw=(p/'tools/physical_dev'/f).read_bytes();assert raw==git('show',before+':tools/physical_dev/'+f);hashes[f]=hashlib.sha256(raw).hexdigest()
assert git('show','HEAD:unified_system/gateway_target_adapter.py')==git('show',before+':unified_system/gateway_target_adapter.py')
(o/'source-verification.json').write_text(json.dumps(dict(head='e203c0bbeaa176a843a7d80b2eadfefe8fce7385',tree='7ca3b471eb7ee2411eb83da68f8e068ee42c803c',changed_files=changes,hashes=hashes,functions=functions,primary_raw=inventory,noextras=True,fixed_six_arg_source_validator_AST_unchanged=True,target_adapter_unchanged=True,A8_helper_imports_or_fixture_tests=0,A8_native_Job_SDK_browser_calls=0,result='SOURCE_ONLY_F35_CORRECTION_ACK_NOT_RUNTIME_PROOF'),indent=2));print(len(inventory),'rawprimary/noextras;3pathdiff; sourceonly')
