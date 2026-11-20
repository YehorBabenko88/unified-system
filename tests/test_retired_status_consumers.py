"""Raw archive custody and mandatory untransferred runtime obligations; no native calls."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
HELD=('PARTIAL_TO_TERMINAL_GAP_DISPLAY','UNAVAILABLE_TERMINAL_DISPLAY','WRONG_PRODUCER_HTTP_REFUSAL','WRONG_PRODUCER_HTTP_RETIREMENT','WRONG_PRODUCER_ENV_PATH_RESTORATION','ROOT_BLOCKED_TO_TERMINAL_MONITOR_HTTP','MONITOR_UNVERIFIED_NO_TRADE','MONITOR_HTTP_RETIREMENT','MONITOR_ENV_PATH_RESTORATION')

class RetiredConsumerTests(unittest.TestCase):
 def checker(self):
  source=ROOT/'scripts/verify_retired_status_consumers.py'
  self.assertTrue(source.is_file(),'raw archive checker must exist before retirement can qualify')
  spec=importlib.util.spec_from_file_location('retired_consumer_checker',source)
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
 def test_raw_archives_preserve_all_roles_and_assertions(self):
  result=self.checker().verify_inventory(ROOT)
  self.assertEqual((result['archive_files'],result['assertions'],result['roles']),(8,14,16))
  self.assertEqual(tuple(result['held_roles']),HELD)
 def test_runtime_gate_keeps_nine_composition_obligations_blocked(self):
  from integration.four_owner.contracts import runtime_gate
  report=runtime_gate('browser',{'qualification':'PASS_SCOPED'})
  self.assertEqual(tuple(report.get('held_status_consumer_roles',())),HELD)
  self.assertIn('LEGACY_STATUS_CONSUMER_COMPOSITION_NOT_QUALIFIED',report['missing_proofs'])
  self.assertEqual(report['additional_legacy_obligation_inventory'],'docs/migration/retired-status-consumers-20261120/role-inventory.json')
  self.assertTrue((ROOT/report['additional_legacy_obligation_inventory']).is_file())
  self.assertFalse(report['passed']);self.assertEqual(report['release_status'],'NO_GO')
 def test_tampered_archive_or_rehashed_scope_cannot_erase_obligations(self):
  checker=self.checker()
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);source=ROOT/checker.INVENTORY.parent
   shutil.copytree(source,root/checker.INVENTORY.parent)
   self.assertEqual(checker.verify_inventory(root)['archive_files'],8)
   inventory=root/checker.INVENTORY;original=inventory.read_bytes();value=json.loads(original)
   archive=root/value['archived'][0]['archive'];before=archive.read_bytes();archive.write_bytes(before+b'changed')
   with self.assertRaises(ValueError):checker.verify_inventory(root)
   archive.write_bytes(before);value['roles'][6]['status']='TRANSFERRED';inventory.write_text(json.dumps(value))
   with self.assertRaises(ValueError):checker.verify_inventory(root)
   inventory.write_bytes(b'x'*65537)
   with self.assertRaises(ValueError):checker.verify_inventory(root)
   inventory.write_bytes(original)
   workflows=root/'.github/workflows';workflows.mkdir(parents=True)
   for filename,command in (('new-caller.yml','python scripts/verify_cross_repo.py'),('new-caller.yaml','python -m scripts.verify_cross_repo'),('new-caller.yml',r'python scripts\verify_cross_repo.py'),('new-caller.yml','python ./scripts/verify_cross_repo.py'),('new-caller.yaml','python -m scripts.verify_cross_repo'),('new-caller.yml','# VERIFY_CROSS_REPO retained consumer')):
    caller=workflows/filename;caller.write_text('jobs:\n  test:\n    steps:\n      - run: '+command+'\n')
    with self.subTest(filename=filename,command=command),self.assertRaises(ValueError):checker.verify_inventory(root)
    caller.unlink()
 def test_archive_pass_cannot_claim_runtime_or_permission(self):
  checker=self.checker();report=checker.archive_report(checker.verify_inventory(ROOT))
  self.assertEqual(report['status'],'PASS_ARCHIVE_CUSTODY_ONLY')
  self.assertEqual(report['runtime_qualification'],'NOT_RUN');self.assertEqual(report['release_status'],'NO_GO')
  for name in ('execution_authority','trading_authorized','source_capability'):self.assertIs(report[name],False)
 def test_canonical_pure_identity_and_unknown_history_stay_denied(self):
  from unified_system.provenance_v11 import inspect_historical_receipt,inspect_market_data_snapshot
  from unified_system.compatibility import validate_response
  from unified_system.contracts import ContractError
  value=inspect_market_data_snapshot({'api_version':{'major':1,'minor':1},'producer':'market_data','status':'PARTIAL','reason':'EXCHANGE_COMPLETENESS_UNATTESTED'})
  self.assertEqual(value['status'],'PARTIAL');self.assertFalse(value['trading_authorized'])
  self.assertEqual(inspect_historical_receipt({})['status'],'UNAVAILABLE')
  for old in ('grid','strattester','supervisor'):
   with self.subTest(old=old),self.assertRaises(ContractError):validate_response(old,'health',503,{})
 def test_ast_dump_requests_empty_optional_fields_on_new_interpreters(self):
  from unittest.mock import patch
  checker=self.checker();original=checker.ast.dump;calls=[]
  def modern_dump(node,include_attributes=False,*,show_empty=False):
   calls.append(show_empty)
   return original(node,include_attributes=include_attributes) if show_empty else 'EMPTY_OPTIONALS_OMITTED'
  with patch.object(checker.ast,'dump',modern_dump):
   self.assertEqual(checker.verify_inventory(ROOT)['assertions'],14)
  self.assertEqual(calls,[True]*14)
 def test_legacy_ast_dump_without_keyword_preserves_original_fingerprints(self):
  from unittest.mock import patch
  checker=self.checker();original=checker.ast.dump;calls=[]
  def legacy_dump(node,include_attributes=False):
   calls.append(True);return original(node,include_attributes=include_attributes)
  with patch.object(checker.ast,'dump',legacy_dump):
   self.assertEqual(checker.verify_inventory(ROOT)['assertions'],14)
  self.assertEqual(len(calls),14)
