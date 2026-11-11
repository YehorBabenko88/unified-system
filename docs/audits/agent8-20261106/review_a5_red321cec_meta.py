import pathlib,subprocess
r=pathlib.Path.cwd();repo=r/'work/review-a5-red321cec';o=r/'outputs/phase74'
s='''import pathlib,sys,asyncio,dataclasses,json,uuid
sys.path.insert(0,str(pathlib.Path.cwd()/'tests'))
import test_agent5_assignment_backend_contract as t
u=str(uuid.uuid4())
def observation(**changes):
 d=dict(assignment_status='COMMITTED',publication_status='REJECTED',supersession_status='COMMITTED',assignment_effects=1,publication_effects=0,debit_effects=0,checkpoint_effects=0,assignment_revision_before='1',assignment_revision_after='2',original_request_id=u,observed_request_id=u,historical_receipt_before=None,historical_receipt_after=None,native_linearization_order=('SUPERSESSION',));d.update(changes);return t.ScenarioObservation(**d)
async def check(method,record):
 case=t.ActualAssignmentBackendContracts(method)
 class InertObservationOnly:
  async def run_scenario(self,name):return record
 case.fixture=InertObservationOnly()
 try:await getattr(case,method)();return True
 except AssertionError:return False
async def main():
 method='test_concurrent_supersession_publication_has_one_native_order'
 positive=observation(publication_status='COMMITTED',publication_effects=1,debit_effects=1,checkpoint_effects=1,historical_receipt_before=b'inert',historical_receipt_after=b'inert',native_linearization_order=('PUBLICATION','SUPERSESSION'))
 assert await check(method,positive)
 negative=[dataclasses.replace(positive,debit_effects=2),dataclasses.replace(positive,observed_request_id=str(uuid.uuid4())),dataclasses.replace(positive,historical_receipt_after=b'changed'),dataclasses.replace(positive,native_linearization_order=('SUPERSESSION','PUBLICATION'))]
 for record in negative:assert not await check(method,record)
 gap=await check(method,dataclasses.replace(positive,assignment_effects=99));assert not gap
 print(json.dumps(dict(scope='UNTRUSTED_OBSERVATION_ASSERTION_META_PROBES_ONLY_NOT_NATIVE_FIXTURE_OR_ACCEPTANCE',native_bodies_via_real_binding=0,valid_publication_first_both_committed_assertion_accepts=True,bad_debit_UUID_history_order_refused=4,assignment_effects99_still_accepted=gap,missing_assignment_effect_zero_refused=not await check(method,dataclasses.replace(positive,assignment_effects=0)),contradictory_assignment_status_refused=not await check(method,dataclasses.replace(positive,assignment_status='REJECTED')),required_owner_clarification='Define assignment_effects per tested original command and assert bound for supersession/concurrent scenarios before future native qualification'),indent=2))
asyncio.run(main())
'''
(o/'observation-meta-executed.py').write_text(s,encoding='utf-8');p=subprocess.run([str(r/'work/audit-venv/Scripts/python.exe'),'-I','-B','-c',s],cwd=repo,capture_output=True,timeout=30);(o/'observation-meta.stdout.json').write_bytes(p.stdout);(o/'observation-meta.stderr.log').write_bytes(p.stderr);assert p.returncode==0,p.stderr;print(p.stdout.decode())
