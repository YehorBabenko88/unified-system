import pathlib,subprocess,io,ast,json,hashlib,re,collections
r=pathlib.Path.cwd();p=r/'work/review-one-shot75-721';o=r/'outputs/phase159';rows=[];head='72117a0ba641f8a4287742f9278f4bee7a5005a6'
def git(*args,data=None):return subprocess.check_output(['git','-C',str(p),*args],input=data)
assert git('show','-s','--format=%T','HEAD').decode().strip()=='a0bfd66ff2731c63e9eb4c16df86e6d5cd795d10'
for row in git('ls-tree','-rz','HEAD').split(b'\0'):
 if row:
  meta,name=row.split(b'\t',1);rows.append((name.decode(),meta.split()[2]))
s=io.BytesIO(git('cat-file','--batch',data=b''.join(oid+b'\n' for _,oid in rows)))
for name,oid in rows:
 actual,kind,size=s.readline().split();raw=s.read(int(size));assert s.read(1)==b'\n' and actual==oid;(p/name).write_bytes(raw)
t=ast.parse((r/'work/phase121_qualify.py').read_text());fn=next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=='inventory');ns={};exec('import pathlib,subprocess,os,hashlib,json,io',ns);exec(compile(ast.Module(body=[fn],type_ignores=[]),'<inventory>','exec'),ns);inventory=ns['inventory'](p);assert len(inventory)==1670
changes=git('diff','--name-status','623c1ebe33c14707b99ad526678f5225f553e49a','HEAD').decode().splitlines();assert len(changes)==3 and all(x.startswith('A\t') for x in changes);(o/'exact-source-diff.patch').write_bytes(git('diff','623c1ebe33c14707b99ad526678f5225f553e49a','HEAD'))
patterns=['test_one_shot_closed_integration.py','test_closed_jobs.py','test_resource_capabilities.py','test_cpu_policy.py','test_capacity_freshness.py','test_clock_source_prerequisites.py'];expected=set();sources={}
for name in patterns:
 raw=(p/'tests/gateway_jobs'/name).read_bytes();tree=ast.parse(raw);sources[name]=hashlib.sha256(raw).hexdigest()
 for cls in tree.body:
  if isinstance(cls,ast.ClassDef):
   for f in cls.body:
    if isinstance(f,(ast.FunctionDef,ast.AsyncFunctionDef)) and f.name.startswith('test_'):expected.add(name.removesuffix('.py')+'.'+cls.name+'.'+f.name)
assert len(expected)==33;ownerbase=pathlib.Path('C:/Users/LS-5/Documents/Codex/2026-11-06/codex-agent-5-resource-aware-distributed/outputs');owner=[]
for version,sha in [('312','7bb718028ca5727169086a27a8c42e05698d7826f27466db7b66e9f6378a9210'),('315','2710c32ad4c6b31ab0e1c5b948d8523e3e3e63ae5524f2f56228e8007771fd8f')]:
 root=ownerbase/('AGENT5-ONE-SHOT-72117A0-LOCAL'+version);raw=(root/'receipt.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==sha;j=json.loads(raw);assert j['head']==head and j['tree']=='a0bfd66ff2731c63e9eb4c16df86e6d5cd795d10';assert j['tests']==33 and j['new_tests']==8 and j['existing_tests']==25 and j['skips']==0
 target=o/('owner'+version);target.mkdir(exist_ok=True);(target/'receipt.json').write_bytes(raw)
 for name,h in j['evidence_sha256'].items():
  b=(root/name).read_bytes();assert hashlib.sha256(b).hexdigest()==h;(target/name).write_bytes(b)
 for name,h in j['hashes'].items():assert inventory[name]==h
 log=(root/'pure-tests.log').read_text();ids=re.findall(r'\btest_\w+\s+\(([^)]+)\)\s+\.\.\.\s+ok',log);assert len(ids)==len(set(ids))==33 and set(ids)==expected and 'Ran 33 tests' in log and not re.search(r'\.\.\.\s+(skipped|FAIL|ERROR)',log)
 mutation=(root/'mutation-expected-failures.log').read_text();assert len(re.findall(r'^FAILED \(failures=1\)',mutation,re.M))==2 and mutation.count('AssertionError')>=2
 owner.append(dict(interpreter=version,receipt_sha256=sha,unique_tests=33,unit_ids=ids,expected_mutation_failures=2,raw_prepost_and_nativezero='OWNER_ASSERTIONS_NOT_A8_REPLAY_OR_HOST_MEASUREMENTS'))
qual=ownerbase/'qualify-one-shot-negative-20261110.py';raw=qual.read_bytes();(o/'owner-qualifier.original.py').write_bytes(raw)
api=subprocess.check_output(['gh','api','repos/YehorBabenko88/unified-system/actions/runs?head_sha='+head+'&per_page=100']);(o/'GitHub-runs.original.json').write_bytes(api);runs=json.loads(api)['workflow_runs'];selected=[x for x in runs if x['path']=='.github/workflows/agent5-one-shot-negative.yml'];jobs=[]
for run in selected:
 b=subprocess.check_output(['gh','api','repos/YehorBabenko88/unified-system/actions/runs/'+str(run['id'])+'/jobs']);(o/(str(run['id'])+'.jobs.original.json')).write_bytes(b);jobs.append(dict(run=run['id'],status=run['status'],conclusion=run['conclusion'],jobs=json.loads(b)['jobs']))
(o/'source-and-owner-evidence-verification.json').write_text(json.dumps(dict(head=head,tree='a0bfd66ff2731c63e9eb4c16df86e6d5cd795d10',primary_raw=inventory,noextras=True,added_only_paths=changes,selected_source_test_ids=sorted(expected),selected_source_hashes=sources,owner_evidence=owner,owner_qualifier_sha256=hashlib.sha256(raw).hexdigest(),hosted_new_workflow_snapshot=jobs,A8_project_imports_tests_SQLite_fixture_native_Job_SDK_browser_Math_calls=0,result='SOURCE_AND_ORIGINAL_OWNER_DATA_REVIEW_ONLY_NOT_A8_TEST_EXECUTION_OR_ADOPTION'),indent=2));print('1670raw/noextras;33sourceIDs match eachownerlog,2expectedfailures each;A8runtime0;hosted',[(x['run'],x['status']) for x in jobs])
