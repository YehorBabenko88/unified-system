"""Inert outer qualification codec tests; no issued approval or acquisition."""
import copy
import datetime
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import time
import unittest
from unified_system import lab_release as lab
from tests.collector.test_collector_capsule import fixture
from tests.test_ci_collector_operational_admission import authorization, iso

PIN=lambda raw:dict(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
RAW=lab.canonical

def candidate():
 path=Path(__file__).absolute().parents[1]/'unified_system/collector_root_qualification.py'
 spec=importlib.util.spec_from_file_location('unified_system.collector_root_qualification',path)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

class RootQualificationTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  m=fixture(Path(self.temp.name));a=authorization();now=int(time.time());a.update(issued_at=iso(now-10),expires_at=iso(now+3600))
  profile=dict(schema='unified.data-only-collector.profile.v1',mode='SYNTHETIC_OFFLINE',grid_launch_profile='grid.data-only-collector.v1',context_id='1'*32,store_id='11111111-1111-4111-8111-111111111111',source_manifest_sha256=m['files'][m['source_manifest']]['sha256'],instrument_identity='synthetic-btcusdt-v1',limits=dict(frames=1,frame_bytes=16,raw_bytes=32,duration_seconds=10),network=dict(rest=False,websocket=False),features=dict.fromkeys(('trading','training','math','public_submit','authority_mutation'),False),logging=dict(schema='unified.collector.logging.v1',max_file_bytes=1024,file_count=2))
  self.profile=RAW(profile);m['files'][m['collector_profile']]=PIN(self.profile);self.manifest=RAW(m)
  a['source']['source_manifest_sha256']=profile['source_manifest_sha256'];a['capsule'].update(manifest_sha256=PIN(self.manifest)['sha256'],manifest_bytes=len(self.manifest));self.auth=RAW(a)
  self.inventory=RAW({k:v for k,v in m['files'].items() if k.startswith('runtime/python/')})
  self.storage=RAW(dict(raw_profile=dict(max_observations=10,max_payload_occurrence_bytes=1024,max_state_bytes=1048576,sqlite_headroom_bytes=262144,inventory_file_limit=128),lifecycle_headroom_bytes=65536,max_lifecycle_records=100,max_context_bytes=2097152))
  source=dict(a['source']);source.update({k+'_sha256':PIN(RAW(m[k]))['sha256'] for k in ('sources','overlays','runtime','dependencies','directories')})
  p=PIN(b'inert evidence never authority');self.release=dict(schema='unified.collector.root-release-qualification.v2',scope='ORDINARY_SOFTWARE_FOR_C3_ADMISSION',qualification_id='44444444-4444-4444-8444-444444444444',source=source,capsule=dict(manifest=PIN(self.manifest),archive=PIN(b'inert capsule zip')),profile_sha256=PIN(self.profile)['sha256'],copied_runtime_inventory=PIN(self.inventory),primary_evidence=p,artifact_inventory=p,execution_authority=False)
  self.envelope=dict(kind='COLLECTOR_DEVELOPER_MAX_ENVELOPE_V1',scope='EMPIRICAL_SOFTWARE_MEASUREMENT_ONLY',workload=dict(storage_profile=__import__('json').loads(self.storage)))
  self.software=dict(schema='unified.collector.root-software-qualification.v2',scope='ORDINARY_SOFTWARE_FOR_C3_ADMISSION',qualification_id=self.release['qualification_id'],release=PIN(RAW(self.release)),test_cohort=p,source_effects_review=p,measurement_evidence=p,collector_max_envelope=self.envelope,execution_authority=False)
 def call(self,**extra):
  args=dict(authorization_raw=self.auth,manifest_raw=self.manifest,profile_raw=self.profile,copied_runtime_inventory_raw=self.inventory,storage_profile_raw=self.storage);args.update(extra)
  return candidate().parse_root_qualification(RAW(self.release),RAW(self.software),**args)
 def sync(self):self.software['release']=PIN(RAW(self.release))
 def test_valid_outer_is_detached_data_not_support_or_nested_attestation(self):
  out=self.call();self.assertIs(out['execution_authority'],False);self.assertEqual(out['supporting_facts'],'NOT_ATTESTED');self.assertEqual(out['measured_envelope_validation'],'REQUIRED_BY_A5_PRIVATE_CONSUMER');out['release']['source']['head']='f'*40;self.assertEqual(self.release['source']['head'],'a'*40)
 def test_closed_keys_and_no_callbacks(self):
  self.release['approved']=True;self.sync()
  with self.assertRaises(ValueError):self.call()
  with self.assertRaises(TypeError):self.call(validator=lambda:True)
 def test_wrong_source_and_closure_hash_deny(self):
  for key in ('head','runtime_sha256'):
   old=self.release['source'][key];self.release['source'][key]='f'*len(old);self.sync()
   with self.subTest(key=key),self.assertRaises(ValueError):self.call()
   self.release['source'][key]=old
 def test_wrong_release_pin_and_qualification_id_deny(self):
  self.software['release']['bytes']+=1
  with self.assertRaises(ValueError):self.call()
  self.sync();self.software['qualification_id']='55555555-5555-4555-8555-555555555555'
  with self.assertRaises(ValueError):self.call()
 def test_bool_pin_and_authority_alias_deny(self):
  self.release['capsule']['manifest']['bytes']=True;self.sync()
  with self.assertRaises(ValueError):self.call()
  self.release['capsule']['manifest']=PIN(self.manifest);self.release['execution_authority']=0;self.sync()
  with self.assertRaises(ValueError):self.call()
 def test_archive_tag_joins_actual_inner_pin_not_outer_zip(self):
  import json
  a=json.loads(self.auth);a['capsule']['archive']=dict(kind='ARCHIVE',**self.release['capsule']['archive']);self.auth=RAW(a);self.call()
  a['capsule']['archive']['sha256']='f'*64;self.auth=RAW(a)
  with self.assertRaises(ValueError):self.call()
 def test_wrong_profile_and_runtime_inventory_deny(self):
  with self.assertRaises(ValueError):self.call(profile_raw=RAW({}))
  with self.assertRaises(ValueError):self.call(copied_runtime_inventory_raw=RAW({}))
 def test_storage_independent_join_and_bool_alias_deny(self):
  import json
  storage=json.loads(self.storage);storage['max_lifecycle_records']+=1
  with self.assertRaises(ValueError):self.call(storage_profile_raw=RAW(storage))
  storage=json.loads(self.storage);storage['raw_profile']['inventory_file_limit']=True;self.envelope['workload']['storage_profile']=storage
  with self.assertRaises(ValueError):self.call(storage_profile_raw=RAW(storage))
 def test_fixed_qualification_members_in_capsule_are_cyclic_and_deny(self):
  import json
  m=json.loads(self.manifest);m['files']['qualification/software.json']=PIN(b'inert');m['directories'].append('qualification');m['directories'].sort();raw=RAW(m)
  a=json.loads(self.auth);a['capsule'].update(manifest_sha256=PIN(raw)['sha256'],manifest_bytes=len(raw));self.auth=RAW(a);self.release['capsule']['manifest']=PIN(raw);self.sync()
  with self.assertRaises(ValueError):self.call(manifest_raw=raw)
 def test_duplicate_keys_noncanonical_and_oversized_records_deny(self):
  api=candidate().parse_root_qualification
  for raw in (b'{"schema":0,"schema":1}\n',b' {}\n',b' '*65537):
   with self.subTest(raw=raw[:20]),self.assertRaises(ValueError):api(raw,RAW(self.software),authorization_raw=self.auth,manifest_raw=self.manifest,profile_raw=self.profile,copied_runtime_inventory_raw=self.inventory,storage_profile_raw=self.storage)
 def test_nested_data_never_claims_a5_validation(self):
  self.envelope['unvalidated_case']='this is deliberately not an A5-valid envelope'
  self.assertEqual(self.call()['measured_envelope_validation'],'REQUIRED_BY_A5_PRIVATE_CONSUMER')

 def test_no_process_network_or_dll_acquisition(self):
  from unittest.mock import patch
  with patch('subprocess.Popen',side_effect=AssertionError('process forbidden')) as process,patch('socket.socket',side_effect=AssertionError('network forbidden')) as network,patch('ctypes.WinDLL',side_effect=AssertionError('DLL forbidden'),create=True) as dll,patch('threading.Thread.start',side_effect=AssertionError('thread forbidden')) as thread:
   self.assertIs(self.call()['execution_authority'],False)
   for sentinel in (process,network,dll,thread):sentinel.assert_not_called()
 def test_no_acquisition_fixture_without_platform_windll_attribute(self):
  import sys
  import types
  from unittest.mock import patch
  original=sys.modules.get('ctypes');fake=types.ModuleType('ctypes')
  self.assertFalse(hasattr(fake,'WinDLL'))
  try:
   with patch.dict(sys.modules,{'ctypes':fake}):
    self.test_no_process_network_or_dll_acquisition()
    self.assertFalse(hasattr(fake,'WinDLL'))
  finally:
   self.assertIs(sys.modules.get('ctypes'),original)
   self.assertFalse(hasattr(fake,'WinDLL'))
 def test_old_schema_and_software_authority_deny(self):
  self.release['schema']='unified.owned-collector-stopped-service.v1';self.sync()
  with self.assertRaises(ValueError):self.call()
  self.release['schema']='unified.collector.root-release-qualification.v2';self.sync();self.software['execution_authority']=True
  with self.assertRaises(ValueError):self.call()
 def test_exact_bytes_type_and_unknown_pin_key_deny(self):
  class Bytes(bytes):pass
  for key,raw in (('authorization_raw',self.auth),('manifest_raw',self.manifest),('profile_raw',self.profile),('copied_runtime_inventory_raw',self.inventory),('storage_profile_raw',self.storage)):
   with self.subTest(key=key),self.assertRaises(ValueError):self.call(**{key:Bytes(raw)})
  with self.assertRaises(ValueError):candidate().parse_root_qualification(Bytes(RAW(self.release)),RAW(self.software),authorization_raw=self.auth,manifest_raw=self.manifest,profile_raw=self.profile,copied_runtime_inventory_raw=self.inventory,storage_profile_raw=self.storage)
  with self.assertRaises(ValueError):candidate().parse_root_qualification(RAW(self.release),Bytes(RAW(self.software)),authorization_raw=self.auth,manifest_raw=self.manifest,profile_raw=self.profile,copied_runtime_inventory_raw=self.inventory,storage_profile_raw=self.storage)
  self.release['artifact_inventory']['approved']=True;self.sync()
  with self.assertRaises(ValueError):self.call()
