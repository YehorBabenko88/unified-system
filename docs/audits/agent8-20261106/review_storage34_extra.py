"""Own actual filesystem negatives; all roots retained inside private audit scratch."""
import base64,hashlib,io,json,os,pathlib,subprocess,sys,unittest,uuid
r=pathlib.Path(__file__).resolve().parents[1];repo=r/'work/review-storage34-cd0286d';out=r/'outputs/phase54';base=r/'work'/('storage34-a8-extra-'+uuid.uuid4().hex[:8]);base.mkdir();assert base.resolve().is_relative_to((r/'work').resolve())
def identity():
 names=subprocess.check_output(['git','--no-replace-objects','-C',str(repo),'ls-tree','-r','--name-only','HEAD'],text=True).splitlines();values={n:hashlib.sha256((repo/n).read_bytes()).hexdigest() for n in names};assert hashlib.sha256(json.dumps(values,sort_keys=True).encode()).hexdigest()=='1d505f1e8902bb8355372ac66dc06e8fa195d505048612ce2918a14ff2dbfe1a';return values
before=identity();sys.path.insert(0,str(repo))
from unified_system.storage import object_store as mod
from unified_system.storage.object_store import ObjectStore,LocalObject,MAX_OBJECT_BYTES
from unified_system.storage.backup import copy_inventory,verify_restore
from unified_system.storage.contracts import StorageBlocked
from unittest.mock import patch
def store(folder):return ObjectStore.create(folder,store_id=str(uuid.uuid4()))
def race(implementation):
 folder=base/('race-'+uuid.uuid4().hex[:6]);s=store(folder);raw=b'actual-original';ref=s.put(raw);path=folder/'objects'/ref.sha256;replacement=folder/'replacement-fixture';replacement.write_bytes(b'corrupt-replacement');newid=mod._identity(replacement.stat());assert newid!=ref.file_identity
 original=mod._read
 def replace_after_read(p,cap):
  value=original(p,cap)
  if p==path:os.replace(replacement,path)
  return value
 with patch.object(mod,'_read',side_effect=replace_after_read):observed=implementation(s,ref.sha256)
 assert path.read_bytes()==b'corrupt-replacement' and observed.file_identity==ref.file_identity,'OBSERVATION_BOUND_TO_UNVERIFIED_REPLACEMENT'
 with unittest.TestCase().assertRaises(StorageBlocked):s.read(ref.sha256)
def legacy(s,sha):
 raw=s.read(sha);current=mod._plain(s._root/'objects'/sha,directory=False);return LocalObject(s.store_id,sha,len(raw),mod._identity(current),'UNQUALIFIED')
red=io.StringIO()
class Red(unittest.TestCase):
 def test_legacy_stat_after_verified_read(self):race(legacy)
rr=unittest.TextTestRunner(stream=red,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Red));(out/'independent-race.RED.log').write_text(red.getvalue(),encoding='utf-8');assert len(rr.failures)==1 and not rr.errors and 'OBSERVATION_BOUND_TO_UNVERIFIED_REPLACEMENT' in red.getvalue()
class Extra(unittest.TestCase):
 def test_current_same_read_identity_and_subsequent_corruption_denial(self):race(lambda s,sha:s.verify(sha))
 def test_three_roots_multiple_binary_empty_objects(self):
  roots=[store(base/('roundtrip-'+str(i))) for i in range(3)];data=[b'',b'\x00\xff\r\n',b'synthetic'*100];refs=[roots[0].put(x) for x in data];inventory=tuple((x.sha256,x.byte_length) for x in refs);a=copy_inventory(roots[0],roots[1],inventory);b=verify_restore(roots[1],roots[2],inventory);self.assertFalse(a.restore_test_passed);self.assertTrue(b.restore_test_passed);self.assertFalse(b.publication_confirmed)
  for raw,ref in zip(data,refs):self.assertEqual(roots[2].read(ref.sha256),raw)
  self.assertEqual(a.inventory_sha256,b.inventory_sha256)
 def test_real_windows_junction_rejected_before_foreign_target_write(self):
  self.assertEqual(sys.platform,'win32');s=store(base/'junction-store');target=base/'junction-target';target.mkdir();sentinel=target/'preserve.bin';sentinel.write_bytes(b'preserve');s._root.joinpath('staging').rename(s._root/'original-staging');link=s._root/'staging'
  script="$ErrorActionPreference='Stop';New-Item -ItemType Junction -Path '"+str(link)+"' -Target '"+str(target)+"'|Out-Null"
  p=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-EncodedCommand',base64.b64encode(script.encode('utf-16le')).decode()],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=20);self.assertEqual(p.returncode,0,p.stderr);self.assertTrue(link.is_junction())
  with self.assertRaises(StorageBlocked):s.put(b'no-foreign-write')
  self.assertEqual(list(target.iterdir()),[sentinel]);self.assertEqual(sentinel.read_bytes(),b'preserve')
 def test_mutated_marker_and_invalid_limits_fail_closed(self):
  s=store(base/'marker-store');ref=s.put(b'bounds')
  for limit in [True,-1,MAX_OBJECT_BYTES+1,1.5,'6']:
   with self.subTest(limit=limit),self.assertRaises(StorageBlocked):s.read(ref.sha256,max_bytes=limit)
  (s._root/'owned-root.json').write_bytes(b'{}')
  with self.assertRaises(StorageBlocked):s.read(ref.sha256)
log=io.StringIO();res=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Extra));(out/'independent-extra.GREEN.log').write_text(log.getvalue(),encoding='utf-8');assert res.wasSuccessful() and res.testsRun==4 and not res.skipped;assert before==identity()
report=dict(head='cd0286dee5fc41cb7a35b0b6ac431a7ebfc25dfb',independent_extra_cases=4,skips=0,legacy_race_RED='1_EXPECTED_ASSERTION_FAILURE_0_ERRORS',current_GREEN=True,actual_windows_junction=True,real_three_root_multiobject_restore=True,raw_files_before_after=307,owned_scratch_retained=str(base),production_admission=False,pilot_rollback_qualified=False,media_durability=False)
(out/'independent-extra.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
