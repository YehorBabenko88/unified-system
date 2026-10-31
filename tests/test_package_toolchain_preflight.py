"""Actual isolated raw launches; tiny synthetic archives are integrity fixtures."""
import hashlib,json,shutil,unittest
from pathlib import Path
from tests import test_package_preflight as release_tests

class ToolchainPreflightTests(unittest.TestCase):
 command=release_tests.PackagePreflightTests.command
 run_preflight=release_tests.PackagePreflightTests.run_preflight
 def setUp(self):
  release_tests.PackagePreflightTests.setUp(self)
  for name in ('unified_system/windows_toolchain.py','unified_system/file_identity.py','unified_system/windows-toolchain.catalog.json','unified_system/owned_python.py','unified_system/runtime_process.py'):
   shutil.copyfile(release_tests.ROOT/name,self.repo/name)
  self.artifacts=self.home/'archives';self.artifacts.mkdir()
  catalog_path=self.repo/'unified_system/windows-toolchain.catalog.json';catalog=json.loads(catalog_path.read_bytes())
  for record in catalog['artifacts']:
   raw=('SYNTHETIC BYTES '+record['component']).encode();(self.artifacts/record['filename']).write_bytes(raw)
   record.update(sha256=hashlib.sha256(raw).hexdigest(),expected_bytes=len(raw))
  catalog_path.write_text(json.dumps(catalog))
  self.command_git('add','.');self.command_git('-c','user.name=Test','-c','user.email=test@example.invalid','commit','-m','synthetic catalog fixture')
  self.head=self.command_git('rev-parse','HEAD');self.tree=self.command_git('rev-parse','HEAD^{tree}')
 def toolchain_command(self):
  command=self.command()
  for flag in ('--package-root','--publisher-sha256'):
   index=command.index(flag);del command[index:index+2]
  return [*command,'--operation','toolchain','--artifact-dir',str(self.artifacts)]
 def test_all_five_bytes_match_only_scoped_component_verification(self):
  result=self.run_preflight(self.toolchain_command());self.assertEqual(result.returncode,0,result.stderr);out=json.loads(result.stdout)
  self.assertEqual(out['status'],'COMPONENT_BYTES_VERIFIED_ONLY');self.assertEqual(out['source_head'],self.head);self.assertEqual(out['source_tree'],self.tree)
  self.assertEqual(len(out['integrity']['artifacts']),5);self.assertTrue(all(a['status']=='BYTES_MATCH' for a in out['integrity']['artifacts']))
  self.assertFalse(out['installation_closure']);self.assertFalse(out['execution_authority']);self.assertFalse(out['physical_deployment_allowed'])
  self.assertEqual(out['integrity']['result'],'INCOMPLETE');self.assertEqual(out['integrity']['native_execution'],'NOT_RUN');self.assertEqual({u['component'] for u in out['integrity']['required_unlocked']},{'python-wheels','consul'})
  self.assertEqual(list(self.cache_parent.iterdir()),[])
 def test_missing_or_wrong_archive_is_nonzero_blocked_json(self):
  artifact=next(self.artifacts.iterdir());raw=artifact.read_bytes()
  for variant in ('missing','wrong'):
   if variant=='missing':artifact.unlink()
   else:artifact.write_bytes(b'X'*len(raw))
   result=self.run_preflight(self.toolchain_command());self.assertNotEqual(result.returncode,0);out=json.loads(result.stdout)
   self.assertEqual(out['status'],'BLOCKED');self.assertFalse(out['installation_closure']);self.assertFalse(out['execution_authority']);self.assertFalse(out['integrity']['all_locked_artifacts_match'])
  self.assertEqual(list(self.cache_parent.iterdir()),[])
 def test_catalog_or_source_tamper_cannot_become_self_pinned_policy(self):
  catalog=self.repo/'unified_system/windows-toolchain.catalog.json';catalog.write_bytes(catalog.read_bytes()+b' ')
  self.command_git('update-index','--assume-unchanged','unified_system/windows-toolchain.catalog.json')
  result=self.run_preflight(self.toolchain_command());self.assertNotEqual(result.returncode,0)
  self.assertNotIn('COMPONENT_BYTES_VERIFIED_ONLY',result.stdout)
