"""Synthetic data-only operator bundle fixtures; no archived code executes."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
import warnings
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def helper():
    spec=importlib.util.spec_from_file_location('owned_operator_unpacker',ROOT/'scripts/extract_worker_operator.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def bundle(path,*,mutate=None):
    names=['scripts/prepare_worker_capsule.py','integration/source_guard.py','unified_system/__init__.py',
           'unified_system/lab_release.py','unified_system/lab_runtime.py','unified_system/lab_capsule_acl.py']
    names += ['unified_system/fixture_'+str(i)+'.py' for i in range(41)]
    payloads={'operator/'+name:b'raise AssertionError("ARCHIVED_CODE_MUST_NOT_EXECUTE")\n' for name in names}
    lock={'schema':'unified.worker-operator.v1','files':{name:hashlib.sha256(payloads['operator/'+name]).hexdigest() for name in names},'source_manifest_sha256s':['a'*64]}
    raw=(json.dumps(lock,sort_keys=True,separators=(',',':'))+'\n').encode();payloads['operator-lock.json']=raw
    if mutate:mutate(payloads)
    with zipfile.ZipFile(path,'w') as z:
        for name,data in payloads.items():
            member=zipfile.ZipInfo(name);member.create_system=3;member.external_attr=0o100600<<16;member.compress_type=zipfile.ZIP_DEFLATED;z.writestr(member,data)
    return hashlib.sha256(path.read_bytes()).hexdigest(),hashlib.sha256(raw).hexdigest()


class OperatorUnpackTests(unittest.TestCase):
    def test_exact_48_data_members_verify_before_new_target_extraction(self):
        module=helper()
        with tempfile.TemporaryDirectory(prefix='operator-unpack-') as directory:
            root=Path(directory).resolve();archive=root/'bundle.zip';outer,lock=bundle(archive);target=root/'new'
            result=module.extract(archive,outer,lock,target)
            self.assertEqual(result['files'],48);self.assertEqual(result['execution'],'NOT_STARTED')
            self.assertEqual(len([p for p in target.rglob('*') if p.is_file()]),48)
            self.assertTrue((target/'operator/scripts/prepare_worker_capsule.py').read_bytes().startswith(b'raise AssertionError'))
    def test_wrong_outer_or_lock_hash_precedes_target_creation(self):
        module=helper()
        with tempfile.TemporaryDirectory(prefix='operator-unpack-') as directory:
            root=Path(directory).resolve();archive=root/'bundle.zip';outer,lock=bundle(archive)
            for outer_pin,lock_pin in [('0'*64,lock),(outer,'0'*64)]:
                target=root/'new'
                with self.assertRaises(ValueError):module.extract(archive,outer_pin,lock_pin,target)
                self.assertFalse(target.exists())
    def test_extra_duplicate_link_and_traversal_members_fail_before_creation(self):
        module=helper()
        with tempfile.TemporaryDirectory(prefix='operator-unpack-') as directory:
            root=Path(directory).resolve()
            for index,(name,mode) in enumerate([('extra.py',0o100600),('../outside',0o100600),('operator-lock.json',0o100600),('operator/link.py',0o120777)]):
                archive=root/('bad'+str(index)+'.zip');_,lock=bundle(archive)
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore',UserWarning)
                    with zipfile.ZipFile(archive,'a') as z:
                        item=zipfile.ZipInfo(name);item.create_system=3;item.external_attr=mode<<16;item.compress_type=zipfile.ZIP_DEFLATED;z.writestr(item,b'bad')
                target=root/('target'+str(index));outer=hashlib.sha256(archive.read_bytes()).hexdigest()
                with self.assertRaises(ValueError):module.extract(archive,outer,lock,target)
                self.assertFalse(target.exists())
    def test_changed_member_and_existing_target_are_never_accepted(self):
        module=helper()
        with tempfile.TemporaryDirectory(prefix='operator-unpack-') as directory:
            root=Path(directory).resolve();archive=root/'bad.zip'
            outer,lock=bundle(archive,mutate=lambda p:p.update({'operator/unified_system/fixture_0.py':b'tampered'}))
            with self.assertRaises(ValueError):module.extract(archive,outer,lock,root/'new')
            self.assertFalse((root/'new').exists())
            honest=root/'honest.zip';outer,lock=bundle(honest);target=root/'existing';target.mkdir();(target/'keep').write_bytes(b'unchanged')
            with self.assertRaises(ValueError):module.extract(honest,outer,lock,target)
            self.assertEqual((target/'keep').read_bytes(),b'unchanged')
    def test_hardlinked_archive_is_rejected(self):
        module=helper()
        with tempfile.TemporaryDirectory(prefix='operator-unpack-') as directory:
            root=Path(directory).resolve();archive=root/'bundle.zip';outer,lock=bundle(archive);alias=root/'alias.zip'
            try:os.link(archive,alias)
            except OSError:self.skipTest('Hardlinks unavailable')
            with self.assertRaises(ValueError):module.extract(alias,outer,lock,root/'new')
            self.assertFalse((root/'new').exists())
