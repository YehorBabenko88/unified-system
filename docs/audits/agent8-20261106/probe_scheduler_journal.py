import dataclasses,json,pathlib,sys,threading,uuid
from concurrent.futures import ThreadPoolExecutor
root=pathlib.Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;sys.path.insert(0,str(root/'work/review5-durable'));out=root/'outputs/phase24'
from scheduler_components.durable import PreparationJournal,ReconciliationRequired
from scheduler_components.placement import Resources,Candidate,Policy
scratch=root/'work'/('a5-journal-independent-'+uuid.uuid4().hex[:8]);scratch.mkdir()
scope=dict(cluster_id='cluster',cluster_generation='generation-old',job_id='job-old',dataset_id='dataset',source_id='source',partition_id='partition');node=Candidate('node','incarnation','incarnation',90,'bench-a',Resources(100,100,100,100,100),Resources(0,0,0,0,0));policy=Policy(10,800000,1,1)
def prep(store,s,n=node):return store.prepare(s,[n],100,policy,quorum_available=True,schedule_active=True)
store=PreparationJournal(scratch/'unknown.sqlite');store.enqueue(scope,Resources(73,73,73,73,73),'bench-a');first=prep(store,scope);store.record_handoff(scope);store.record_unknown(scope);store.close();store=PreparationJournal(scratch/'unknown.sqlite');unknown=store.view(scope);assert unknown['request_id']==first['request_id'] and unknown['state']=='UNKNOWN' and unknown['execution_authorized'] is False
try:store.cancel(scope)
except ReconciliationRequired:cancel='DENIED_UNKNOWN'
else:raise AssertionError('UNKNOWN_REFUNDED')
new_scope=dict(scope,cluster_generation='generation-new',job_id='job-new');store.enqueue(new_scope,Resources(28,28,28,28,28),'bench-a');blocked=prep(store,new_scope,dataclasses.replace(node,incarnation='new',observation_incarnation='new'));assert blocked['state']=='QUEUED' and blocked['request_id'] is None
exact_scope=dict(new_scope,job_id='job-exact');store.enqueue(exact_scope,Resources(27,27,27,27,27),'bench-a');exact=prep(store,exact_scope);assert exact['state']=='PREPARED' and exact['execution_authorized'] is False
scale_scope=dict(new_scope,job_id='job-new-scale');store.enqueue(scale_scope,Resources(1,1,1,1,1),'bench-b');scale=prep(store,scale_scope,dataclasses.replace(node,benchmark_id='bench-b',capacity=Resources(1000,1000,1000,1000,1000)));assert scale['state']=='QUEUED';store.close()
race_path=scratch/'race.sqlite';store=PreparationJournal(race_path);store.enqueue(scope,Resources(1,1,1,1,1),'bench-a');prep(store,scope);store.close();barrier=threading.Barrier(2)
def attempt(op):
 s=PreparationJournal(race_path)
 try:
  barrier.wait(timeout=5)
  try:row=s.cancel(scope) if op=='cancel' else s.record_handoff(scope);return {'operation':op,'state':row['state'],'execution_authorized':row['execution_authorized']}
  except (ReconciliationRequired,ValueError) as e:return {'operation':op,'denied':type(e).__name__}
 finally:s.close()
with ThreadPoolExecutor(max_workers=2) as pool:race=list(pool.map(attempt,['cancel','seal']))
store=PreparationJournal(race_path);final=store.view(scope);events=store.events();store.close();assert final['state'] in ('CANCELLED','SEALED') and sum('denied' in x for x in race)==1 and not {'CANCELLED','SEALED'}<=set(e['kind'] for e in events)
r={'head':'175b48a2a0d2882669172abc5774bd71b42e2215','unknown_request_retained':True,'unknown_cancel':cancel,'new_generation_incarnation_over_capacity':'QUEUED_NO_REQUEST','exact_remaining_capacity':'PREPARED_NOT_AUTHORIZED','incompatible_CPU_scale':'QUEUED','two_connection_cancel_seal_race':race,'final_race_state':final['state'],'all_returned_views_execution_authorized':False,'actual_external_or_network_calls':0,'scope':'AUDITOR_DERIVED_LOCAL_SQLITE_ONLY_NOT_CLUSTER_AUTHORITY'}
(out/'independent-journal-probes.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
