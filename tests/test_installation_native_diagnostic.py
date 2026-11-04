"""Closed failure stages only; no native service effects in these tests."""
import json,unittest,os,subprocess
from unified_system import installation_service as service

class NativeDiagnosticTests(unittest.TestCase):
 @unittest.skipUnless(os.name=='nt','Windows unprivileged child exit observation')
 def test_real_child_exit_code_without_service_or_acl_operations(self):
  command="$ErrorActionPreference='Stop';$m=Import-Module -Name ([WildcardPattern]::Escape($env:UNIFIED_TEST_MODULE)) -PassThru;& $m {Add-Type -TypeDefinition $script:Native;$script:NativeStage='NSSM_SET_APPLICATION'};$ps=Join-Path ([Environment]::SystemDirectory) 'WindowsPowerShell\\v1.0\\powershell.exe';try{$null=[UnifiedStoppedServiceNative]::Run($ps,'-NoProfile -NonInteractive -Command \"exit 7\"')}catch{};if((Get-UnifiedOwnedNativeExitCode) -ne 7){throw 'EXIT_FACT_REJECTED'};Write-Output 'EXIT_FACT_VERIFIED'"
  env=service._environment();env['UNIFIED_TEST_MODULE']=str(service.MODULE)
  child=subprocess.run([service._native_tools()['powershell']['path'],'-NoProfile','-NonInteractive','-Command',command],env=env,capture_output=True,timeout=15)
  self.assertEqual(child.returncode,0,child.stderr.decode(errors='replace'))
  self.assertIn(b'EXIT_FACT_VERIFIED',child.stdout)
 def test_nssm_exit_code_is_bounded_numeric_fact_without_raw_output(self):
  for code in (1,2,5,0xc0000142):
   with self.assertRaises(service.OwnedServiceRejected) as caught:
    service._native_result(json.dumps({'error':'OWNED_SERVICE_REJECTED','native_stage':'NSSM_SET_APPLICATION','native_exit_code':code}),1)
   self.assertEqual(caught.exception.native_exit_code,code)
  for code in (True,-1,2**32,'private'):
   with self.assertRaises(service.OwnedServiceRejected) as caught:
    service._native_result(json.dumps({'error':'OWNED_SERVICE_REJECTED','native_stage':'NSSM_SET_APPLICATION','native_exit_code':code}),1)
   self.assertIsNone(caught.exception.native_exit_code)
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
