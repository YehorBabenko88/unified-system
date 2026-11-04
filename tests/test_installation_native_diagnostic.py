"""Closed failure stages only; no native service effects in these tests."""
import json,unittest
from unified_system import installation_service as service

class NativeDiagnosticTests(unittest.TestCase):
 def test_failed_native_response_retains_only_known_static_stage(self):
  for stage in ('SCM_CREATE','NSSM_SET_APPLICATION','SCM_READ','NSSM_GET_APP_EXIT','ACL_PROOF'):
   with self.subTest(stage=stage),self.assertRaises(service.OwnedServiceRejected) as caught:
    service._native_result(json.dumps({'error':'OWNED_SERVICE_REJECTED','native_stage':stage}),1)
   self.assertEqual(caught.exception.native_stage,stage)
   self.assertEqual(str(caught.exception),'OWNED_SERVICE_REJECTED')
 def test_private_or_malformed_native_details_are_never_promoted(self):
  for raw in ('PRIVATE_EXCEPTION',json.dumps({'error':'OWNED_SERVICE_REJECTED','native_stage':'PRIVATE_PATH'}),json.dumps({'error':'OWNED_SERVICE_REJECTED','native_stage':'SCM_CREATE','private':'secret'})):
   with self.subTest(raw=raw[:20]),self.assertRaises(service.OwnedServiceRejected) as caught:
    service._native_result(raw,1)
   self.assertEqual(caught.exception.native_stage,'UNAVAILABLE')
   self.assertNotIn('PRIVATE',str(caught.exception))
 def test_successful_closed_backend_result_is_unchanged(self):
  self.assertEqual(service._native_result('{"root_created":true}',0),{'root_created':True})
  with self.assertRaises(service.OwnedServiceRejected):service._native_result('{"error":"OWNED_SERVICE_REJECTED","native_stage":"SCM_CREATE"}',0)
