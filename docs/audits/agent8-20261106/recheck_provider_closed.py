import asyncio,hashlib,json,os,pathlib,socket,subprocess,sys,unittest
root=pathlib.Path(__file__).resolve().parents[1];repo=root/'work/review-network-f14';out=root/'outputs/phase22';out.mkdir(exist_ok=True);head='15dd9e8340cc332204ebbe6c13744f797ceca2f4';base='2b0a500245c7bb661abdfc50c08e4aab1575ade2'
def git(*args):return subprocess.check_output(['git','-C',str(repo),*args])
assert set(git('diff','--name-only',base,head).decode().splitlines())=={'scripts/network_readonly_probe.ps1','tests/test_network_probe_provider_closed.py','docs/network/provider-probe-admission-safety.md'}
frozen='unified_system/network_deployment_guard.py';assert git('show',head+':'+frozen)==git('show',base+':'+frozen)==git('show','0346018b58ed612dbe62fba7861f3e0b6a63ee94:'+frozen)
def identity():
 rows=[]
 for row in git('ls-tree','-rz',head).split(b'\0'):
  if not row:continue
  meta,name=row.split(b'\t',1);mode,kind,oid=meta.split();raw=(repo/name.decode()).read_bytes();assert kind==b'blob' and hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==oid.decode();rows.append([name.decode(),hashlib.sha256(raw).hexdigest()])
 return hashlib.sha256(json.dumps(rows).encode()).hexdigest()
before=identity();sys.dont_write_bytecode=True;sys.path[:0]=[str(repo),str(repo/'tests')];os.chdir(repo)
original=subprocess.Popen
def guarded(argv,*args,**kwargs):
 text=argv if isinstance(argv,str) else ' '.join(map(str,argv))
 if 'ssh.exe' in text.lower():assert not isinstance(argv,str) and '-G' in argv,'REAL_SSH_FORBIDDEN'
 return original(argv,*args,**kwargs)
subprocess.Popen=guarded
def deny(*a,**k):raise RuntimeError('NETWORK_CONNECTION_FORBIDDEN')
socket.socket.connect=deny;socket.socket.connect_ex=deny
names=['tests.test_lan_probe_inventory','tests.test_network_probe_transport','tests.test_network_deployment_guard','tests.test_network_broker_boundary','tests.test_network_probe_provider_closed']
with (out/'regressions.log').open('w',encoding='utf-8') as stream:result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(n) for n in names))
assert result.wasSuccessful() and not result.skipped
subprocess.Popen=original;after=identity();assert before==after
r={'head':head,'tree':git('rev-parse','HEAD^{tree}').decode().strip(),'base':base,'diff_scope':'THREE_FILES_PS_EIGHT_INSERTED_LINES_NEW_TEST_DOC','frozen_v1_guard_unchanged':True,'old_tests_assertions_unchanged':True,'focused_tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skips':len(result.skipped),'source_raw_pre_post':[before,after],'independent_original_oracle':'phase22/provider-gap-review.json_3ZERO_SENTINEL_HITS_4NOT_RUN','new_native_free_test':'6BLOCKED_TARGETS_ZERO_IO_GENERAL_TARGET_SENTINEL1_RETURN_DOMINANCE_V1_DENIAL','actual_network_or_office_calls':0,'F14':'FIX_VERIFIED_OFFLINE_EXACT_SOURCE','provider_runtime_budget_manager':'NOT_IMPLEMENTED_NOT_QUALIFIED_PROVIDER_DISABLED','inert_bootstrap':'NOT_QUALIFIED','hosted':'NOT_QUALIFIED','physical':'BLOCKED','overall':'NO_GO'}
(out/'provider-closed-review.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
