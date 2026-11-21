import subprocess
import unittest
from unittest.mock import patch
from tests.native_phase_diagnostics import phase, phase_summary, run_phased


class PhaseDiagnosticsTests(unittest.TestCase):
 def test_private_unknown_or_excessive_phase_data_is_rejected(self):
  for value in (b'PRIVATE C:\\secret',b'UNIFIED_PHASE:PRIVATE:1',
                b'UNIFIED_PHASE:ENTRY:notnumeric',b'x'*4097,
                b'UNIFIED_PHASE:ENTRY:1\n'*17):
   self.assertEqual(phase_summary(value),'PHASE_DATA_REJECTED')
  with self.assertRaises(ValueError):phase('PRIVATE')
 def test_only_allowlisted_bounded_phase_markers_are_reported(self):
  self.assertEqual(phase_summary(b'UNIFIED_PHASE:ENTRY:1\r\nUNIFIED_PHASE:IMPORT_BEGIN:2\r\n'),
                   'ENTRY@1,IMPORT_BEGIN@2')
 def test_timeout_reports_static_phases_without_private_exception_payload(self):
  error=subprocess.TimeoutExpired(['PRIVATE_PATH'],15,output=b'PRIVATE_STDOUT',stderr=b'UNIFIED_PHASE:ENTRY:1')
  with patch('subprocess.run',side_effect=error) as child:
   with self.assertRaises(AssertionError) as caught:run_phased(['PRIVATE_PATH'],env={})
  self.assertNotIn('PRIVATE',str(caught.exception));self.assertIn('ENTRY@1',str(caught.exception))
  self.assertEqual(child.call_args.kwargs['timeout'],15)
 def test_finer_static_powershell_phases_are_allowlisted(self):
  for name in ('OBJECT_BEGIN','OBJECT_END','FIRST_MEMBER_BEGIN','FIRST_MEMBER_END','PARSE_BEGIN','PARSE_END','UNICODE_BEGIN','UNICODE_END','CAP_BEGIN','CAP_END'):
   self.assertIn(name,phase(name))
 def test_thirty_second_timeout_retains_bound_and_hides_payload(self):
  error=subprocess.TimeoutExpired(['PRIVATE_PATH'],30,output=b'PRIVATE',stderr=b'UNIFIED_PHASE:PARSE_BEGIN:1')
  with patch('subprocess.run',side_effect=error) as child:
   with self.assertRaises(AssertionError) as caught:run_phased(['PRIVATE_PATH'],env={},timeout=30)
  self.assertNotIn('PRIVATE',str(caught.exception));self.assertIn('TIMEOUT_30S',str(caught.exception))
  self.assertEqual(child.call_args.kwargs['timeout'],30)
 def test_other_powershell_bounds_are_rejected_before_spawn(self):
  with patch('subprocess.run') as child:
   for value in (True,0,16,31,'15'):
    with self.assertRaises(ValueError):run_phased([],env={},timeout=value)
   child.assert_not_called()
 def test_node_phase_allowlist_accepts_bytes_and_text(self):
  from tests.native_phase_diagnostics import node_phase_summary
  for raw in (b'UNIFIED_NODE:ENTRY\nUNIFIED_NODE:STDIN_END\n','UNIFIED_NODE:ENTRY\r\nUNIFIED_NODE:STDIN_END\r\n'):
   self.assertEqual(node_phase_summary(raw),'ENTRY,STDIN_END')
 def test_node_parser_rejects_private_unknown_nonascii_and_excess(self):
  from tests.native_phase_diagnostics import node_phase_summary
  for raw in (b'PRIVATE',b'UNIFIED_NODE:PRIVATE',b'\xff',b'x'*1025,b'UNIFIED_NODE:ENTRY\n'*9,object()):
   self.assertEqual(node_phase_summary(raw),'PHASE_DATA_REJECTED')
  self.assertEqual(node_phase_summary(None),'NO_PHASE_OBSERVED')
 def test_node_timeout_hides_harness_input_path_and_raw_outputs(self):
  from tests.native_phase_diagnostics import run_node_phased
  error=subprocess.TimeoutExpired(['PRIVATE_PATH','PRIVATE_HARNESS'],15,output=b'PRIVATE_OUTPUT',stderr=b'UNIFIED_NODE:ENTRY\nUNIFIED_NODE:PARSED\n')
  with patch('subprocess.run',side_effect=error) as child:
   with self.assertRaises(AssertionError) as caught:run_node_phased(['PRIVATE_PATH','PRIVATE_HARNESS'],input='PRIVATE_INPUT')
  self.assertNotIn('PRIVATE',str(caught.exception));self.assertIn('ENTRY,PARSED',str(caught.exception))
  self.assertEqual(child.call_args.kwargs['timeout'],15)
