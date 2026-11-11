import pathlib,subprocess,json,hashlib,io,os
r=pathlib.Path.cwd();o=r/'outputs/phase101';o.mkdir(exist_ok=True);repo=r/'work/review-target8dc';roots={'unified':repo,'strattester':r/'work/review-research75-aed8','meta_analyse':r/'work/research75-a8-temp/gateway-meta-source-f3c'};tmp=r/'work/target8dc-a8-temp';tmp.mkdir(exist_ok=True)
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
before={name:inventory(path) for name,path in roots.items()};(o/'independent-primary-before.json').write_text(json.dumps(before,indent=2));env={k:v for k,v in os.environ.items() if not k.upper().startswith('GIT_')};env.update(EXPECTED_HEAD='8dc717ab85681d71711783df3ff11bfa8d9a2d87',TARGET_STRATT_ROOT=str(roots['strattester']),TARGET_META_ROOT=str(roots['meta_analyse']),RUNNER_TEMP=str(tmp))
p=subprocess.run([str(r/'work/audit-venv/Scripts/python.exe'),'-I','-S','-B',str(repo/'docs/intelligence/target-adapter/run_qualification.py')],cwd=repo,env=env,capture_output=True,timeout=120);(o/'own21.stdout.log').write_bytes(p.stdout);(o/'own21.stderr.log').write_bytes(p.stderr);assert before=={name:inventory(path) for name,path in roots.items()};assert p.returncode==0,p.stderr.decode(errors='replace')[-2500:]
for pth in (tmp/'target-adapter-evidence').iterdir():
 if pth.is_file():(o/pth.name).write_bytes(pth.read_bytes())
d=json.loads((o/'qualification.json').read_bytes());assert d['tests_run']==len(d['tests'])==len(set(d['tests']))==21 and d['skips']==0 and d['source_before']==d['source_after'];print(json.dumps(dict(tests=21,skips=0,primary_files={name:len(value) for name,value in before.items()})))
