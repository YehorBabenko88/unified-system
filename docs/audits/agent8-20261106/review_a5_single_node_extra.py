"""Independent sync ABI and same-context history models; never actual worker dispatch."""
import json,os,pathlib,subprocess,textwrap
r=pathlib.Path(__file__).resolve().parents[1];repo=r/'work/review-a5-single7a418';out=r/'outputs/phase59';head='7a4185924d4702ade53f518644e45d6ee4f6f451';workflow=(repo/'.github/workflows/agent5-components.yml').read_text(encoding='utf-8');code=textwrap.dedent(workflow.split("          python -I -B - <<'PY'\n",1)[1].split('          PY',1)[0]);guard=code.split("expected = os.environ['EXPECTED_SOURCE_SHA']",1)[0];folder=out/'independent';folder.mkdir()
extra='''
assert before['protected_inputs_valid'] and before['head']==os.environ['EXPECTED_SOURCE_SHA']
sys.path[:0]=[str(Path.cwd()),str(Path.cwd()/'tests')]
import inspect,types
from scheduler_components.single_node import _require,SingleNodeScheduler
from scheduler_components.runtime import Unavailable
from scheduler_components.attempt_registry import AttemptRegistry
from test_agent5_single_node import ModelOwners,context,request,uid
results=[]
def rejected(name,owner):
 try:_require(owner,'check')
 except Unavailable:results.append(name)
 else:raise AssertionError(name)
_require(types.SimpleNamespace(check=lambda:None),'check');results.append('None_contract_only_not_admission')
for flag in [False,True]:rejected('boolean_'+str(flag),types.SimpleNamespace(check=lambda:flag))
called=[]
async def guard_async():called.append('BODY')
rejected('async_function_not_invoked',types.SimpleNamespace(check=guard_async));assert not called
class AsyncCallable:
 async def __call__(self):called.append('CALLABLE_BODY')
rejected('async_callable_not_invoked',types.SimpleNamespace(check=AsyncCallable()));assert not called
created=guard_async();rejected('unstarted_coroutine_discarded_not_awaited',types.SimpleNamespace(check=lambda:created));assert inspect.getcoroutinestate(created)==inspect.CORO_CLOSED and not called
class Pending:
 def __await__(self):called.append('AWAIT');yield
rejected('custom_awaitable_never_awaited',types.SimpleNamespace(check=lambda:Pending()));assert not called
cleanup=[]
async def suspended_owner():
 try:await Pending()
 finally:cleanup.append('FINALLY')
coro=suspended_owner();coro.send(None);called.clear();rejected('suspended_coroutine_cleanup_not_run_by_wrapper',types.SimpleNamespace(check=lambda:coro));assert cleanup==[] and inspect.getcoroutinestate(coro)==inspect.CORO_SUSPENDED
coro.close();assert cleanup==['FINALLY'] # Explicit owner-test cleanup only.
db=Path(os.environ['TEMP'])/'a8-single-history.db';registry=AttemptRegistry(db);owners=ModelOwners();pilot=SingleNodeScheduler(context(),registry,admission=owners,authority=owners,storage=owners,native=owners);pilot.attach_owned_worker(b'MODEL_REF',b'MODEL_CONTROL_ONLY');pilot.submit(request());original=registry.get(uid(5));initialexec=[x for x in owners.calls if x[0]=='execute']
history=SingleNodeScheduler(context(),registry,admission=owners,authority=owners,storage=None,native=None);assert history.reconcile(uid(5))['state']=='UNKNOWN' and [x for x in owners.calls if x[0]=='execute']==initialexec and owners.worker.starts==[];results.append('same_context_history_without_storage_native_no_execute_or_start')
for name,changes in [('generation',dict(cluster_generation=uid(99))),('incarnation',dict(worker_incarnation_id=uid(99)))]:
 other=SingleNodeScheduler(context(**changes),registry,admission=owners,authority=owners,storage=owners,native=owners);calls=list(owners.calls)
 try:other.reconcile(uid(5))
 except (ValueError,Unavailable):pass
 else:raise AssertionError(name)
 assert owners.calls==calls and registry.get(uid(5))==original;results.append('changed_'+name+'_history_rejected_not_continuity')
old_context=registry.db.execute('SELECT context FROM single_node_context WHERE singleton=1').fetchone()[0];other=SingleNodeScheduler(context(cluster_generation=uid(99)),registry,admission=owners,authority=owners,storage=owners,native=owners)
try:other.attach_owned_worker(b'MODEL_REF',b'MODEL_CONTROL_ONLY')
except Unavailable:pass
else:raise AssertionError('REBOUND_JOURNAL')
assert registry.db.execute('SELECT context FROM single_node_context WHERE singleton=1').fetchone()[0]==old_context;results.append('generation_attachment_cannot_rebind_journal')
unattached=SingleNodeScheduler(context(),registry)
try:unattached.drain(uid(5))
except Unavailable:pass
else:raise AssertionError('NO_NATIVE_DRAIN_SUCCESS')
afterrow=registry.get(uid(5));assert afterrow['drain_requested']==1 and {k:v for k,v in afterrow.items() if k!='drain_requested'}=={k:v for k,v in original.items() if k!='drain_requested'} and owners.worker.pauses==owners.worker.starts==[];results.append('unattached_drain_intent_only_no_release_or_pause')
registry.close();after=source();assert after==before and after['protected_inputs_valid'];assert len(results)==13
(out/'extra-models.json').write_text(json.dumps(dict(head=before['head'],cases=results,scope='MODEL_ONLY_NOT_NATIVE_API_COMPATIBILITY',worker_starts=0,raw_before_after=339,history_scope='EXACT_CONTEXT_GENERATION_INCARNATION_ONLY_NO_CROSS_GENERATION_CONTINUITY',skips=0),indent=2),encoding='utf-8')
'''
env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')};temp=r/'work/a5-single-extra-temp';temp.mkdir();env.update(EXPECTED_SOURCE_SHA=head,EVIDENCE_DIR=str(folder),TEMP=str(temp),TMP=str(temp),GIT_CONFIG_COUNT='2',GIT_CONFIG_KEY_0='core.autocrlf',GIT_CONFIG_VALUE_0='false',GIT_CONFIG_KEY_1='core.eol',GIT_CONFIG_VALUE_1='lf');p=subprocess.run([str(r/'work/audit-venv/Scripts/python.exe'),'-I','-B','-c',guard+extra],cwd=repo,env=env,capture_output=True,timeout=60);(out/'extra.stdout.log').write_bytes(p.stdout);(out/'extra.stderr.log').write_bytes(p.stderr);assert p.returncode==0,p.stderr.decode(errors='replace')[-2500:];print((folder/'extra-models.json').read_text(encoding='utf-8'))
