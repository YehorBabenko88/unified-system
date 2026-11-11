"""False-PASS controls for mandatory phased acceptance reporting."""
import importlib.util,pathlib,unittest
spec=importlib.util.spec_from_file_location('phased_gate',pathlib.Path(__file__).with_name('run_phased_acceptance.py'))
gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
class ReporterTests(unittest.TestCase):
 def test_missing_mandatory_case_is_not_go(self):
  with self.assertRaises(ValueError):gate.decide({})
 def test_primitive_pass_cannot_clear_blocked_integrated_endpoint(self):
  rows={key:dict(status='PASS',evidence_class='REAL_PROCESS') for key in gate.REQUIRED}
  rows['ENDPOINT-INTEGRATED']['status']='BLOCKED'
  self.assertEqual(gate.decide(rows),'NO_GO')
 def test_mock_cannot_qualify_endpoint(self):
  rows={key:dict(status='PASS',evidence_class='REAL_PROCESS') for key in gate.REQUIRED}
  rows['ENDPOINT-CONSUL']['evidence_class']='MOCK'
  with self.assertRaises(ValueError):gate.decide(rows)
 def test_skipped_mandatory_case_cannot_qualify(self):
  rows={key:dict(status='PASS',evidence_class='REAL_PROCESS') for key in gate.REQUIRED}
  rows['ENDPOINT-MTLS']['status']='SKIPPED'
  with self.assertRaises(ValueError):gate.decide(rows)
 def test_same_count_substitution_cannot_hide_missing_case(self):
  rows={key:dict(status='PASS',evidence_class='REAL_PROCESS') for key in gate.REQUIRED}
  rows['UNAPPROVED-REPLACEMENT']=rows.pop('ENDPOINT-INTEGRATED')
  with self.assertRaises(ValueError):gate.decide(rows)
if __name__=='__main__':unittest.main()
