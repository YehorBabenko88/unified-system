import copy,unittest
from unified_system.network_deployment_guard import NetworkDeploymentGuard, NetworkBlocked, ROW_KEYS

def observation():
 return dict(schema='unified.network-readonly-observation.v1',computer='PC1',
  started_utc='2026-11-05T15:00:00+00:00',finished_utc='2026-11-05T15:00:01+00:00',
  mutations=False,configuration={key:([{field:('fixture' if field=='Name' else None)for field in fields}]
   if key!='firewall'else[{field:(name if field=='Name'else 1)for field in fields}for name in('Domain','Private','Public')])
   for key,fields in ROW_KEYS.items()},
  checks=[dict(host='www.microsoft.com',dns='PASS',tcp443='PASS',https='PASS',api='NOT_RUN'),
   dict(host='api.bybit.com',dns='PASS',tcp443='PASS',https='PASS',api='PASS')])

class NetworkGuardTests(unittest.TestCase):
 def test_validation_clock_is_captured_after_blocking_observer_returns(self):
  clock=[1793890800.]
  def observe():clock[0]=1793890802.;return observation()
  guard=NetworkDeploymentGuard('PC1','operation',observe=observe,record=lambda _:None,now=lambda:clock[0])
  guard.begin()
 def test_incomplete_configuration_cannot_establish_baseline(self):
  for key in ('adapters','interfaces','addresses','dns','routes','firewall','services'):
   data=observation();del data['configuration'][key]
   with self.subTest(key=key),self.assertRaises(NetworkBlocked):self.guard(data).begin()
 def guard(self,source=None):
  self.source=source or observation();self.receipts=[];self.calls=[]
  def collect():self.calls.append('observe');return copy.deepcopy(self.source)
  return NetworkDeploymentGuard('PC1','owned-operation',observe=collect,record=self.receipts.append,now=lambda:1793890802.)
 def test_baseline_and_post_are_timestamped_hashed_observations_not_network_actions(self):
  guard=self.guard();guard.begin();guard.checkpoint('AFTER')
  self.assertEqual(self.calls,['observe','observe']);self.assertEqual(len(self.receipts),2)
  for receipt in self.receipts:
   self.assertEqual(receipt['computer'],'PC1');self.assertEqual(len(receipt['observation_sha256']),64)
   self.assertIs(receipt['network_mutations'],False)
 def test_pre_effect_requires_successful_baseline(self):
  with self.assertRaises(NetworkBlocked):self.guard().checkpoint('BEFORE_EFFECT')
 def test_any_failed_connectivity_stops_only_this_operation_and_never_retries(self):
  for host,key in ((0,'dns'),(0,'tcp443'),(0,'https'),(1,'api')):
   guard=self.guard();guard.begin();self.source['checks'][host][key]='FAIL'
   with self.subTest(host=host,key=key),self.assertRaises(NetworkBlocked):guard.checkpoint('BEFORE_EFFECT')
   count=len(self.calls)
   with self.assertRaises(NetworkBlocked):guard.checkpoint('AFTER')
   self.assertEqual(len(self.calls),count)
 def test_changed_dns_or_routes_stops_without_any_repair_callback(self):
  guard=self.guard();guard.begin();self.source['configuration']['routes'][0]['NextHop']='192.0.2.2'
  with self.assertRaisesRegex(NetworkBlocked,'NETWORK_CONFIGURATION_CHANGED'):guard.checkpoint('AFTER')
  self.assertEqual(self.receipts[-1]['decision'],'STOP_CURRENT_DEPLOYMENT')
 def test_wrong_host_stale_future_missing_or_duplicate_check_rejected(self):
  for kind in ('host','stale','future','missing','duplicate','mutation'):
   data=observation()
   if kind=='host':data['computer']='ADMINIT'
   elif kind=='stale':data['finished_utc']='2026-11-04T15:00:01+00:00'
   elif kind=='future':data['finished_utc']='2026-11-06T15:00:01+00:00'
   elif kind=='missing':data['checks'].pop()
   elif kind=='duplicate':data['checks'].append(data['checks'][0])
   else:data['mutations']=True
   with self.subTest(kind=kind),self.assertRaises(NetworkBlocked):self.guard(data).begin()
 def test_observer_or_evidence_failure_stops_before_another_effect(self):
  for callback in ('observe','record'):
   guard=self.guard()
   def fail(*args):raise OSError('inert fault')
   setattr(guard,'_'+callback,fail)
   with self.subTest(callback=callback),self.assertRaises(NetworkBlocked):guard.begin()
   self.assertTrue(guard.stopped)
 def test_adminit_and_unknown_nodes_are_not_accepted(self):
  for node in ('ADMINIT','AMINIT','localhost','pc1','PC5'):
   with self.subTest(node=node),self.assertRaises(NetworkBlocked):
    NetworkDeploymentGuard(node,'operation',observe=observation,record=lambda _:None)

if __name__=='__main__':unittest.main()
