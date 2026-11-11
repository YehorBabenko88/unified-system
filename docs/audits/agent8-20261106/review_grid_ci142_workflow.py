"""Execute committed workflow Python blocks locally; hosted review stays separate."""
import hashlib,io,json,os,pathlib,subprocess
r=pathlib.Path(__file__).resolve().parents[1];repo=r/'work/review-grid-ci142-7a19';out=r/'outputs/phase58';out.mkdir(exist_ok=True);head='7a19ab40c30efef431bb16f0ddc91960608bf597';temp=r/'work/a3-ci142-a8-temp';temp.mkdir(exist_ok=False);py=r/'work/a3-ci142-env/Scripts/python.exe'
def git(*a):return subprocess.check_output(['git','--no-replace-objects','-C',str(repo),*a])
assert git('diff','--name-only','9d71ee33',head).decode().splitlines()==['.github/workflows/agent3-checkpoint-v3.yml'];workflow=git('show',head+':.github/workflows/agent3-checkpoint-v3.yml');text=workflow.decode();(out/'workflow.original.yml').write_bytes(workflow)
def block(name):
 part=text.split('      - name: '+name+'\n',1)[1].split('        run: |\n',1)[1];lines=[]
 for line in part.splitlines():
  if line and not line.startswith('          '):break
  lines.append(line[10:] if line else '')
 return '\n'.join(lines)+'\n'
def identity():
 names=git('ls-tree','-r','--name-only',head).decode().splitlines();stream=io.BytesIO(subprocess.check_output(['git','--no-replace-objects','-C',str(repo),'cat-file','--batch'],input=''.join(head+':'+n+'\n' for n in names).encode()));rows={}
 for name in names:
  oid,kind,size=stream.readline().split();assert kind==b'blob';raw=stream.read(int(size));assert stream.read(1)==b'\n' and raw==(repo/name).read_bytes();rows[name]=hashlib.sha256(raw).hexdigest()
 return rows
before=identity();env={k:v for k,v in os.environ.items() if not k.startswith('GIT_') and k not in ('PYTHONPYCACHEPREFIX','PYTEST_ADDOPTS','PYTEST_PLUGINS')};env.update(A3_EXPECTED_HEAD=head,RUNNER_TEMP=str(temp),PYTHONDONTWRITEBYTECODE='1')
steps=['Source guard before tests','Exact codec inventory and zero skips','Exact separate domain/page inventory and zero skips','Exact separate response advice inventory and zero skips','Source guard after tests']
for index,name in enumerate(steps):
 e=dict(env,A3_GUARD_PHASE='after' if index==4 else 'before');p=subprocess.run([str(py),'-I','-B','-c',block(name)],cwd=repo,env=e,capture_output=True,timeout=90);(out/('step'+str(index)+'.stdout.log')).write_bytes(p.stdout);(out/('step'+str(index)+'.stderr.log')).write_bytes(p.stderr);assert p.returncode==0,(name,p.stderr.decode(errors='replace')[-1500:])
folder=temp/'agent3-checkpoint-v3'
for f in folder.iterdir():
 if f.is_file() and f.suffix in ('.json','.xml','.log'):(out/f.name).write_bytes(f.read_bytes())
a=json.loads((folder/'before-source.json').read_bytes());b=json.loads((folder/'after-source.json').read_bytes());assert len(a['files'])==27 and a['files']==b['files'] and a['head']==b['head']==head;assert before==identity()
counts=[]
for name,count in [('result.json',43),('domain-result.json',55),('response-result.json',44)]:
 v=json.loads((folder/name).read_bytes());assert v['cases']==count and v['skips']==0 and v['head']==head;counts.append(count)
report=dict(head=head,tree=git('rev-parse',head+'^{tree}').decode().strip(),workflow_raw_sha256=hashlib.sha256(workflow).hexdigest(),only_delta_from9d71='WORKFLOW',all_product_profile_policy_inventories_raw_unchanged=True,actual_tests=counts,total=142,skips=0,protected_raw_files=27,all_primary_raw_files_before_after=len(before),interpreter='Python3.12-I-B-pytest8.3.5-own-venv',scope='LOCAL_WINDOWS_COMMITTED_WORKFLOW_NOT_HOSTED',hosted='NOT_QUALIFIED',permission=False,provider_or_native_admission=False)
(out/'local-workflow-review.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
