import pathlib,subprocess,os,json,hashlib,io,xml.etree.ElementTree as ET
r=pathlib.Path.cwd();repo=r/'work/review-slice77-887';o=r/'outputs/phase95';o.mkdir(exist_ok=True);head='887e3eeaf23ef8d9d1429435bc88bbac8099c6e6';tmp=r/'work/slice77-a8-temp';tmp.mkdir(exist_ok=True)
subprocess.run(['git','clone','--no-hardlinks','--no-checkout',str(r/'work/review-query76-cdd'),str(repo)],check=True,capture_output=True);subprocess.run(['git','-c','core.autocrlf=false','-c','core.eol=lf','-C',str(repo),'checkout','--detach',head],check=True,capture_output=True)
def g(*a,data=None):return subprocess.check_output(['git','--no-replace-objects','-C',str(repo),*a],input=data)
def inventory():
 rows=[]
 for row in g('ls-tree','-rz','HEAD').split(b'\0'):
  if row:
   meta,name=row.split(b'\t',1);mode,kind,oid=meta.split();assert kind==b'blob';rows.append((name.decode(),oid.decode()))
 s=io.BytesIO(g('cat-file','--batch',data=''.join(oid+'\n' for _,oid in rows).encode()));result={}
 for name,oid in rows:
  actual,kind,size=s.readline().split();b=s.read(int(size));assert s.read(1)==b'\n' and actual.decode()==oid and hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==oid and (repo/name).read_bytes()==b;result[name]=hashlib.sha256(b).hexdigest()
 for p in repo.rglob('*'):
  rel=p.relative_to(repo)
  if rel.parts[0]!='.git' and p.is_file():assert rel.as_posix() in result
 return result
before=inventory();assert len(before)==806;env=os.environ.copy();env.update(PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTHONDONTWRITEBYTECODE='1');code="import sys,pytest;sys.path.insert(0,'.');raise SystemExit(pytest.main(sys.argv[1:]))";args=['tests/research/gateway_artifact_persistence/test_local_stage.py','tests/persistence/test_result_store.py','tests/persistence/test_result_store_recovery.py','tests/runtime/test_service_manager.py','-q','-rs','-p','no:cacheprovider','--junitxml='+str(o/'own45.xml'),'--basetemp='+str(tmp/'pytest')]
p=subprocess.run([str(r/'work/a3-ci142-env/Scripts/python.exe'),'-I','-B','-c',code,*args],cwd=repo,env=env,capture_output=True,timeout=120);(o/'own45.stdout.log').write_bytes(p.stdout);(o/'own45.stderr.log').write_bytes(p.stderr);assert p.returncode==0,p.stderr+p.stdout;cases=list(ET.parse(o/'own45.xml').iter('testcase'));assert len(cases)==45 and not any(c.find(tag) is not None for c in cases for tag in ['failure','error','skipped']);assert inventory()==before
receipt=dict(head=head,tree=g('rev-parse','HEAD^{tree}').decode().strip(),tests=45,skips=0,primary_raw_prepost=806,pytest='8.3.5_OWN_ENV_AUTO_PLUGINS_DISABLED',full_pytest=False,source_raw=before)
(o/'primary-verification.json').write_text(json.dumps(receipt,indent=2));print(json.dumps({k:v for k,v in receipt.items() if k!='source_raw'}))
