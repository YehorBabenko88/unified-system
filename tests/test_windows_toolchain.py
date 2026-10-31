import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from unified_system.windows_toolchain import read_catalog, validate_catalog, validate_artifact_directory


class ToolchainTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.catalog=read_catalog()
    def populate(self):
        for item in self.catalog['artifacts']:
            data=('inert-fixture-'+item['component']).encode()
            item.update(sha256=hashlib.sha256(data).hexdigest(),expected_bytes=len(data),max_bytes=100)
            (self.root/item['filename']).write_bytes(data)
    def test_missing_artifacts_and_unlocked_components_block_closure(self):
        result=validate_artifact_directory(self.root)
        self.assertEqual({r['status'] for r in result['artifacts']},{'MISSING'})
        self.assertFalse(result['all_locked_artifacts_match']);self.assertFalse(result['installation_closure'])
        self.assertEqual({r['component'] for r in result['required_unlocked']},{'python-wheels','consul'})
        self.assertFalse(result['execution_authority']);self.assertFalse(result['publisher_authenticated'])
    def test_same_bytes_are_integrity_only_even_if_every_locked_artifact_present(self):
        self.populate();before={p.name:p.read_bytes() for p in self.root.iterdir()}
        result=validate_artifact_directory(self.root,catalog=self.catalog)
        self.assertTrue(result['all_locked_artifacts_match']);self.assertFalse(result['installation_closure'])
        self.assertEqual({r['status'] for r in result['artifacts']},{'BYTES_MATCH'})
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.root.iterdir()})
        self.assertEqual(result['native_execution'],'NOT_RUN');self.assertFalse(result['execution_authority'])
        self.assertNotIn(str(self.root),json.dumps(result))
    def test_digest_and_size_mismatch_never_qualify(self):
        self.populate();first=self.catalog['artifacts'][0];path=self.root/first['filename']
        original=path.read_bytes();path.write_bytes(b'x'*len(original))
        report=validate_artifact_directory(self.root,catalog=self.catalog)
        self.assertEqual(report['artifacts'][0]['status'],'DIGEST_MISMATCH')
        path.write_bytes(b'x'*101)
        self.assertEqual(validate_artifact_directory(self.root,catalog=self.catalog)['artifacts'][0]['status'],'SIZE_MISMATCH')
    def test_malformed_catalog_and_unlocked_policy_cannot_silently_shrink(self):
        changes=[lambda c:c.update(schema='unknown'),lambda c:c.update(platform='linux'),
            lambda c:c.update(required_unlocked=[]),lambda c:c['artifacts'].pop(),
            lambda c:c['artifacts'][0].update(filename='../escape'),lambda c:c['artifacts'][0].update(filename='NUL.zip'),
            lambda c:c['artifacts'][0].update(sha256='0'*63),lambda c:c['artifacts'][0].update(max_bytes=True),
            lambda c:c['artifacts'][0].update(expected_bytes=0),lambda c:c['artifacts'][0].update(url='http://nodejs.org/a'),
            lambda c:c['artifacts'][0].update(url='https://untrusted.invalid/a'),lambda c:c['artifacts'][0].update(extra='unknown'),
            lambda c:c['artifacts'][1].update(filename=c['artifacts'][0]['filename'].upper()),
            lambda c:c['artifacts'][0].update(url=c['artifacts'][0]['url']+'?token=secret')]
        for change in changes:
            with self.subTest(change=changes.index(change)):
                bad=copy.deepcopy(self.catalog);change(bad)
                with self.assertRaises(ValueError):validate_catalog(bad)
    def test_external_namespace_rejected_before_metadata_and_fixed_drive_guard_reused(self):
        with patch('pathlib.Path.lstat',side_effect=AssertionError('metadata touched')):
            with self.assertRaises(ValueError):validate_artifact_directory('//office.invalid/share')
        from unified_system.owned_python import reject_external_namespace
        with self.assertRaises(ValueError):reject_external_namespace('Z:\\artifacts',platform='nt',drive_type=lambda _:4)
        with self.assertRaises(ValueError):validate_artifact_directory(self.root/'..'/'outside')
    def test_hardlinks_and_unreadable_files_are_unverified(self):
        self.populate();item=self.catalog['artifacts'][0];path=self.root/item['filename']
        os.link(path,self.root/'other-link')
        self.assertEqual(validate_artifact_directory(self.root,catalog=self.catalog)['artifacts'][0]['status'],'UNVERIFIED')
        (self.root/'other-link').unlink()
        with patch('unified_system.windows_toolchain.os.open',side_effect=PermissionError):
            result=validate_artifact_directory(self.root,catalog=self.catalog)
        self.assertEqual({r['status'] for r in result['artifacts']},{'UNVERIFIED'})
    def test_validation_performs_no_network_process_or_output_writes(self):
        self.populate()
        with patch('socket.socket',side_effect=AssertionError('network forbidden')), \
             patch('subprocess.Popen',side_effect=AssertionError('execution forbidden')), \
             patch('pathlib.Path.write_bytes',side_effect=AssertionError('write forbidden')):
            result=validate_artifact_directory(self.root,catalog=self.catalog)
        self.assertTrue(result['all_locked_artifacts_match']);self.assertFalse(result['installation_closure'])

    def test_catalog_duplicate_json_keys_rejected(self):
        path=self.root/'policy.json';path.write_text('{"schema":1,"schema":2}')
        with self.assertRaises(ValueError):read_catalog(path)
