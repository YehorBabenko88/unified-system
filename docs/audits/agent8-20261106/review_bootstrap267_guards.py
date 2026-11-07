"""Four own-clone source guard controls; no test execution in negative fixtures."""
import hashlib,json,os,pathlib,subprocess,textwrap,uuid
r=pathlib.Path(__file__).resolve().parents[1];seed=r/'work/review-bootstrap7a83';out=r/'outputs/phase63';head='7a83e6e1aa74001c4797e9bf7af9368d3192bfbe';workflow=(out/'workflow.original.yml').read_text(encoding='utf-8');code=textwrap.dedent(workflow.split('        run: |\n',1)[1].split('      - uses:',1)[0]);guard=code.split('before=receipt()',1)[0];rows=[]
for name in ['cache','shadow','tracked','replace']:
 repo=r/'work'/('bootstrap-a8-negative-'+name+'-'+uuid.uuid4().hex[:6]);subprocess.run(['git','clone','--no-hardlinks','--no-checkout',str(seed),str(repo)],check=True,capture_output=True);subprocess.run(['git','-C',str(repo),'-c','core.autocrlf=false','-c','core.eol=lf','checkout','--detach',head],check=True,capture_output=True);temp=r/'work'/('bootstrap-a8-negative-evidence-'+uuid.uuid4().hex[:6]);temp.mkdir();marker=temp/'UNEXPECTED_GUARD_SUCCESS';target=repo/'grid/strategy_statistics.py'
 if name=='cache':(repo/'orphan.pyc').write_bytes(b'INERT_NOT_EXECUTED')
 elif name=='shadow':(repo/'statistics.py').write_text("raise AssertionError('INERT_UNTRUSTED_SHADOW')\n",encoding='utf-8')
 else:
  target.write_bytes(target.read_bytes()+b'\n# inert primary source mismatch\n')
  if name=='replace':
   old=subprocess.check_output(['git','--no-replace-objects','-C',str(repo),'rev-parse',head+':grid/strategy_statistics.py']).decode().strip();new=subprocess.check_output(['git','-C',str(repo),'hash-object','-w','--no-filters',str(target)]).decode().strip();assert subprocess.check_output(['git','--no-replace-objects','-C',str(repo),'cat-file','blob',new])==target.read_bytes();subprocess.run(['git','-C',str(repo),'replace',old,new],check=True,capture_output=True)
 env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')};env.update(EXPECTED_HEAD=head,RUNNER_TEMP=str(temp));p=subprocess.run([str(r/'work/audit-venv/Scripts/python.exe'),'-I','-B','-c',guard+'\nreceipt()\npathlib.Path('+repr(str(marker))+').write_text("unexpected")'],cwd=repo,env=env,capture_output=True,timeout=30);(out/('guard-'+name+'.stderr.log')).write_bytes(p.stderr);assert p.returncode!=0 and not marker.exists();rows.append(dict(case=name,rejected=True,tests_executed=0,stderr_sha256=hashlib.sha256(p.stderr).hexdigest()))
ci=[]
for run in [42365574486,42365571505]:
 p=subprocess.run(['gh','api','repos/YehorBabenko88/bybit-cluster-grid/actions/runs/'+str(run)],capture_output=True,check=True);(out/('ci-'+str(run)+'.original.json')).write_bytes(p.stdout);d=json.loads(p.stdout);assert d['head_sha']==head;ci.append({k:d.get(k) for k in ['id','head_sha','run_attempt','status','conclusion','event']})
(out/'guard-controls.json').write_text(json.dumps(dict(own_source_controls=rows,hosted_snapshot=ci,scope='GUARDS_NOT_ACTUAL_PYTEST_OR_HOSTED_RESULT'),indent=2),encoding='utf-8');print(json.dumps(dict(controls=4,ci=ci)))
