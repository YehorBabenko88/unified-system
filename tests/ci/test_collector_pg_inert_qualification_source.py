"""Pure controls of optional89 qualification source; no PG effects."""
import ast,importlib.util,unittest
from pathlib import Path
ROOT=Path(__file__).absolute().parents[2]
spec=importlib.util.spec_from_file_location('pg_lane',ROOT/'tools/collector/qualify_pg_inert.py');q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
class SourceControls(unittest.TestCase):
 def test_class_filter_keeps_readiness12_separate_from_same_file49(self):
  custody=['pg.PgCustodyTests.test_'+str(i) for i in range(37)]
  readiness=['pg.ServerReadinessTests.test_'+str(i) for i in range(12)]
  self.assertEqual(q.class_ids(custody+readiness,'pg','PgCustodyTests',37),custody)
  self.assertEqual(q.class_ids(custody+readiness,'pg','ServerReadinessTests',12),readiness)
 def test_class_filter_rejects_missing_duplicate_wrong_count_and_alias(self):
  ids=['pg.ServerReadinessTests.test_'+str(i) for i in range(12)]
  for actual,count in [(ids[:-1],12),(ids+ids[:1],12),(ids,49),([s.replace('Tests.','TestsAlias.') for s in ids],12),([object()],1)]:
   with self.assertRaises(ValueError):q.class_ids(actual,'pg','ServerReadinessTests',count)
 def test_staging_deduplicates_shared_qualification_file(self):
  paths=q.staged_paths();self.assertEqual(len(paths),6);self.assertEqual(len(set(paths)),6)
  self.assertEqual(paths.count('tests/collector/test_pg_qualification.py'),1)
 def test_child_embeds_all_five_exact_groups_without_stale_counts(self):
  tree=ast.parse(q.INERT_SOURCE)
  loop=next(node for node in tree.body if isinstance(node,ast.For) and isinstance(node.target,ast.Tuple) and any(isinstance(n,ast.Name) and n.id=='module_name' for n in node.target.elts))
  self.assertEqual(ast.literal_eval(loop.iter),q.GROUPS)
  self.assertEqual([r[3] for r in q.GROUPS],[37,12,2,19,19]);self.assertIn('INERT89_ONLY',q.INERT_SOURCE);self.assertNotIn('INERT73',q.INERT_SOURCE)
 def test_updated_owner_pins_are_only_qualification_and_writer(self):
  self.assertEqual(len(q.ACTIVE),14)
  self.assertEqual(q.ACTIVE['tools/collector/pg_qualification.py'],'23c109cdede68e39d51bbb27431d2bde49d08568a34dceb47227714bf2ddfd1b')
  self.assertEqual(q.ACTIVE['tools/collector/pg_private_writer.py'],'e14455f6fd1947646f848aaf2d867dc5fd01e50e7a3822d31a8201e3fffe4660')
  self.assertEqual(q.ACTIVE['tools/collector/pg_protocol.py'],'e73811777525142fb340e994e9a68aee63806c296d264ac36390fbfa3440e884')
 def test_retired_nonzero_child_handle_is_closed(self):
  calls=[]
  class Handle:
   def Close(self):calls.append('close')
  class Child:
   _handle=Handle()
   def poll(self):return 1
   def wait(self,timeout):calls.append(('wait',timeout));return 1
   def kill(self):raise AssertionError('retired child must not be killed')
  self.assertEqual(q.retire_held([Child()]),[]);self.assertEqual(calls,[('wait',0),'close'])
 def test_unknown_poll_still_attempts_kill_wait_and_close(self):
  calls=[]
  class Handle:
   def Close(self):calls.append('close')
  class Child:
   _handle=Handle()
   def poll(self):raise RuntimeError('inert')
   def kill(self):calls.append('kill');raise RuntimeError('inert')
   def wait(self,timeout):calls.append(('wait',timeout));return 1
  self.assertEqual(q.retire_held([Child()]),['HELD_POLL_UNKNOWN','HELD_KILL_UNKNOWN']);self.assertEqual(calls,['kill',('wait',0),'close'])
 def test_exact89_ids_no_alias_duplicates_or_omissions(self):
  ids=['a'+str(i) for i in range(89)];q.check_results(ids,[{'id':i,'outcome':'PASS'} for i in ids],89,0,0,0,0,0)
  for actual in (ids[:-1],ids[:-1]+[ids[0]],ids[:-1]+['foreign']):
   with self.assertRaises(ValueError):q.check_results(ids,[{'id':i,'outcome':'PASS'} for i in actual],89,0,0,0,0,0)
 def test_test_flags_never_pass(self):
  ids=['a'+str(i) for i in range(89)]
  for field in range(1,6):
   flags=[89,0,0,0,0,0];flags[field]=1
   with self.assertRaises(ValueError):q.check_results(ids,[{'id':i,'outcome':'PASS'} for i in ids],*flags)
 def test_capture_unknown_overflow_nonzero_or_unretired_denies(self):
  good={'returncode':0,'reason':None,'errors':[],'retired':True};q.check_capture(good)
  for k,v in [('returncode',1),('reason','OUTPUT_LIMIT'),('errors',['READER_UNKNOWN']),('retired',False)]:
   with self.assertRaises(ValueError):q.check_capture(dict(good,**{k:v}))
 def test_source_and_supplier_roles_are_closed(self):
  q.check_supplier(q.HELPER_HEAD,q.HELPER_TREE,q.COLLECTOR_SHA)
  for values in [('a'*40,q.HELPER_TREE,q.COLLECTOR_SHA),(q.HELPER_HEAD,'b'*40,q.COLLECTOR_SHA),(q.HELPER_HEAD,q.HELPER_TREE,'c'*64)]:
   with self.assertRaises(ValueError):q.check_supplier(*values)
 def test_active14_pins_do_not_accept_sdk_substitution(self):
  source={'files':{path:{'sha256':sha} for path,sha in q.ACTIVE.items()}};q.check_active(source)
  source['files']['unified_system/lab_release.py']['sha256']='432108bdb03344331c9badccb2f331f768d6d2625b28263d3c8f74de45a81b99'
  with self.assertRaises(ValueError):q.check_active(source)
 def test_source_supplier_output_layout_rejects_overlap(self):
  q.check_layout(Path('/source'),Path('/helpers'),Path('/out'))
  for args in [(Path('/source'),Path('/source'),Path('/out')),(Path('/source'),Path('/helpers'),Path('/source/out'))]:
   with self.assertRaises(ValueError):q.check_layout(*args)
 def test_exact_groups_are_37_12_19_19(self):self.assertEqual([r[3] for r in q.GROUPS],[37,12,2,19,19])
 def test_workflow_has_two_pinned_readonly_inputs_and_no_dispatch(self):
  text=(ROOT/'.github/workflows/collector-pg-inert-qualified.yml').read_text();self.assertIn('contents: read',text);self.assertIn('fail-fast: false',text);self.assertNotIn('workflow_dispatch:',text);self.assertEqual(text.count('persist-credentials: false'),2);self.assertIn(q.HELPER_HEAD,text);self.assertIn('inert89',text);self.assertNotIn('inert73',text)
if __name__=='__main__':unittest.main()
