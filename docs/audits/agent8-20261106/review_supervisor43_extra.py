import pathlib,subprocess
r=pathlib.Path.cwd();o=r/'outputs/phase78';repo=r/'work/review-supervisor43'
s='''import pathlib,sys,tempfile,json,dataclasses,hashlib,copy
root=pathlib.Path.cwd();sys.path.insert(0,str(root))
def audit(event,args):
 if event in ('socket.connect','socket.bind','subprocess.Popen','os.system'):raise AssertionError('A8_EXTERNAL_EFFECT_TRIPWIRE:'+event)
sys.addaudithook(audit)
from unified_system import ci_queue_controller as q
from tests.test_supervisor_local_integration import LocalIntegrationTests
from unified_system.supervisor_deployment import DeploymentBlocked
from unified_system.node_task_journal import NodeJournalError
from tests.test_node_task_journal import operation
pin=q.Pin(*q.PROTECTED);denials=0
for key,value in [('repository','Other/repo'),('workflow_id',pin.workflow_id+1),('attempt',2),('source_sha','a'*40),('job_id',pin.job_id+1)]:
 try:dataclasses.replace(pin,**{key:value});raise AssertionError('PROTECTED_TUPLE_ALIAS')
 except ValueError:denials+=1
ordinary=dataclasses.replace(pin,run_id=pin.run_id+1);assert q.authorization(ordinary)=='NOT_APPLICABLE' and q.authorization(pin)=='CONSUMED'
case=LocalIntegrationTests();case.setUp()
try:
 plan=case.deployment.rollout([case.node()]);forged=copy.deepcopy(plan);forged.update(mode='ACTIVATE',effects_authorized=True,trading_authorized=True,physical_acceptance='PASS',rollback_authorized=True)
 try:case.deployment.execute(forged);raise AssertionError('FORGED_PLAN_EXECUTED')
 except DeploymentBlocked:pass
 case.supervisor.submit(operation(operation_type='REQUEST_DRAIN',approval_reference='approved'))
 denied=case.supervisor.run_readonly('task1');assert denied['state']=='BLOCKED' and denied['receipt']['effects_authorized'] is False
 assert plan['source_provenance']=='PINNED_METADATA_ONLY_VERIFY_SOURCES_BEFORE_EXECUTION' and plan['installed_release']=='NOT_OBSERVED'
finally:case.doCleanups()
print(json.dumps(dict(scope='OWN_LOCAL_COMPONENT_API_PROBES_NOT_NATIVE_AUTHORITY',five_protected_tuple_mutations_refused=denials,different_run_authorization='NOT_APPLICABLE',exact_historical_authorization='CONSUMED',forged_positive_deployment_plan_refused=True,drain_approval_reference_does_not_authorize=True,external_network_and_process_tripwire='NO_CALLS',native_acceptance=False),indent=2))
'''
(o/'extra-executed.py').write_text(s,encoding='utf-8');p=subprocess.run([str(r/'work/audit-venv/Scripts/python.exe'),'-I','-S','-B','-c',s],cwd=repo,capture_output=True,timeout=30);(o/'extra.stdout.json').write_bytes(p.stdout);(o/'extra.stderr.log').write_bytes(p.stderr);assert p.returncode==0,p.stderr;print(p.stdout.decode())
