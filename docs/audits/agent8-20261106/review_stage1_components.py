"""A8 independent exact-source focused acceptance, guarded loopback only."""
import concurrent.futures,datetime,hashlib,json,os,pathlib,subprocess
r=pathlib.Path(__file__).resolve().parents[1];out=r/'outputs/phase31';out.mkdir(exist_ok=True)
cases=[('lan',30,'1541af3b0e99fdb671f59c205696faab40e283e4','30d32ab7b75eadcca46b41ae6809415665ef1413'),('storage',29,'10157fed4d28606adf587be3494d2f6d42887ce9','62564f00bd8c37b982c2ee958ff58b956c55b1be'),('control',31,'7a0365bd0161ec619019157cf04672b513c495c6','597dbbdad1861f3e872f867dba30ad2667566d15')]
def git(p,*args):return subprocess.check_output(['git','--no-replace-objects','-C',str(p),*args])
def identity(p,sha):
 rows=[]
 for item in filter(None,git(p,'ls-tree','-rz',sha).split(b'\0')):
  metadata,name=item.split(b'\t',1);mode,kind,oid=metadata.split();assert kind==b'blob' and mode in (b'100644',b'100755')
  raw=(p/name.decode()).read_bytes();assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==oid.decode(),name
  rows.append([name.decode(),hashlib.sha256(raw).hexdigest()])
 return dict(files=len(rows),sha256=hashlib.sha256(json.dumps(rows).encode()).hexdigest())
guard='''import sys,ipaddress,json,pathlib
network=[]
def guard(event,args):
 if event in ('socket.connect','socket.bind'):
  addr=args[1]
  if not isinstance(addr,tuple) or not ipaddress.ip_address(addr[0]).is_loopback:raise RuntimeError('A8_NONLOOPBACK_IO_DENIED')
  network.append(dict(event=event,address=addr[0],port=addr[1]))
sys.addaudithook(guard)
'''
def run(case):
 label,pr,sha,tree=case;p=r/('work/review-stage1-'+label);folder=out/label;folder.mkdir(exist_ok=True)
 metadata=subprocess.check_output(['gh','pr','view',str(pr),'--repo','YehorBabenko88/unified-system','--json','headRefOid,baseRefOid,isDraft,files,url']);(folder/'primary-pr.json').write_bytes(metadata);m=json.loads(metadata);assert m['headRefOid']==sha and m['isDraft']
 assert git(p,'rev-parse','HEAD').decode().strip()==sha and git(p,'rev-parse','HEAD^{tree}').decode().strip()==tree
 assert (p/'.git').is_dir() and not (p/'.git/objects/info/alternates').exists();assert (p/git(p,'rev-parse','--git-common-dir').decode().strip()).resolve()==(p/'.git').resolve()
 before=identity(p,sha)
 boot=guard+'sys.path.insert(0,'+repr(str(p))+')\n'
 if label=='lan':
  boot+="import unittest\nsuite=unittest.defaultTestLoader.loadTestsFromNames(['tests.test_lan_transport','tests.test_network_budget'])\nresult=unittest.TextTestRunner(verbosity=2).run(suite)\nrc=0 if result.wasSuccessful() and result.testsRun==28 and not result.skipped else 1\n"
 elif label=='storage':
  boot+="import runpy\nmodule=runpy.run_path('tests/storage/run_stage1.py');rc=module['main']()\n"
 else:
  boot+="from tests.control_v3.source_runner import run\nrun(pathlib.Path.cwd(),"+repr(sha)+",pathlib.Path("+repr(str(folder/'runner'))+"));rc=0\n"
 boot+='pathlib.Path('+repr(str(folder/'observed-loopback.json'))+').write_text(json.dumps(network,indent=2));raise SystemExit(rc)\n'
 env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1');env.pop('GIT_NO_REPLACE_OBJECTS',None)
 process=subprocess.run([str(r/'work/audit-venv/Scripts/python.exe'),'-I','-B','-c',boot],cwd=p,env=env,capture_output=True,timeout=120)
 (folder/'stdout.log').write_bytes(process.stdout);(folder/'stderr.log').write_bytes(process.stderr)
 assert process.returncode==0,(label,process.stderr.decode(errors='replace')[-2000:])
 after=identity(p,sha);assert before==after
 return dict(repository='unified-system',pr=m['url'],head=sha,tree=tree,environment='Windows isolated no-hardlink clone; Python3.12; loopback-only audit hook in test process',exit_code=process.returncode,raw_before=before,raw_after=after,test_count={'lan':28,'storage':26,'control':46}[label],skips=0,status='FOCUSED_OFFLINE_PASS_ONLY',hosted='NOT_QUALIFIED',physical='BLOCKED')
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(run,cases))
report=dict(checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),results=results,full_suite='NOT_RERUN_NOT_QUALIFIED_REPORTED_AGENT1_ERROR_AND11SKIPS_NOT_WAIVED',runtime='NOT_ADMITTED',physical='BLOCKED',tailscale_removal='BLOCKED',overall='NO_GO')
(out/'stage1-focused-review.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
