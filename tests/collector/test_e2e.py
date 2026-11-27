"""Actual composition tests, not mocked Worker/recorder/storage implementations."""
import contextlib,hashlib,io,json,os,unittest
from pathlib import Path
from unified_system import collector_offline as co
from unified_system.collector_profile import validate_collector_profile
from unified_system.collector_entry import main as collector_main
from unified_system.journal import Journal
from test_profile import fixture

def complete(coro):
 try:
  try:coro.send(None)
  except StopIteration as done:return done.value
  raise AssertionError('unqualified asynchronous suspension')
 finally:coro.close()

class OfflineCollectorTests(unittest.TestCase):
 def setUp(self):
  self.parent=Path(os.environ['COLLECTOR_E2E_SCRATCH'])/self._testMethodName;self.parent.mkdir(exist_ok=False)
  self.manifest=Path(os.environ['COLLECTOR_INPUT_MANIFEST']).read_bytes()
  value=fixture();value['source_manifest_sha256']=hashlib.sha256(self.manifest).hexdigest()
  self.profile=validate_collector_profile(value,manifest_sha256=value['source_manifest_sha256'])
  self.state=self.parent/'state';self.code=Path(os.environ['COLLECTOR_CODE_ROOT'])
 def run_capture(self,frames,resume=False):
  return complete(co.collect_synthetic(self.profile,manifest_bytes=self.manifest,frames=frames,
   state_root=self.state,code_root=self.code,observed_at_ms=1794441600000,resume=resume))
 def test_actual_raw_occurrences_digest_and_bounded_log(self):
  frame=co.synthetic_frames()[0];result=self.run_capture((frame,frame))
  self.assertEqual(result['phase'],'STOPPED');self.assertTrue(result['writer_closed'])
  self.assertEqual(result['raw_frames_received'],2);self.assertEqual(result['raw_observations_stored'],5)
  self.assertEqual(result['raw_payload_occurrence_bytes'],len(frame)*2)
  self.assertEqual(result['raw_payload_unique_bytes'],len(frame));self.assertTrue(result['all_digests_verified'])
  self.assertEqual(result['native_outcome'],'UNKNOWN');self.assertFalse(result['publication_confirmed'])
  logs=list((self.state/'logs').glob('*.jsonl'));self.assertTrue(logs)
  self.assertNotIn(b'publicTrade.BTCUSDT',b''.join(p.read_bytes() for p in logs))
 def test_clean_resume_preserves_checkpoint_and_accumulated_occurrences(self):
  first=self.run_capture(co.synthetic_frames());second=self.run_capture(co.synthetic_frames(),resume=True)
  self.assertEqual(second['previous_checkpoint'],first['checkpoint'])
  self.assertEqual(second['raw_observations_stored'],6)
  self.assertEqual(second['counter_epoch'],first['counter_epoch']);self.assertTrue(second['writer_closed'])
  self.assertNotEqual(second['checkpoint']['observation_sha256'],first['checkpoint']['observation_sha256'])
 def test_invalid_frame_is_explicit_gap_not_verified_history(self):
  result=self.run_capture((b'{invalid',co.synthetic_frames()[0]))
  self.assertEqual(result['quality'],'GAP_DETECTED');self.assertTrue(result['gap_open'])
  self.assertFalse(result['publication_confirmed']);self.assertEqual(result['phase'],'STOPPED')
 def test_manifest_substitution_denies_before_state_creation(self):
  with self.assertRaises(co.CollectorOfflineBlocked):
   complete(co.collect_synthetic(self.profile,manifest_bytes=self.manifest+b' ',frames=co.synthetic_frames(),state_root=self.state,code_root=self.code,observed_at_ms=1794441600000))
  self.assertFalse(self.state.exists())
 def test_actual_synthetic_entry_and_resume_use_existing_components(self):
  profile_path=self.parent/'profile.json';profile_path.write_bytes(self.profile.encoded)
  outputs=[]
  for mode in ('--synthetic-offline','--resume-synthetic'):
   out=io.StringIO()
   with contextlib.redirect_stdout(out):code=collector_main([mode,str(profile_path),'--manifest',os.environ['COLLECTOR_INPUT_MANIFEST'],'--state',str(self.state)])
   self.assertEqual(code,0);outputs.append(json.loads(out.getvalue()))
  self.assertEqual(outputs[0]['raw_observations_stored'],3);self.assertEqual(outputs[1]['raw_observations_stored'],6)
  self.assertEqual(outputs[1]['previous_checkpoint'],outputs[0]['checkpoint'])
  self.assertTrue(all(value['writer_closed'] and value['provider_sends']==0 for value in outputs))
 def test_resume_rejects_batch_before_persistent_budget_partial_write(self):
  frames=co.synthetic_frames()*4
  first=self.run_capture(frames);self.assertEqual(first['raw_observations_stored'],9)
  with self.assertRaises(co.CollectorBudgetExhausted):self.run_capture(frames,resume=True)
  self.assertEqual(len(Journal(self.state/'context/raw/capture.sqlite').read()),9)
  values=[json.loads(line) for file in (self.state/'logs').glob('*.jsonl') for line in file.read_bytes().splitlines()]
  self.assertTrue(any(value['event']=='RESOURCE' and value['error_code']=='RESOURCE_LIMIT' for value in values))
 def test_persisted_exact_payload_boundary_then_one_byte_exhaustion(self):
  first=self.run_capture((b'x'*1048576,)*4)
  self.assertEqual(first['raw_payload_occurrence_bytes'],4194304)
  self.assertEqual(first['raw_observations_stored'],9)
  with self.assertRaises(co.CollectorBudgetExhausted):self.run_capture((b'x',),resume=True)
  rows=Journal(self.state/'context/raw/capture.sqlite').read()
  self.assertEqual(len(rows),9)
  self.assertEqual(sum(row['receipt']['payload_byte_count'] for row in rows),4194304)
 def test_clean_resume_does_not_hide_a_persisted_history_gap(self):
  first=self.run_capture((b'{invalid',));self.assertEqual(first['quality'],'GAP_DETECTED')
  second=self.run_capture(co.synthetic_frames(),resume=True)
  self.assertEqual(second['quality'],'GAP_DETECTED')
  self.assertEqual(second['gap_count'],1);self.assertTrue(second['gap_open'])
  self.assertFalse(second['invocation_gap_open']);self.assertEqual(second['continuity'],'UNKNOWN')

if __name__=='__main__':unittest.main()
