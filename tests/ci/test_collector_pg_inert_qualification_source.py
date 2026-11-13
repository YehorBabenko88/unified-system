"""Pure controls of the new optional73 qualification source; no PG effects."""
import importlib.util,unittest
from pathlib import Path
ROOT=Path(__file__).absolute().parents[2]
spec=importlib.util.spec_from_file_location('pg_lane',ROOT/'tools/collector/qualify_pg_inert.py');q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
class SourceControls(unittest.TestCase):
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
 def test_exact73_ids_no_alias_duplicates_or_omissions(self):
  ids=['a'+str(i) for i in range(73)];q.check_results(ids,[{'id':i,'outcome':'PASS'} for i in ids],73,0,0,0,0,0)
  for actual in (ids[:-1],ids[:-1]+[ids[0]],ids[:-1]+['foreign']):
   with self.assertRaises(ValueError):q.check_results(ids,[{'id':i,'outcome':'PASS'} for i in actual],73,0,0,0,0,0)
 def test_test_flags_never_pass(self):
  ids=['a'+str(i) for i in range(73)]
  for field in range(1,6):
   flags=[73,0,0,0,0,0];flags[field]=1
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
  source['files']['unified_system/lab_release.py']['sha256']='204f8fe279f3db40c8d5b2091a0804663de62e4bfe746fcbf1667886fd384f28'
  with self.assertRaises(ValueError):q.check_active(source)
 def test_source_supplier_output_layout_rejects_overlap(self):
  q.check_layout(Path('/source'),Path('/helpers'),Path('/out'))
  for args in [(Path('/source'),Path('/source'),Path('/out')),(Path('/source'),Path('/helpers'),Path('/source/out'))]:
   with self.assertRaises(ValueError):q.check_layout(*args)
 def test_exact_groups_are_36_19_18(self):self.assertEqual([r[3] for r in q.GROUPS],[36,19,18])
 def test_workflow_has_two_pinned_readonly_inputs_and_no_dispatch(self):
  text=(ROOT/'.github/workflows/collector-pg-inert-qualified.yml').read_text();self.assertIn('contents: read',text);self.assertIn('fail-fast: false',text);self.assertNotIn('workflow_dispatch:',text);self.assertEqual(text.count('persist-credentials: false'),2);self.assertIn(q.HELPER_HEAD,text)
if __name__=='__main__':unittest.main()
