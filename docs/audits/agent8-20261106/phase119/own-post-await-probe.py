import sys,os,json,unittest
sys.path[:0]=[str(sys.argv[1]),str(sys.argv[1])+'/tests/coordination/assignment_v1',str(sys.argv[2]),str(sys.argv[2])+'/tests/gateway_research_identity']
import test_native_job_negative as source
from unified_system.gateway_research_identity import ResearchIdentityDenied
class PostAwaitProbe(source.NativeJobNegativeTests):
 async def test_actual_context_invalidated_after_read_never_emits_resource_observation(self):
  fired=[]
  async def close_after_actual_read(response):
   if response.request.url.path!='/v1/txn' or fired:return
   operations=json.loads(response.request.content)
   if not operations or not all(x.get('KV',{}).get('Verb')=='get-or-empty' for x in operations):return
   if not any(x['KV']['Key']==self.prefix+'jobs/'+self.job for x in operations):return
   await response.aread()
   fired.append(dict(actual_read_operations=len(operations),job_key_in_same_read=True,response_untouched=True))
   await self.broker.invalidate_context(self.context)
  self.authority.client.event_hooks['response'].append(close_after_actual_read)
  with self.assertRaises(ResearchIdentityDenied):
   await self.handler.submit(self.raw,context=self.context,leader=self.leader)
  self.assertEqual(len(fired),1)
  self.assertIsNone(await self.authority._request('GET','/v1/kv/'+self.prefix+'jobs/'+self.job,params={'consistent':''},missing_ok=True))
  print(json.dumps(dict(scope='A8_ACTUAL_POST_AWAIT_CONTEXT_INVALIDATION_NEGATIVE_ONLY',observations=fired,actual_exception='ResearchIdentityDenied',resource_observation_returned=False,job_key_absent=True,native_effect_permission=False)),flush=True)
suite=unittest.TestSuite([PostAwaitProbe('test_actual_context_invalidated_after_read_never_emits_resource_observation')]);result=unittest.TextTestRunner(verbosity=2).run(suite);assert result.wasSuccessful() and result.testsRun==1 and not result.skipped
