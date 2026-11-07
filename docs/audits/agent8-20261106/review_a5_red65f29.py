import pathlib,subprocess,os,json,hashlib,io
r=pathlib.Path.cwd();repo=r/'work/review-a5-red65f29';o=r/'outputs/phase73';o.mkdir(exist_ok=True);py=r/'work/audit-venv/Scripts/python.exe'
def git(*a,data=None):return subprocess.check_output(['git','--no-replace-objects','-C',str(repo),*a],input=data)
head=git('rev-parse','HEAD').decode().strip();assert head=='65f29d7528a5b1ac0f5a7338ab49dfd78cfb8161';assert git('rev-parse','HEAD^{tree}').decode().strip()=='ed54ae64c6aeab7ba7b8b3e748afaea4012e6634';changes=git('diff','--name-status','7a4185924d4702ade53f518644e45d6ee4f6f451','HEAD').decode().splitlines();assert len(changes)==2 and all(x.startswith('A\t') for x in changes)
entries=[]
for row in git('ls-tree','-rz','HEAD').split(b'\0'):
 if row:
  meta,name=row.split(b'\t',1);mode,kind,oid=meta.split();entries.append((name.decode(),oid.decode()))
s=io.BytesIO(git('cat-file','--batch',data=''.join(oid+'\n' for _,oid in entries).encode()));before={}
for name,oid in entries:
 actual,kind,size=s.readline().split();raw=s.read(int(size));assert s.read(1)==b'\n' and actual.decode()==oid and hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==oid and (repo/name).read_bytes()==raw;before[name]=hashlib.sha256(raw).hexdigest()
env={k:v for k,v in os.environ.items() if k!='AGENT5_RUN_NATIVE_ASSIGNMENT_CONTRACTS'};env['PYTHONDONTWRITEBYTECODE']='1'
def run(name,args,expected):
 p=subprocess.run([str(py),'-I','-B',*args],cwd=repo,env=env,capture_output=True,timeout=30);(o/(name+'.stdout.log')).write_bytes(p.stdout);(o/(name+'.stderr.log')).write_bytes(p.stderr);assert p.returncode==expected,(name,p.stderr);return p
p=run('direct-unselected',['tests/test_agent5_assignment_backend_contract.py'],2);assert json.loads(p.stdout)['native_acceptance'] is False
p=run('native-selected',['tests/test_agent5_assignment_backend_contract.py','--run-native-contracts','-v'],1);assert b'Ran 5 tests' in p.stderr and b'FAILED (errors=5)' in p.stderr and p.stderr.count(b'ERROR: test_')==5
p=run('default-discovery',['-c',"import unittest,pathlib; s=unittest.defaultTestLoader.discover(str(pathlib.Path.cwd()/'tests'),pattern='test_agent5_assignment_backend_contract.py');assert s.countTestCases()==0;r=unittest.TextTestRunner().run(s);assert r.testsRun==0"],0);assert b'NOT_RUN_ACTUAL_BINDING_UNAVAILABLE' in p.stderr
for name,digest in before.items():assert hashlib.sha256((repo/name).read_bytes()).hexdigest()==digest
assert not list(repo.rglob('*.pyc'))
(o/'source-classification.json').write_text(json.dumps(dict(head=head,tree='ed54ae64c6aeab7ba7b8b3e748afaea4012e6634',changed_paths=changes,primary_raw_prepost=before,default_scheduled_native_cases=0,default='NOT_RUN',unselected_direct_exit=2,selected_scheduled=5,selected_setup_errors=5,native_bodies_executed=0,native_acceptance='NOT_RUN',scope='CLASSIFICATION_AND_SOURCE_ONLY_NOT_NATIVE_PASS'),indent=2),encoding='utf-8');print('341raw prepost; default0 NOT_RUN/direct2; selected5 dependencyERROR/0nativebodies')
