import unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch
from unified_system import service_bootstrap as bootstrap

class ProtectedResearchEntryTests(unittest.TestCase):
 def test_full_admission_failure_prevents_factory_import(self):
  grant=Mock();grant.require_current.return_value=True
  with patch.object(bootstrap,'_admit_capsule',side_effect=bootstrap.ActivationBlocked('ACTIVATION_CODE_REJECTED')):
   with self.assertRaises(bootstrap.ActivationBlocked):bootstrap.run_protected_data_first(grant)
 def test_missing_policy_rejected_before_workspace_or_app(self):
  grant=Mock();grant.require_current.return_value=True;grant.profile={}
  with patch.object(bootstrap,'_admit_capsule',return_value={'manifest':{}}),patch.object(bootstrap,'_runtime_admission',return_value=({},{})):
   with self.assertRaises(bootstrap.ActivationBlocked):bootstrap.run_protected_data_first(grant)


class ConstructorRouteTests(unittest.TestCase):
 def test_research_route_rejects_foreign_cwd_before_owned_import_setup(self):
  import tempfile
  from pathlib import Path
  from unified_system import data_first_service as service
  with tempfile.TemporaryDirectory() as temporary:
   root=Path(temporary).resolve();workspace=SimpleNamespace(root=root,require_current=lambda:True)
   with patch.object(service,'admit_data_first_workspace',return_value=workspace):
    with self.assertRaises(bootstrap.ActivationBlocked):service.serve_research(Mock(),{}, {}, {})
 def test_worker_program_is_closed_and_does_not_mutate_admitted_config(self):
  import tempfile,copy
  from pathlib import Path
  from unified_system import data_first_service as service
  with tempfile.TemporaryDirectory() as temporary:
   root=Path(temporary).resolve();grant=SimpleNamespace(code_root=root,profile={'data_first':{}},descriptor={'service_plan':{'role':'WORKER'}})
   config={'programs':{'grid':{'argv':['python','old'],'external_file_pins':{}}}};before=copy.deepcopy(config)
   manifest={'sources':{'unified-system':{'root':'sources/unified-system'}},'files':{'sources/unified-system/unified_system/service_entry.py':{'sha256':'a'*64}}}
   with patch('unified_system.data_first_policy.validate_data_first_grant',return_value={}):result=service.worker_program(config,grant,manifest)
   self.assertEqual(config,before);self.assertEqual(result['programs']['grid']['argv'],['python','-I','-S','-B',str(root/'sources/unified-system/unified_system/service_entry.py'),'--data-first-worker'])
   grant.descriptor['service_plan']['role']='CONTROL'
   with patch('unified_system.data_first_policy.validate_data_first_grant',return_value={}):
    with self.assertRaises(bootstrap.ActivationBlocked):service.worker_program(config,grant,manifest)
