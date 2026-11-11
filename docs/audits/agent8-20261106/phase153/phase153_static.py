import pathlib,subprocess,io,ast,json,hashlib,re
r=pathlib.Path.cwd();p=r/'work/review-deadline78-475';o=r/'outputs/phase153';rows=[]
def git(*args,data=None):return subprocess.check_output(['git','-C',str(p),*args],input=data)
assert git('show','-s','--format=%T','HEAD').decode().strip()=='6f47cda8aba93ca87a377b15aae1118351237e8e'
for row in git('ls-tree','-rz','HEAD').split(b'\0'):
 if row:
  meta,name=row.split(b'\t',1);rows.append((name.decode(),meta.split()[2]))
s=io.BytesIO(git('cat-file','--batch',data=b''.join(oid+b'\n' for _,oid in rows)))
for name,oid in rows:
 actual,kind,size=s.readline().split();raw=s.read(int(size));assert s.read(1)==b'\n' and actual==oid;(p/name).write_bytes(raw)
t=ast.parse((r/'work/phase121_qualify.py').read_text());fn=next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=='inventory');ns={};exec('import pathlib,subprocess,os,hashlib,json,io',ns);exec(compile(ast.Module(body=[fn],type_ignores=[]),'<inventory>','exec'),ns);inventory=ns['inventory'](p);assert len(inventory)==406
changes=git('diff','--name-only','458de55b7170d23f2e7ab3a5d72597b2a0124653','HEAD').decode().splitlines();assert set(changes)=={'tests/fresh_render/owned_lifecycle.cjs','tests/fresh_render/test_cleanup_deadline.cjs','tests/fresh_render/CLEANUP-DEADLINE.md'};(o/'exact-source-diff.patch').write_bytes(git('diff','458de55b7170d23f2e7ab3a5d72597b2a0124653','HEAD'))
hashes={};sources={}
for f in ['owned_lifecycle.cjs','test_cleanup_deadline.cjs','bootstrap.cjs','harness.cjs','diagnostics.cjs','sync_spawn_guard.cjs']:
 raw=(p/'tests/fresh_render'/f).read_bytes();hashes[f]=hashlib.sha256(raw).hexdigest()
 if f not in ['owned_lifecycle.cjs','test_cleanup_deadline.cjs']:assert raw==git('show','458de55b7170d23f2e7ab3a5d72597b2a0124653:tests/fresh_render/'+f)
 if f in ['owned_lifecycle.cjs','test_cleanup_deadline.cjs']:sources[f]=raw.decode()
(o/'source-verification.json').write_text(json.dumps(dict(PR=79,head='47530d81e8b6f297a060a206bea6f783ccd0702e',tree='6f47cda8aba93ca87a377b15aae1118351237e8e',changed_files=changes,hashes=hashes,reviewed_sources=sources,primary_raw=inventory,noextras=True,A8_helper_project_mock_native_Job_SDK_browser_calls=0,result='F37_SOURCE_CORRECTION_ACK_RUNTIME_QUALIFICATION_NOT_RUN_BY_A8'),indent=2));print('406 rawprimary/noextras,3pathdiff,PR79',hashes['owned_lifecycle.cjs'])
