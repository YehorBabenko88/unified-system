import pathlib,subprocess
r=pathlib.Path.cwd();o=r/'outputs/phase75';repo=r/'work/review-a5-red1bb6'
s='''import pathlib,sys,asyncio,dataclasses,uuid,json
sys.path.insert(0,str(pathlib.Path.cwd()/'tests'));import test_agent5_assignment_backend_contract as t
u=str(uuid.uuid4());base=t.ScenarioObservation('UNKNOWN','UNKNOWN','REJECTED',0,0,0,0,'1','1',u,u,None,None,())
async def accepts(record):
 case=t.ActualAssignmentBackendContracts('test_native_no_quorum_preserves_original_intent_without_mutation')
 class OnlyObservation:
  async def run_scenario(self,name):return record
 case.fixture=OnlyObservation()
 try:await case.scenario('A8_META_ONLY_NOT_NATIVE_SCENARIO');return True
 except AssertionError:return False
async def main():
 bad=0;good=0
 for field in ['assignment_effects','publication_effects','debit_effects','checkpoint_effects']:
  for n in [True,-1,2]:assert not await accepts(dataclasses.replace(base,**{field:n}));bad+=1
 for status_field,effect_field in [('assignment_status','assignment_effects'),('publication_status','publication_effects')]:
  for status in ['UNKNOWN','UNAVAILABLE']:
   for n in [0,1]:assert await accepts(dataclasses.replace(base,**{status_field:status,effect_field:n}));good+=1
  for status,n in [('COMMITTED',0),('REJECTED',1),('INVENTED',0)]:assert not await accepts(dataclasses.replace(base,**{status_field:status,effect_field:n}));bad+=1
 print(json.dumps(dict(scope='ASSERTION_META_ONLY_NO_ACTUAL_NATIVE_FIXTURE',invalid_count_status_cases_refused=bad,uncertain_zero_or_one_cases_allowed=good,native_acceptance='NOT_RUN'),indent=2))
asyncio.run(main())
'''
(o/'field-semantics-executed.py').write_text(s,encoding='utf-8');p=subprocess.run([str(r/'work/audit-venv/Scripts/python.exe'),'-I','-B','-c',s],cwd=repo,capture_output=True,timeout=30);(o/'field-semantics.stdout.json').write_bytes(p.stdout);(o/'field-semantics.stderr.log').write_bytes(p.stderr);assert p.returncode==0,p.stderr;print(p.stdout.decode())
