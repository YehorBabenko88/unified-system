import pathlib,subprocess,io,ast,json,hashlib,re
r=pathlib.Path.cwd();p=r/'work/review-render78-458';o=r/'outputs/phase152';rows=[]
def git(*args,data=None):return subprocess.check_output(['git','-C',str(p),*args],input=data)
assert git('show','-s','--format=%T','HEAD').decode().strip()=='135159a2daa9fb035f620cca26c84c471d339260'
for row in git('ls-tree','-rz','HEAD').split(b'\0'):
 if row:
  meta,name=row.split(b'\t',1);rows.append((name.decode(),meta.split()[2]))
s=io.BytesIO(git('cat-file','--batch',data=b''.join(oid+b'\n' for _,oid in rows)))
for name,oid in rows:
 actual,kind,size=s.readline().split();raw=s.read(int(size));assert s.read(1)==b'\n' and actual==oid;(p/name).write_bytes(raw)
t=ast.parse((r/'work/phase121_qualify.py').read_text());fn=next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=='inventory');ns={};exec('import pathlib,subprocess,os,hashlib,json,io',ns);exec(compile(ast.Module(body=[fn],type_ignores=[]),'<inventory>','exec'),ns);inventory=ns['inventory'](p);assert len(inventory)==404
files=['bootstrap.cjs','harness.cjs','diagnostics.cjs','owned_lifecycle.cjs'];sources={f:(p/'tests/fresh_render'/f).read_text() for f in files};hashes={f:hashlib.sha256((p/'tests/fresh_render'/f).read_bytes()).hexdigest() for f in files};(o/'exact-source-diff.patch').write_bytes(git('diff','161ea1e0fc3a3a4cd64783b0e111e1e119e14d71','HEAD'))
for f in ['tests/fresh_render/sync_spawn_guard.cjs','terminan/target_adapter_result.js']:assert (p/f).read_bytes()==git('show','161ea1e0fc3a3a4cd64783b0e111e1e119e14d71:'+f)
a6=pathlib.Path('C:/Users/LS-5/Documents/Codex/2026-11-06/codex-agent-6-distributed-terminan-control/outputs/terminan-sync-v1/render-diagnostics');originals={}
for f in ['RESULTS-458de55.json','PINNED-SDK-SEMANTICS.json','render-diagnostics-18-final.tap']:
 raw=(a6/f).read_bytes();originals[f]=dict(original=str(a6/f),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest());(o/f).write_bytes(raw)
result=json.loads((o/'RESULTS-458de55.json').read_bytes());assert result['head']=='458de55b7170d23f2e7ab3a5d72597b2a0124653' and result['tree']=='135159a2daa9fb035f620cca26c84c471d339260'
for f,key in [('bootstrap.cjs','bootstrap'),('harness.cjs','harness'),('diagnostics.cjs','diagnostics'),('owned_lifecycle.cjs','owned_lifecycle')]:assert hashes[f]==result['pins_sha256'][key]
tap=(o/'render-diagnostics-18-final.tap').read_text();assert len(re.findall(r'^ok \d+ - ',tap,re.M))==18 and '# pass 18' in tap and '# fail 0' in tap and '# skipped 0' in tap
sdk=[]
for row in json.loads((o/'PINNED-SDK-SEMANTICS.json').read_bytes())['rows']:
 raw=pathlib.Path(row['source_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['sha256'];sdk.append(dict(**row,independently_read_hash_match=True))
(o/'source-verification.json').write_text(json.dumps(dict(head=result['head'],tree=result['tree'],primary_raw=inventory,noextras=True,hashes=hashes,reviewed_sources=sources,owner_originals=originals,owner_TAP='ORIGINAL_18_PASS_0FAIL_0SKIP_NOT_A8_EXECUTION',owner_full_raw_prepost='OWNER_ASSERTION_NOT_INDEPENDENTLY_REPLAYED',sdk_source_only=sdk,F37='NO_POSTCOMPLETION_OR_FINAL_MONOTONIC_CLEANUP_DEADLINE_CHECK',A8_project_imports_tests_native_SDK_Job_browser_calls=0),indent=2));print('404primary raw/noextras;ownerTAP18 authenticated distinctnotA8;sourceF37')
