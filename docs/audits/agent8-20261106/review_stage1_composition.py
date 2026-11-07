"""Synthetic composition is compatibility evidence, never a release candidate."""
import hashlib,json,os,pathlib,subprocess,uuid
r=pathlib.Path(__file__).resolve().parents[1];out=r/'outputs/phase31';seed=r/'work/review-integration75';base='18085568df01bdbc4df74404e3c650ec30bb7d6b';p=r/('work/stage1-composition-'+uuid.uuid4().hex[:8])
def git(at,*args):return subprocess.check_output(['git','--no-replace-objects','-C',str(at),*args])
subprocess.run(['git','clone','--no-hardlinks','--no-checkout',str(seed),str(p)],check=True,capture_output=True);subprocess.run(['git','-C',str(p),'-c','core.autocrlf=false','-c','core.eol=lf','checkout','--detach',base],check=True,capture_output=True)
composition={}
for label in ('lan','storage','control'):
 src=r/('work/review-stage1-'+label);metadata=json.loads((out/label/'primary-pr.json').read_bytes());sha=metadata['headRefOid']
 for item in metadata['files']:
  relative=item['path'];target=p/relative;assert not target.exists(),relative
  raw=git(src,'show',sha+':'+relative);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);composition[relative]=dict(source=sha,sha256=hashlib.sha256(raw).hexdigest())
def hashes():return {name:hashlib.sha256((p/name).read_bytes()).hexdigest() for name in composition}
before=hashes()
boot='''import sys,json,pathlib,unittest,ipaddress
sys.path.insert(0,str(pathlib.Path.cwd()))
sys.path.insert(1,DEPS)
def guard(event,args):
 if event in ('socket.connect','socket.bind'):
  if not isinstance(args[1],tuple) or not ipaddress.ip_address(args[1][0]).is_loopback:raise RuntimeError('A8_NONLOOPBACK_DENIED')
sys.addaudithook(guard)
inventory=json.loads(pathlib.Path('release/component-test-inventory.json').read_bytes())
modules=inventory['modules']+['tests.test_lan_transport','tests.test_network_budget','tests.storage.test_contracts','tests.storage.test_segments','tests.storage.test_retention','tests.storage.test_checkpoint_vectors','tests.test_control_v3_boundary']
suite=unittest.defaultTestLoader.loadTestsFromNames(modules)
def flatten(suite):
 for test in suite:
  if isinstance(test,unittest.TestSuite):yield from flatten(test)
  else:yield test.id()
ids=list(flatten(suite));assert len(ids)==len(set(ids))==159
result=unittest.TextTestRunner(verbosity=2).run(suite)
assert result.wasSuccessful() and result.testsRun==159 and not result.skipped
# Independent effect-boundary probes, no network or native callbacks.
from unified_system.lan_transport import LanTransport,TransportError
from unified_system.network_budget import NodeBudget,EgressProjection,BudgetError
from unified_system.storage.contracts import require_publication_authority,StorageBlocked
from unified_system.storage.segments import ByteCheck
from unified_system.control_v3_boundary import ControlV3App
from tests.test_control_v3_boundary import call,environ
probes=[]
for fn,error in ((LanTransport.runtime,TransportError),(NodeBudget.runtime,BudgetError),(EgressProjection.runtime,BudgetError),(require_publication_authority,StorageBlocked)):
 for value in (True,{'COMMITTED':True},ByteCheck('0'*64,1,1)):
  try:fn(value)
  except error:probes.append('DENIED_'+fn.__qualname__)
  else:raise AssertionError('effect boundary opened')
for headers in ({'HTTP_AUTHORIZATION':'Bearer forged'},{'REMOTE_USER':'Administrator','HTTP_X_SESSION_EXPIRES':'9999999999999999'},{'HTTP_X_AUTHORITY':'COMMITTED','HTTP_X_ROLE':'OPERATOR'}):
 status,_,value=call(ControlV3App(),environ(**headers));assert status==503 and value['native_admission'] is False and 'resources' not in value;probes.append('DEFAULT_CONTROL_UNAUTHENTICATED_DENIED')
print(json.dumps(dict(tests=159,skips=0,independent_effect_boundary_vectors=len(probes),scope='SYNTHETIC_OVERLAY_COMPATIBILITY_ONLY_NOT_RELEASE_HEAD_OR_AUTHENTICATION_ACCEPTANCE')))
'''.replace('DEPS',repr(str(r/'work/integration-review-deps')))
proc=subprocess.run([str(r/'work/audit-venv/Scripts/python.exe'),'-I','-B','-c',boot],cwd=p,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),capture_output=True,timeout=120)
(out/'composition.stdout.log').write_bytes(proc.stdout);(out/'composition.stderr.log').write_bytes(proc.stderr);assert proc.returncode==0,proc.stderr.decode(errors='replace')[-2000:];assert before==hashes()
for item in filter(None,git(p,'ls-tree','-rz',base).split(b'\0')):
 meta,name=item.split(b'\t',1);raw=(p/name.decode()).read_bytes();assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==meta.split()[2].decode()
report=dict(base=base,composition=composition,tests=159,unique_cases=159,control_inventory_reuses_16_existing_root_cases=True,skips=0,independent_effect_boundary_vectors=15,raw_overlay_unchanged=True,raw_base_blobs_unchanged=True,status='SYNTHETIC_OFFLINE_COMPATIBILITY_PASS_ONLY',runtime_admission=False,physical='BLOCKED',overall='NO_GO')
(out/'composition-review.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='composition'}))
