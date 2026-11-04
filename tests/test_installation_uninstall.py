"""Inert source-only uninstall tests; no SCM or physical installation."""
import copy,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tests import test_installation_service as service_fixtures
from unified_system.installation_service import ServiceResource
from unified_system.installation_uninstall import Uninstaller

class FakeRemoval:
 def __init__(self,backend):self.backend=backend;self.calls=[];self.pending=False
 def call(self,action,plan,record,guard):
  if guard(action,plan['plan_sha256']) is not True:raise ValueError('denied')
  self.calls.append(action)
  if action=='REMOVE_SERVICE':
   if self.backend.service!=record['proof']:raise ValueError('foreign live service')
   if self.pending:return {'service':'MARKED_PENDING'}
   self.backend.service=None
  return {'service':'ABSENT' if self.backend.service is None else 'PRESENT_REVIEW_REQUIRED'}

class UninstallTests(unittest.TestCase):
 def setUp(self):
  service_fixtures.ServiceResourceTests.setUp(self);self.service_plan=service_fixtures.ServiceResourceTests.plan(self)
  self.resource=ServiceResource.create(self.service_plan,self.backend,self.guard)
  self.removal=FakeRemoval(self.backend);self.uninstall=Uninstaller(self.resource,self.removal)
  self.state=Path(self.service_plan['state']);(self.state/'user-data').write_bytes(b'PRESERVE_DATA');(self.state/'config').write_bytes(b'PRESERVE_CONFIG')
  self.ownership=Path(self.service_plan['root'])/'ownership/service.sqlite';self.ownership_before=self.ownership.read_bytes()
 def guard(self,action,pin):self.grants.append((action,pin));return True
 def test_app_only_real_inert_code_removal_preserves_state_and_ownership(self):
  preview=self.uninstall.preview();self.assertEqual(preview['mode'],'APP_ONLY');self.assertGreater(preview['code_bytes'],0)
  result=self.uninstall.run(guard=self.guard);self.assertEqual(result['status'],'APP_ONLY_REMOVED')
  self.assertIsNone(self.backend.service);self.assertFalse(Path(self.service_plan['code']).exists())
  self.assertEqual((self.state/'user-data').read_bytes(),b'PRESERVE_DATA');self.assertEqual((self.state/'config').read_bytes(),b'PRESERVE_CONFIG');self.assertEqual(self.ownership.read_bytes(),self.ownership_before)
  self.assertEqual(self.uninstall.run(guard=self.guard)['status'],'APP_ONLY_REMOVED')
 def test_default_denial_and_unclassified_modes_have_no_effect(self):
  for mode in ('REMOVE_CONFIG','FULL'):
   with self.assertRaisesRegex(ValueError,'BLOCKED'):self.uninstall.run(mode=mode,guard=self.guard)
  with self.assertRaises(ValueError):self.uninstall.run()
  self.assertEqual(self.removal.calls,[]);self.assertTrue(Path(self.service_plan['code']).exists())
  self.assertFalse((Path(self.service_plan['root'])/'ownership/uninstall.sqlite').exists())
 def test_changed_unknown_and_foreign_paths_block_before_service_removal(self):
  code=Path(self.service_plan['code']);(code/'foreign').write_bytes(b'FOREIGN')
  with self.assertRaises(ValueError):self.uninstall.run(guard=self.guard)
  self.assertEqual(self.removal.calls,[]);self.assertEqual((code/'foreign').read_bytes(),b'FOREIGN')
 def test_guard_before_each_unlink_partial_resume_and_absence_is_not_attribution(self):
  original=Path.unlink;deleted=[]
  def fail(path,*args,**kwargs):
   if path.is_relative_to(Path(self.service_plan['code'])):
    if deleted:raise OSError('interrupted')
    deleted.append(str(path))
   return original(path,*args,**kwargs)
  with patch.object(Path,'unlink',fail):
   with self.assertRaises(OSError):self.uninstall.run(guard=self.guard)
  self.assertEqual(len(deleted),1)
  reopened=Uninstaller(ServiceResource.open(self.service_plan,self.backend),self.removal)
  self.assertEqual(reopened.run(guard=self.guard)['status'],'APP_ONLY_REMOVED')
  self.assertEqual(self.removal.calls.count('REMOVE_SERVICE'),1)
 def test_missing_without_intent_and_changed_after_intent_are_rejected(self):
  preview=self.uninstall.preview();Path(self.service_plan['code'],'runtime.json').unlink()
  with self.assertRaises(ValueError):self.uninstall.run(guard=self.guard)
  self.assertEqual(self.removal.calls,[])
 def test_marked_pending_and_foreign_recreated_name_do_not_remove_code(self):
  self.removal.pending=True;r=self.uninstall.run(guard=self.guard);self.assertEqual(r['status'],'SERVICE_REMOVAL_PENDING')
  self.assertTrue(Path(self.service_plan['code']).exists())
  self.backend.service={'foreign':True}
  with self.assertRaises(ValueError):self.uninstall.run(guard=self.guard)
  self.assertEqual(self.removal.calls.count('REMOVE_SERVICE'),1)
  self.assertTrue(Path(self.service_plan['code']).exists())
 def test_resume_rejects_missing_code_without_its_own_intent(self):
  with self.assertRaises(ValueError):self.uninstall.run(guard=lambda action,pin:action!='REMOVE_CODE')
  member=Path(self.service_plan['code'],'runtime.json');member.unlink()
  with self.assertRaises(ValueError):self.uninstall.run(guard=self.guard)
  self.assertEqual(self.removal.calls.count('REMOVE_SERVICE'),1);self.assertTrue((self.state/'user-data').exists())
 def test_native_bootstrap_encoding_and_request_are_bound_without_execution(self):
  import base64,json
  from unified_system.installation_uninstall import WindowsRemovalBoundary
  record=self.resource.recorded();plan=self.uninstall._plan(record,self.uninstall._members()[1]);calls=[]
  def capture(argv,**kw):
   calls.append((argv,kw));return ('{\"service\":\"ABSENT\"}',0)
  with patch('unified_system.installation_service.current_computer_name',return_value='TEST-PC'),patch('unified_system.installation_service._native_tools',return_value=self.backend.native_tools()),patch('unified_system.installation_service._native_hash',return_value='b'*64),patch('unified_system.installation_service._run',capture):
   self.assertEqual(WindowsRemovalBoundary().call('REMOVE_SERVICE',plan,record,self.guard),{'service':'ABSENT'})
  argv,kw=calls[0];self.assertEqual(argv[-2],'-EncodedCommand');self.assertIn('Invoke-UnifiedOwnedServiceRemoval',base64.b64decode(argv[-1]).decode('utf-16le'));self.assertEqual(json.loads(kw['payload'])['plan'],record['plan']);self.assertEqual(json.loads(kw['payload'])['action'],'REMOVE_SERVICE')
 @unittest.skipUnless(os.name=='nt','Windows native boundary control instrumentation')
 def test_seventy_member_controller_admits_sources_once_and_observes_without_powershell(self):
  import shutil
  from tests.test_lab_capsule_builder import builder
  from tests.test_installation_service import FakeWindows
  from unified_system import lab_release,installation_service as service
  from unified_system.installation_uninstall import WindowsRemovalBoundary
  source=self.root/'bulk-source';shutil.copytree(self.source,source)
  for i in range(70):
   path=source/'bulk'/('member-%03d.txt'%i);path.parent.mkdir(exist_ok=True);path.write_bytes(b'INERT')
  import hashlib,json
  manifest=json.loads((source/'lab-release.json').read_bytes());(source/'lab-release.json').unlink();manifest['files'],manifest['directories']=builder.inventory(source);raw=lab_release.canonical(manifest);(source/'lab-release.json').write_bytes(raw);pin=hashlib.sha256(raw).hexdigest()
  backend=FakeWindows();p=service.service_plan(source,pin,self.root/'bulk-service','bulk','node','CONTROL',backend);resource=ServiceResource.create(p,backend,self.guard)
  boundary=WindowsRemovalBoundary();observations=[];spawns=[]
  boundary._api={'manager':lambda *a:1,'open':lambda *a:(observations.append(a) or 0),'close':lambda h:True,'error':lambda:1060}
  def capture(argv,**kw):spawns.append(argv);backend.service=None;return ('{\"service\":\"ABSENT\"}',0)
  original=lab_release.verify_capsule
  from unified_system.journal import Journal
  original_read=Journal.read;chain_rows=[]
  def counted(journal):
   rows=original_read(journal)
   if journal.path.name=='uninstall.sqlite':chain_rows.append(len(rows))
   return rows
  with patch.object(Journal,'read',counted),patch.object(service,'current_computer_name',return_value='TEST-PC'),patch.object(service,'_native_tools',return_value=backend.native_tools()),patch.object(service,'_native_hash',return_value='b'*64),patch.object(service,'_run',capture),patch.object(lab_release,'verify_capsule',wraps=original) as verified:
   self.assertEqual(Uninstaller(resource,boundary).run(guard=self.guard)['status'],'APP_ONLY_REMOVED')
   self.assertLessEqual(verified.call_count,8,'full closure admission must be O(1) per operation')
  self.assertEqual(len(spawns),1,'only actual DELETE uses PowerShell');self.assertGreaterEqual(len(observations),70);self.assertLessEqual(len(chain_rows),5,'full audit verification must be O(1) per operation');self.assertLessEqual(sum(chain_rows),2*len(observations)+10,'audit rows processed must be linear')
 def test_external_sql_rewrite_with_unchanged_tail_blocks_further_deletion(self):
  import sqlite3
  from contextlib import closing
  code=Path(self.service_plan['code']);before={p.relative_to(code).as_posix() for p in code.rglob('*') if p.is_file()};calls=0
  def corrupt(action,pin):
   nonlocal calls
   if action=='REMOVE_CODE':
    calls+=1
    if calls==3:
     with closing(sqlite3.connect(self.uninstall.audit.path)) as connection,connection:connection.execute("UPDATE transitions SET receipt='{}' WHERE sequence=1")
   return True
  with self.assertRaises(ValueError):self.uninstall.run(guard=corrupt)
  after={p.relative_to(code).as_posix() for p in code.rglob('*') if p.is_file()};self.assertEqual(len(before-after),1);self.assertEqual(self.removal.calls.count('REMOVE_SERVICE'),1)
 def test_native_boundary_default_denial_precedes_any_os_probe(self):
  from unified_system.installation_uninstall import WindowsRemovalBoundary
  with patch('unified_system.installation_service._native_tools',side_effect=AssertionError('native probe forbidden')):
   with self.assertRaises(ValueError):WindowsRemovalBoundary().call('REMOVE_SERVICE',{}, {}, None)
   with self.assertRaises(ValueError):WindowsRemovalBoundary().call('REMOVE_SERVICE',{'plan_sha256':'unapproved'}, {}, lambda a,p:False)
 def test_changed_owned_file_and_denied_code_phase_preserve_remaining_bytes(self):
  with self.assertRaises(ValueError):self.uninstall.run(guard=lambda action,pin:action!='REMOVE_CODE')
  self.assertTrue(Path(self.service_plan['code']).exists())
  p=Path(self.service_plan['code'],'runtime.json');p.write_bytes(b'CHANGED')
  with self.assertRaises(ValueError):self.uninstall.run(guard=self.guard)
  self.assertEqual(p.read_bytes(),b'CHANGED')
 def test_foreign_name_recreated_after_intent_blocks_the_pending_unlink(self):
  before={p.relative_to(self.service_plan['code']).as_posix():p.read_bytes() for p in Path(self.service_plan['code']).rglob('*') if p.is_file()};calls=0
  def recreate(action,pin):
   nonlocal calls
   if action=='REMOVE_CODE':
    calls+=1
    if calls==2:self.backend.service={'foreign':True}
   return True
  with self.assertRaises(ValueError):self.uninstall.run(guard=recreate)
  after={p.relative_to(self.service_plan['code']).as_posix():p.read_bytes() for p in Path(self.service_plan['code']).rglob('*') if p.is_file()}
  self.assertEqual(after,before);self.assertEqual(self.removal.calls.count('REMOVE_SERVICE'),1)
 def test_dangling_foreign_code_junction_is_not_observed_absence(self):
  import subprocess
  self.uninstall.run(guard=self.guard);code=Path(self.service_plan['code']);target=self.root/'owned-empty-link-target';target.mkdir()
  self.assertIn(self.root,target.parents);self.assertIn(self.root,code.parents)
  if os.name=='nt':
   from unified_system.installation_service import _system_directory
   linked=subprocess.run([str(_system_directory()/'cmd.exe'),'/d','/c','mklink','/J',str(code),str(target)],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=10);self.assertEqual(linked.returncode,0)
  else:code.symlink_to(target,target_is_directory=True)
  target.rmdir()
  try:
   self.assertFalse(code.exists());self.assertTrue(code.lstat())
   with self.assertRaises(ValueError):self.uninstall.run(guard=self.guard)
   self.assertTrue(code.lstat());self.assertTrue((self.state/'user-data').exists())
  finally:
   if os.name=='nt':code.rmdir()
   else:code.unlink()
 def test_boundary_cannot_mutate_controller_plan_or_record(self):
  original=self.removal.call
  def mutate(action,plan,record,guard):
   result=original(action,plan,record,guard);plan['root_fingerprint']={'root_device':0,'root_inode':0};record['proof']['state']=4;return result
  self.removal.call=mutate
  self.assertEqual(self.uninstall.run(guard=self.guard)['status'],'APP_ONLY_REMOVED')
  self.assertEqual(self.resource.recorded()['proof']['state'],1)
 def test_other_computer_rejects_before_every_effect(self):
  self.uninstall.preview()
  with patch.object(self.backend,'computer_name',return_value='OTHER-PC'):
   with self.assertRaises(ValueError):self.uninstall.run(guard=self.guard)
  self.assertEqual(self.removal.calls,[]);self.assertFalse(self.uninstall.audit.path.exists());self.assertTrue(Path(self.service_plan['code']).exists())
 def test_parent_root_replacement_is_not_adopted(self):
  self.uninstall.preview();root=Path(self.service_plan['root']);root.rename(root.with_name('retained'))
  root.mkdir();(root/'foreign').write_bytes(b'KEEP')
  with self.assertRaises(ValueError):self.uninstall.run(guard=self.guard)
  self.assertEqual((root/'foreign').read_bytes(),b'KEEP')


 def test_recorded_intent_requires_fresh_bytes_before_unlink(self):
  calls=0
  def interrupt(action,pin):
   nonlocal calls
   if action=='REMOVE_CODE':
    calls+=1
    return calls!=2
   return True
  with self.assertRaises(ValueError):self.uninstall.run(guard=interrupt)
  rows=self.uninstall.audit.read();intent=next(r['receipt']['data'] for r in rows if r['receipt'].get('kind')=='MEMBER_INTENT')
  member=Path(self.service_plan['code'])/intent['path'];self.assertTrue(member.exists());member.write_bytes(b'FOREIGN_CHANGED')
  with self.assertRaises(ValueError):self.uninstall.run(guard=self.guard)
  self.assertEqual(member.read_bytes(),b'FOREIGN_CHANGED');self.assertEqual(self.removal.calls.count('REMOVE_SERVICE'),1)
 def test_fresh_reinstall_never_adopts_or_erases_retained_state(self):
  from unified_system.installation_service import service_plan
  self.uninstall.run(guard=self.guard)
  replacement=service_plan(self.source,self.pin,self.root/'fresh-generation','install','node','CONTROL',self.backend)
  new=ServiceResource.create(replacement,self.backend,self.guard)
  self.assertEqual(new.inspect(self.guard)['status'],'STOPPED_RESOURCE_RECORDED')
  self.assertNotEqual(replacement['state'],self.service_plan['state']);self.assertEqual((self.state/'user-data').read_bytes(),b'PRESERVE_DATA')


