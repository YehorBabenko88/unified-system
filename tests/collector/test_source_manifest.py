import copy,json,unittest
from unified_system import collector_offline as co

def fixture():
 return dict(schema='unified.collector.integration-manifest.v2',execution_scope='SYNTHETIC_OFFLINE',permissions=dict.fromkeys(('real_provider_sends','service_creation','acl_changes','production_sql','training','trading','public_submit','authority_mutation'),False),sources={'market_data':{'commit':'a'*40}})

def encoded(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode('ascii')

class SourceManifestTests(unittest.TestCase):
 def test_canonical_data_source_revision_is_unattested_metadata_only(self):
  self.assertEqual(co._market_data_revision(encoded(fixture())),'a'*40)
 def test_retired_or_ambiguous_owners_and_permissions_are_refused(self):
  base=fixture()
  variants=[]
  old=copy.deepcopy(base);old['schema']='unified.collector.integration-manifest.v1';old['new_components']=[{'owner':'A3','head':'a'*40}];variants.append(old)
  for source in ({'grid':{'commit':'a'*40}},{'market_data':{'commit':'a'*40},'grid':{'commit':'a'*40}},{'market_data':{'commit':'a'*40,'head':'b'*40}}):
   v=copy.deepcopy(base);v['sources']=source;variants.append(v)
  for permission in base['permissions']:
   v=copy.deepcopy(base);v['permissions'][permission]=True;variants.append(v)
  for value in variants:
   with self.subTest(value=value),self.assertRaises(co.CollectorOfflineBlocked):co._market_data_revision(encoded(value))
 def test_duplicate_json_and_invalid_revision_refused(self):
  for value in (b'{"schema":"a","schema":"b"}',b'[]',b'{"x":NaN}'):
   with self.assertRaises(co.CollectorOfflineBlocked):co._market_data_revision(value)
  for revision in ('A'*40,'a'*39,True,None):
   value=fixture();value['sources']['market_data']['commit']=revision
   with self.assertRaises(co.CollectorOfflineBlocked):co._market_data_revision(encoded(value))
