import pathlib,subprocess,json,hashlib,io,os
r=pathlib.Path.cwd();repo=r/'work/review-map55-c741';o=r/'outputs/phase105';o.mkdir(exist_ok=True);head='c741f36e8ddaf58bb8a709b986609916ec6f2358'
def g(*a,data=None):return subprocess.check_output(['git','--no-replace-objects','-C',str(repo),*a],input=data)
def inventory():
 rows=[]
 for row in g('ls-tree','-rz','HEAD').split(b'\0'):
  if row:
   meta,name=row.split(b'\t',1);mode,kind,oid=meta.split();assert kind==b'blob';rows.append((name.decode(),oid.decode()))
 stream=io.BytesIO(g('cat-file','--batch',data=''.join(oid+'\n' for _,oid in rows).encode()));result={}
 for name,oid in rows:
  actual,kind,size=stream.readline().split();b=stream.read(int(size));assert stream.read(1)==b'\n' and actual.decode()==oid and hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==oid and (repo/name).read_bytes()==b;result[name]=hashlib.sha256(b).hexdigest()
 for p in repo.rglob('*'):
  rel=p.relative_to(repo)
  if rel.parts[0]!='.git' and p.is_file():assert rel.as_posix() in result
 return result
before=inventory();assert len(before)==1411
code='''import sys,unittest,json,importlib.metadata
sys.path.insert(0,'.');import jsonschema
blocked=[]
def audit(event,args):
 if event in ['subprocess.Popen','sqlite3.connect','socket.connect','socket.getaddrinfo','os.system']:blocked.append(event);raise AssertionError('A8_PURE_TEST_RUNTIME_EFFECT_FORBIDDEN')
 if event=='import' and any(args[0]==x or args[0].startswith(x+'.') for x in ['grid','meta_analyse','unified_system.gateway_research_identity','unified_system.gateway_worker','unified_system.gateway_target_adapter']):blocked.append('runtime_import');raise AssertionError('A8_RUNTIME_IMPORT_FORBIDDEN')
sys.addaudithook(audit)
class Result(unittest.TextTestResult):
 def __init__(self,*a,**k):super().__init__(*a,**k);self.subcases={}
 def addSubTest(self,test,subtest,err):
  self.subcases[test.id()]=self.subcases.get(test.id(),0)+1;super().addSubTest(test,subtest,err)
s=unittest.TestLoader().discover('tests/gateway_jobs',pattern='test_target_native_mapping_proposal.py')
def ids(s):return [x for item in s for x in (ids(item) if isinstance(item,unittest.TestSuite) else [item.id()])]
actual=ids(s);assert len(actual)==len(set(actual))==14
r=unittest.TextTestRunner(verbosity=2,resultclass=Result).run(s);assert r.wasSuccessful() and r.testsRun==14 and not r.skipped and not blocked
print(json.dumps({'tests':actual,'tests_run':14,'skips':0,'subcase_counts':r.subcases,'runtime_effect_or_import_attempts':blocked,'jsonschema':importlib.metadata.version('jsonschema'),'python':sys.version,'scope':'PURE_FORMAT_AND_HASH_SENSITIVITY_NOT_NATIVE_ADMISSION'},indent=2))
'''
(o/'pure14-executed.py').write_text(code);p=subprocess.run([str(r/'work/mux-independent-env/Scripts/python.exe'),'-I','-B','-c',code],cwd=repo,capture_output=True,timeout=45);(o/'pure14.stdout.json').write_bytes(p.stdout);(o/'pure14.stderr.log').write_bytes(p.stderr);assert p.returncode==0,p.stderr;assert before==inventory()
(o/'primary-verification.json').write_text(json.dumps(dict(head=head,tree=g('rev-parse','HEAD^{tree}').decode().strip(),base='3e498de973536c2d6393f83abe7d59cb1452a9b4',new_paths=g('diff','--name-status','3e498de973536c2d6393f83abe7d59cb1452a9b4','HEAD').decode().splitlines(),primary_raw_prepost=1411,source_raw=before,tests=14,skips=0,actual_backend_runtime_calls=0),indent=2));print(p.stdout.decode())
