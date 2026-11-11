import pathlib,subprocess,os,json,hashlib,io
r=pathlib.Path.cwd();o=r/'outputs/phase89';repo=r/'work/read-bcfa-a8';head='bcfa243b6ecb5389270152612217f8d89643a248'
def g(path,*args,input=None):return subprocess.check_output(['git','--no-replace-objects','-C',str(path),*args],input=input)
if not repo.exists():subprocess.run(['git','clone','--no-hardlinks','--no-checkout',str(r/'work/unified-audit'),str(repo)],check=True,capture_output=True)
subprocess.run(['git','-c','core.autocrlf=false','-c','core.eol=lf','-C',str(repo),'checkout','--detach',head],check=True,capture_output=True)
def inventory():
 rows=[]
 for line in g(repo,'ls-tree','-rz','HEAD').split(b'\0'):
  if line:
   meta,name=line.split(b'\t',1);mode,kind,oid=meta.split();assert kind==b'blob';rows.append((name.decode(),oid.decode()))
 stream=io.BytesIO(g(repo,'cat-file','--batch',input=''.join(oid+'\n' for _,oid in rows).encode()));result={}
 for name,oid in rows:
  actual,kind,size=stream.readline().split();b=stream.read(int(size));assert stream.read(1)==b'\n' and actual.decode()==oid and hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==oid and (repo/name).read_bytes()==b;result[name]=hashlib.sha256(b).hexdigest()
 return result
before=inventory();env=os.environ.copy();env.update(GRID_GATEWAY_SOURCE_ROOT=str(r/'work/read815-a8-grid-f19'),A4_COMPONENT_ROOT=str(repo),PYTHONDONTWRITEBYTECODE='1')
code="import sys,unittest;sys.path[:0]=['.','tests','tests/gateway_runtime'];import test_manifest_front;s=unittest.defaultTestLoader.loadTestsFromModule(test_manifest_front);r=unittest.TextTestRunner(verbosity=2).run(s);assert r.testsRun==3 and r.wasSuccessful() and not r.skipped"
p=subprocess.run([str(r/'work/identity-a8-env/Scripts/python.exe'),'-I','-B','-c',code],cwd=repo,env=env,capture_output=True,timeout=90);(o/'bcfa-focused.stdout.log').write_bytes(p.stdout);(o/'bcfa-focused.stderr.log').write_bytes(p.stderr);assert p.returncode==0,p.stderr;assert inventory()==before
receipt=dict(head=head,tree=g(repo,'rev-parse','HEAD^{tree}').decode().strip(),primary_blob_raw_prepost=len(before),tests=3,skips=0,scope='ACTUAL_OWN_TLS_MANIFEST_TESTS_ONLY_NOT_REPEAT146',runtime_blob=g(repo,'rev-parse','HEAD:unified_system/gateway_runtime_composition.py').decode().strip(),source_raw=before)
(o/'bcfa-focused-receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps({k:v for k,v in receipt.items() if k!='source_raw'}))
