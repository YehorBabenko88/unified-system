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
