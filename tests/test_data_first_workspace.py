"""Workspace ownership checks; temporary files and fake protected grants only."""
import copy,json,os,subprocess,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unified_system import data_first_workspace as workspace

class WorkspaceTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve()/'service';self.root.mkdir();self.state=self.root/'state';self.state.mkdir();self.active=True
  self.manifest={'sources':{'strattester':{'commit':'a'*40}}}
  self.policy=dict(schema='unified.data-first-runtime.v1',source_commit='a'*40,strategy_fingerprints=['b'*64],categories=['linear'],network_scope='BYBIT_PUBLIC_GET_ONLY',workspace_relative='data-first',limits=dict(timeout_seconds=30,ram_limit_mb=128,max_pages=1,max_observations=100,requests_per_second=1))
  self.plan=dict(installation_id='install-1',node_id='NODE1',service_name='UnifiedLab_test',service_sid='S-1-5-80-1-2-3-4-5',computer_name='LABHOST',root=str(self.root),state=str(self.state))
  self.grant=SimpleNamespace(profile={'data_first':self.policy},descriptor={'service_plan':self.plan},service_sid=self.plan['service_sid'],computer_name='LABHOST',require_current=lambda:self.active)
 def admit(self):return workspace.admit_data_first_workspace(self.grant,self.manifest)
 def test_new_marker_and_reopen_preserve_data_and_no_source_commit_binding(self):
  first=self.admit();self.assertEqual(first.root,self.state/'data-first');self.assertIs(first.require_current(),True)
  for name in ('market','results','logs','state','data-first-abc123'):(first.root/name).mkdir()
  (first.root/'market'/'retained').write_bytes(b'cache')
  self.manifest['sources']['strattester']['commit']='c'*40;self.policy['source_commit']='c'*40
  second=self.admit();self.assertEqual((second.root/'market'/'retained').read_bytes(),b'cache');self.assertIs(second.require_current(),True)
  self.assertNotIn('source_commit',(first.root/'data-first-owned.json').read_text())
 def test_missing_or_invalid_permission_never_creates_workspace(self):
  for value in (None,{},dict(self.policy,workspace_relative='../foreign')):
   self.grant.profile['data_first']=value
   with self.assertRaises(workspace.WorkspaceBlocked):self.admit()
   self.assertFalse((self.state/'data-first').exists())
 def test_revoked_or_json_grant_has_no_effect(self):
  self.active=False
  with self.assertRaises(workspace.WorkspaceBlocked):self.admit()
  with self.assertRaises(workspace.WorkspaceBlocked):workspace.admit_data_first_workspace({'authorized':True},self.manifest)
  self.assertFalse((self.state/'data-first').exists())
 def test_existing_unmarked_empty_and_cli_v1_roots_are_not_adopted(self):
  path=self.state/'data-first';path.mkdir()
  with self.assertRaises(workspace.WorkspaceBlocked):self.admit()
  marker=path/'data-first-owned.json';marker.write_text(json.dumps({'version':1,'scope':'DEDICATED_RESEARCH_ONLY','categories':['linear']}));before=marker.read_bytes()
  with self.assertRaises(workspace.WorkspaceBlocked):self.admit()
  self.assertEqual(marker.read_bytes(),before)
 def test_cross_install_node_service_sid_and_host_are_rejected(self):
  self.admit()
  for key in ('installation_id','node_id','service_name','service_sid','computer_name'):
   original=self.plan[key];self.plan[key]=original+'x'
   with self.assertRaises(workspace.WorkspaceBlocked):self.admit()
   self.plan[key]=original
 def test_unknown_top_files_or_directories_block_without_removal(self):
  first=self.admit()
  for name in ('foreign.db','foreign-dir'):
   path=first.root/name
   path.write_bytes(b'foreign') if '.' in name else path.mkdir()
   with self.assertRaises(workspace.WorkspaceBlocked):first.require_current()
   self.assertTrue(path.exists());path.unlink() if path.is_file() else path.rmdir()
 def test_marker_mutation_and_replacement_are_rejected(self):
  first=self.admit();marker=first.root/'data-first-owned.json';raw=marker.read_bytes();marker.write_bytes(raw+b' ')
  with self.assertRaises(workspace.WorkspaceBlocked):first.require_current()
  marker.unlink();marker.write_bytes(raw)
  with self.assertRaises(workspace.WorkspaceBlocked):first.require_current()
 def test_replaced_root_and_state_are_rejected(self):
  first=self.admit();first.root.rename(self.state/'retained');first.root.mkdir()
  with self.assertRaises(workspace.WorkspaceBlocked):first.require_current()
  self.assertTrue((self.state/'retained'/'data-first-owned.json').exists())
 def test_replaced_state_inode_blocks_reopen_without_writing_new_state(self):
  first=self.admit();self.state.rename(self.root/'retained-state');self.state.mkdir()
  with self.assertRaises(workspace.WorkspaceBlocked):first.require_current()
  self.assertEqual(list(self.state.iterdir()),[])

 def test_hardlinked_marker_is_rejected(self):
  first=self.admit();os.link(first.root/'data-first-owned.json',self.root/'marker-copy')
  with self.assertRaises(workspace.WorkspaceBlocked):first.require_current()
 def test_symlink_or_junction_workspace_rejected_without_foreign_write(self):
  foreign=self.root/'foreign';foreign.mkdir();link=self.state/'data-first'
  if os.name=='nt':
   result=subprocess.run(['cmd.exe','/c','mklink','/J',str(link),str(foreign)],capture_output=True)
   self.assertEqual(result.returncode,0)
  else:link.symlink_to(foreign,target_is_directory=True)
  self.addCleanup(lambda:os.rmdir(link) if os.name=='nt' else link.unlink())
  with self.assertRaises(workspace.WorkspaceBlocked):self.admit()
  self.assertEqual(list(foreign.iterdir()),[])
 def test_normal_directory_replacement_in_grant_callback_has_no_marker_write(self):
  def current():
   path=self.state/'data-first'
   if path.exists() and not (self.state/'retained-workspace').exists():
    path.rename(self.state/'retained-workspace');path.mkdir()
   return True
  self.grant.require_current=current
  with self.assertRaises(workspace.WorkspaceBlocked):self.admit()
  self.assertEqual(list((self.state/'data-first').iterdir()),[])
  self.assertEqual(list((self.state/'retained-workspace').iterdir()),[])
 def test_known_directory_names_cannot_be_regular_files(self):
  first=self.admit();(first.root/'market').write_bytes(b'foreign')
  with self.assertRaises(workspace.WorkspaceBlocked):first.require_current()
  self.assertEqual((first.root/'market').read_bytes(),b'foreign')
 def test_noncanonical_duplicate_or_oversized_marker_is_preserved_and_rejected(self):
  first=self.admit();marker=first.root/'data-first-owned.json';original=marker.read_bytes()
  for raw in (b'{"version":2,"version":2}\n',original+b' ',b'x'*(workspace.MAX_MARKER_BYTES+1)):
   marker.write_bytes(raw)
   with self.assertRaises(workspace.WorkspaceBlocked):self.admit()
   self.assertEqual(marker.read_bytes(),raw)
 def test_bounded_top_namespace_rejects_without_truncating(self):
  from unittest.mock import patch
  first=self.admit();(first.root/'market').mkdir()
  with patch.object(workspace,'MAX_TOP_LEVEL_ENTRIES',1):
   with self.assertRaises(workspace.WorkspaceBlocked):first.require_current()
  self.assertTrue((first.root/'market').is_dir())
 def test_known_factory_category_junction_is_rejected_before_database_open(self):
  first=self.admit();market=first.root/'market';market.mkdir();foreign=self.root/'foreign-market';foreign.mkdir();link=market/'linear'
  if os.name=='nt':
   result=subprocess.run(['cmd.exe','/c','mklink','/J',str(link),str(foreign)],capture_output=True);self.assertEqual(result.returncode,0)
  else:link.symlink_to(foreign,target_is_directory=True)
  self.addCleanup(lambda:os.rmdir(link) if os.name=='nt' else link.unlink())
  with self.assertRaises(workspace.WorkspaceBlocked):first.require_current()
  self.assertEqual(list(foreign.iterdir()),[])
 def test_current_grant_rechecked_before_marker_write(self):
  calls=[]
  def current():
   calls.append(True)
   if (self.state/'data-first').exists():return False
   return True
  self.grant.require_current=current
  with self.assertRaises(workspace.WorkspaceBlocked):self.admit()
  self.assertFalse((self.state/'data-first'/'data-first-owned.json').exists())

if __name__=='__main__':unittest.main()
