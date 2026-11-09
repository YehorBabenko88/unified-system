import pathlib,subprocess,json,hashlib,io,os
r=pathlib.Path.cwd();o=r/'outputs/phase101';o.mkdir(exist_ok=True);repo=r/'work/review-targeta84';roots={'unified':repo,'strattester':r/'work/review-research75-aed8','meta_analyse':r/'work/research75-a8-temp/gateway-meta-source-f3c'};tmp=r/'work/targeta84-a8-temp';tmp.mkdir(exist_ok=True)
def inventory(path):
 def g(*a,data=None):return subprocess.check_output(['git','--no-replace-objects','-C',str(path),*a],input=data)
 rows=[]
 for row in g('ls-tree','-rz','HEAD').split(b'\0'):
  if row:
   meta,name=row.split(b'\t',1);mode,kind,oid=meta.split();assert kind==b'blob';rows.append((name.decode(),oid.decode()))
 s=io.BytesIO(g('cat-file','--batch',data=''.join(oid+'\n' for _,oid in rows).encode()));result={}
 for name,oid in rows:
  actual,kind,size=s.readline().split();b=s.read(int(size));assert s.read(1)==b'\n' and actual.decode()==oid and hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==oid and (path/name).read_bytes()==b;result[name]=hashlib.sha256(b).hexdigest()
 return result
before={name:inventory(path) for name,path in roots.items()};(o/'correction-independent-primary-before.json').write_text(json.dumps(before,indent=2));env={k:v for k,v in os.environ.items() if not k.upper().startswith('GIT_')};env.update(EXPECTED_HEAD='a84eabb533865f6a422a03bf096222ee51052e8f',TARGET_STRATT_ROOT=str(roots['strattester']),TARGET_META_ROOT=str(roots['meta_analyse']),RUNNER_TEMP=str(tmp))
p=subprocess.run([str(r/'work/audit-venv/Scripts/python.exe'),'-I','-S','-B','-c',"import sys,unittest;sys.path.insert(0,'.');s=unittest.TestLoader().discover('tests/gateway_target_adapter',pattern='test_direct.py');cases=[];flatten=lambda suite:[x for item in suite for x in (flatten(item) if isinstance(item,unittest.TestSuite) else [item])];cases=[x for x in flatten(s) if x.id()=='test_direct.DirectTests.test_actual_target_no_python_network_and_only_owned_sqlite'];assert len(cases)==1;r=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(cases));assert r.testsRun==1 and r.wasSuccessful() and not r.skipped"],cwd=repo,env=env,capture_output=True,timeout=120);(o/'correction-own1.stdout.log').write_bytes(p.stdout);(o/'correction-own1.stderr.log').write_bytes(p.stderr);assert before=={name:inventory(path) for name,path in roots.items()};assert p.returncode==0,p.stderr.decode(errors='replace')[-2500:]
(o/'correction-focused-receipt.json').write_text(json.dumps(dict(head='a84eabb533865f6a422a03bf096222ee51052e8f',tree='0b064c8291cb4030e0a4a97ca3296b69883576a6',tests=1,skips=0,primary_files={name:len(value) for name,value in before.items()},source_raw=before),indent=2));print(json.dumps(dict(tests=1,skips=0,primary_files={name:len(value) for name,value in before.items()})))
