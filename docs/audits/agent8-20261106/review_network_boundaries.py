"""Eight-path audit with inert fixtures. Real SSH/network probe invocation forbidden."""
import ast,asyncio,base64,gzip,hashlib,json,os,pathlib,re,socket,subprocess,sys,unittest
root=pathlib.Path(__file__).resolve().parents[1];repo=root/'work/review-network-034';out=root/'outputs/phase21';out.mkdir(exist_ok=True)
head='0346018b58ed612dbe62fba7861f3e0b6a63ee94';parent='b12c6c24eeb2c59aa099f1c516d77508f36b20a6'
paths=['scripts/network_readonly_probe.ps1','tests/test_lan_probe_inventory.py','tests/test_network_broker_boundary.py','tests/test_network_deployment_guard.py','tests/test_network_probe_transport.py','unified_system/lan_probe_inventory.py','unified_system/network_deployment_guard.py','unified_system/network_probe_transport.py']
def git(*args):return subprocess.check_output(['git','-C',str(repo),*args])
hashes={}
for p in paths:
 raw=git('show',head+':'+p);assert raw==(repo/p).read_bytes() and raw==git('show',parent+':'+p);hashes[p]=hashlib.sha256(raw).hexdigest()
def identity():
 values=[]
 for row in git('ls-tree','-rz',head).split(b'\0'):
  if not row:continue
  meta,name=row.split(b'\t',1);mode,kind,oid=meta.split();raw=(repo/name.decode()).read_bytes();assert kind==b'blob' and hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==oid.decode();values.append([name.decode(),hashlib.sha256(raw).hexdigest()])
 return hashlib.sha256(json.dumps(values).encode()).hexdigest()
before=identity();sys.dont_write_bytecode=True;sys.path.insert(0,str(repo));os.chdir(repo)
_popen=subprocess.Popen;spawns=[]
def guarded_popen(args,*a,**kw):
 command=args if isinstance(args,str) else ' '.join(map(str,args))
 if 'ssh.exe' in command.lower():
  assert not isinstance(args,str) and '-G' in args,'AUDITOR_REAL_SSH_CONNECTION_FORBIDDEN'
 spawns.append({'kind':'LOCAL_SSH_G_NO_CONNECT' if 'ssh.exe' in command.lower() else 'LOCAL_INERT_PARSER','argv_sha256':hashlib.sha256(command.encode()).hexdigest()})
 return _popen(args,*a,**kw)
subprocess.Popen=guarded_popen
def deny(*args,**kwargs):raise RuntimeError('AUDITOR_NETWORK_CONNECT_FORBIDDEN')
socket.socket.connect=deny;socket.socket.connect_ex=deny
modules=['tests.test_lan_probe_inventory','tests.test_network_probe_transport','tests.test_network_deployment_guard','tests.test_network_broker_boundary']
with (out/'tests.log').open('w',encoding='utf-8') as stream:
 result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(n) for n in modules))
assert result.wasSuccessful() and not result.skipped
# Original fake transport exposes the fixed outgoing script payload, never executes it.
from tests.test_network_probe_transport import TransportTests,FakeRunner
case=TransportTests('test_success_requires_second_channel_exit_evidence');case.setUp()
try:
 runner=FakeRunner();observation=case.transport(runner).observe('PC1');assert len(runner.calls)==2
 command=runner.calls[0][0][-1];packed=re.search(r'set UNIFIED_NP_[a-f0-9]{32}=([A-Za-z0-9+/=]+)&',command)[1];payload=gzip.decompress(base64.b64decode(packed)).decode()
 assert 'https://api.bybit.com/v5/market/time' in payload
except:raise
finally:case.doCleanups()
# Derived endpoint negatives: Tailscale CGNAT, public, loopback and link-local are rejected.
from tests.test_lan_probe_inventory import InventoryTests
from unified_system.lan_probe_inventory import LanInventoryBlocked
derived=[]
for address in ('100.64.0.1','8.8.8.8','127.0.0.1','169.254.1.1','224.0.0.1'):
 fixture=InventoryTests('test_identity_and_endpoint_owner_callbacks_are_literal_and_current');fixture.setUp()
 try:
  fixture.fixture.data['nodes'][0]['address']=address;fixture.fixture.repin()
  try:
   with fixture.inventory.lease('PC1'):pass
  except LanInventoryBlocked:derived.append({'address':address,'result':'REJECTED_BEFORE_ANY_CONNECTION'})
  else:raise AssertionError('BAD_ENDPOINT_ADMITTED')
 finally:fixture.doCleanups()
subprocess.Popen=_popen
after=identity();assert before==after
ps=(repo/'scripts/network_readonly_probe.ps1').read_text();assert "$request.AllowAutoRedirect=$false" in ps
provider={'fixed_provider_GET_present':True,'payload_observed_in_fake_runner':True,'actual_provider_requests_by_auditor':0,'source_and_SSH_only_admission_allows_fixed_recipe_preparation':True,'per_request_budget_policy_reservation_interface_in_reviewed_paths':'ABSENT','inert_bootstrap_compatible':False,'required_operational_admission':'Separate exact provider policy/budget/usage/UNKNOWN gate required before invoking probe; source/endpoint/identity authorization alone is not provider quota authorization.'}
report={'head':head,'tree':git('rev-parse','HEAD^{tree}').decode().strip(),'original_component':parent,'eight_raw_git_paths_equal_original':hashes,'source_raw_pre_post':[before,after],'focused_tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'derived_endpoint_negatives':derived,'local_processes':spawns,'provider_boundary':provider,'network_repair_or_service_privilege_expansion_identified':'NONE_IN_EIGHT_PATHS','authority_roles':'SOURCE_INVENTORY_CALLBACKS_ARE_REQUIRED_EXTERNAL_TRUST_SEAMS_NOT_NATIVE_AUTHENTICATION_PROOF','remote_cleanup':'ONLY_MATCHED_OWN_HELPER_HANDLE_UNKNOWN_STICKY_NOT_HARD_REMOTE_KILL_GUARANTEE','actual_LAN_or_mTLS_or_route_independence':'NOT_RUN_NOT_QUALIFIED','office_commands_executed':False,'network_connections_by_auditor':0,'native_services_or_acl_changes':False,'overall':'NO_GO'}
(out/'network-source-review.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