class NativeRemovalTests(unittest.TestCase):
 @unittest.skipUnless(os.name=='nt','Windows compile-only native mock regression')
 def test_actual_native_algorithm_uses_same_verified_handle_and_rechecks_state(self):
  import subprocess
  module=Path(__file__).resolve().parents[1]/'scripts/UnifiedOwnedServiceRemoval.psm1'
  regression=r"""
public static class RemovalRegression {
 sealed class Fake:UnifiedOwnedRemovalNative.Kernel {
  public int reads,deletes,closes;public bool running,foreign;
  public IntPtr Open(string name){return new IntPtr(41);}
  public UnifiedOwnedRemovalNative.Snapshot Read(IntPtr h){Need(h==new IntPtr(41));reads++;return new UnifiedOwnedRemovalNative.Snapshot{Binary="\"C:\\fixed\\nssm.exe\"",Account="NT AUTHORITY\\LocalService",Type=16,Start=3,Error=1,Sid=1,State=running?4u:1u};}
  public void Delete(IntPtr h){Need(h==new IntPtr(41)&&reads==2&&closes==0);deletes++;}
  public void Close(IntPtr h){Need(h==new IntPtr(41));closes++;}
  public string Observe(string name){Need(closes==1);return foreign?"PRESENT_REVIEW_REQUIRED":"ABSENT";}
 }
 static void Need(bool ok){if(!ok)throw new InvalidOperationException("SAME_HANDLE_REGRESSION");}
 public static string Run(){var normal=new Fake();Need(UnifiedOwnedRemovalNative.RemoveUsing(normal,"fixed","C:\\fixed\\nssm.exe",()=>{})=="ABSENT"&&normal.deletes==1&&normal.closes==1);var changed=new Fake();bool rejected=false;try{UnifiedOwnedRemovalNative.RemoveUsing(changed,"fixed","C:\\fixed\\nssm.exe",()=>{changed.running=true;});}catch(InvalidOperationException){rejected=true;}Need(rejected&&changed.deletes==0&&changed.closes==1);var foreign=new Fake{foreign=true};Need(UnifiedOwnedRemovalNative.RemoveUsing(foreign,"fixed","C:\\fixed\\nssm.exe",()=>{})=="PRESENT_REVIEW_REQUIRED"&&foreign.deletes==1&&foreign.closes==1);return "SAME_HANDLE_MOCK_ONLY_PASS";}
}
"""
  script="$ErrorActionPreference='Stop';$text=[IO.File]::ReadAllText($env:REMOVAL_SOURCE);$source=[regex]::Match($text,\"(?s)\\$script:Native=@'\\r?\\n(.*?)\\r?\\n'@\").Groups[1].Value;if(-not $source){throw 'SOURCE_UNAVAILABLE'};Add-Type -TypeDefinition ($source+[Environment]::NewLine+$env:REMOVAL_REGRESSION);[RemovalRegression]::Run()"
  child=subprocess.run([str(Path(os.environ['WINDIR'])/'System32/WindowsPowerShell/v1.0/powershell.exe'),'-NoProfile','-NonInteractive','-Command',script],env={**os.environ,'REMOVAL_SOURCE':str(module),'REMOVAL_REGRESSION':regression},capture_output=True,text=True,timeout=30)
  self.assertEqual(child.returncode,0,'compile-only mocked native algorithm failed')
  self.assertEqual(child.stdout.strip(),'SAME_HANDLE_MOCK_ONLY_PASS');self.assertEqual(child.stderr,'')

if __name__=='__main__':unittest.main()
