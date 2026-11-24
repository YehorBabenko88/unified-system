"""Pure qualifier controls; never imports or runs Scheduler fixtures.

Design: preserve the old 30-case inventory byte-for-byte; qualify its exact union
with six integrity cases in an additive Windows/Ubuntu CP312 workflow. Bootstrap
verifies the driver before import; driver batch-verifies all raw Git blobs before
and after a bounded child suite. Evidence is external. Existing crash child keeps
its original command (not isolated -I/-S); inherited no-bytecode is scoped locally.
No qualification receipt grants runtime, native or physical authority.
"""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

DRIVER=Path(__file__).resolve().parents[1]/"tools/ci/qualify_preparation_integrity.py"
spec=importlib.util.spec_from_file_location("preparation_qualifier_controls",DRIVER)
module=importlib.util.module_from_spec(spec)
if DRIVER.exists():spec.loader.exec_module(module)


class PreparationQualificationControls(unittest.TestCase):
    def test_runner_temp_is_bound_at_step_time_not_job_env(self):
        workflow=(DRIVER.parents[2]/'.github/workflows/preparation-integrity.yml').read_text()
        job_env=workflow.split('    env:',1)[1].split('    steps:',1)[0]
        self.assertNotIn('${{ runner.',job_env)
        self.assertIn("os.environ['RUNNER_TEMP']",workflow)
        self.assertIn("os.environ['GITHUB_ENV']",workflow)

    def inventory(self):
        old=dict(schema="agent5.component-test-inventory.v2",expected_count=30,
                 expected_ids=["legacy."+str(i) for i in range(30)])
        added=["integrity."+str(i) for i in range(6)]
        new=dict(schema="preparation-integrity-inventory.v1",expected_count=36,
                 preserved_legacy_ids=old["expected_ids"].copy(),added_integrity_ids=added,
                 expected_ids=old["expected_ids"]+added)
        return old,new

    def test_exact_inventory_accepts_only_all_36_unique_ids(self):
        old,new=self.inventory()
        module.validate_inventory(old,new,list(reversed(new["expected_ids"])))
        for ids in (new["expected_ids"][:-1],new["expected_ids"]+["extra"],new["expected_ids"][:-1]+[new["expected_ids"][0]]):
            with self.assertRaises(ValueError):module.validate_inventory(old,new,ids)

    def test_legacy_inventory_and_closed_new_schema_cannot_drift(self):
        old,new=self.inventory()
        for mutate in (lambda n:n["preserved_legacy_ids"].pop(),lambda n:n.update(extra=True),
                       lambda n:n.update(expected_count=True),lambda n:n["added_integrity_ids"].append("extra")):
            changed=copy.deepcopy(new);mutate(changed)
            with self.assertRaises(ValueError):module.validate_inventory(old,changed,changed["expected_ids"])

    def test_raw_bytes_extra_empty_directory_and_cache_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve();(root/"a.py").write_bytes(b"x\n")
            module.check_files(root,{"a.py":b"x\n"})
            (root/"a.py").write_bytes(b"x\r\n")
            with self.assertRaises(ValueError):module.check_files(root,{"a.py":b"x\n"})
            (root/"a.py").write_bytes(b"x\n");(root/"empty").mkdir()
            with self.assertRaises(ValueError):module.check_files(root,{"a.py":b"x\n"})
            (root/"empty").rmdir();(root/"__pycache__").mkdir()
            with self.assertRaises(ValueError):module.check_files(root,{"a.py":b"x\n"})

    def test_unsafe_paths_and_hardlinks_refused(self):
        import os
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve();(root/"a").write_bytes(b"x")
            for name in ("../a","/a","a\\b","A:a"):
                with self.assertRaises(ValueError):module.check_files(root,{name:b"x"})
            os.link(root/"a",root/"b")
            with self.assertRaises(ValueError):module.check_files(root,{"a":b"x","b":b"x"})

    def test_batch_blob_parser_rejects_truncation_wrong_identity_extra(self):
        import hashlib
        raw=b"content";oid=hashlib.sha1(b"blob 7\0"+raw).hexdigest()
        output=oid.encode()+b" blob 7\n"+raw+b"\n"
        self.assertEqual(module.parse_blobs([(oid,7)],output),[raw])
        for bad in (output[:-1],output+b"x",output.replace(b"content",b"changed")):
            with self.assertRaises(ValueError):module.parse_blobs([(oid,7)],bad)

    def test_run_result_requires_zero_skips_and_exact_count(self):
        expected=["case."+str(i) for i in range(36)]
        module.validate_result(dict(ids=expected,tests=36,skips=0,failures=0,errors=0),expected)
        for key in ("tests","skips","failures","errors"):
            result=dict(ids=expected,tests=36,skips=0,failures=0,errors=0);result[key]+=1
            with self.assertRaises(ValueError):module.validate_result(result,expected)

    def test_unpinned_timezone_wheel_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve();wheel=root/"tzdata.whl";wheel.write_bytes(b"untrusted")
            with self.assertRaisesRegex(ValueError,"pin mismatch"):module.validate_zoneinfo(root,wheel)

    def test_git_path_rejects_relative_local_and_nonordinary_without_launch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve()
            for path in (Path("git"),root/"git.exe",root.parent/root.name):
                with self.assertRaises(ValueError):module.approved_git(root,path)
            external=root.parent/(root.name+"-directory");external.mkdir()
            self.addCleanup(external.rmdir)
            with self.assertRaises(ValueError):module.approved_git(root,external)

    def test_windows_git_selector_is_fixed_bin_without_fallback(self):
        workflow=(DRIVER.parents[2]/'.github/workflows/preparation-integrity.yml').read_text()
        self.assertNotIn('C:/Program Files/Git/cmd/git.exe',workflow)
        self.assertEqual(workflow.count('C:/Program Files/Git/bin/git.exe'),2)
        self.assertEqual(module.selected_git_path('nt'),'C:/Program Files/Git/bin/git.exe')
        self.assertEqual(module.selected_git_path('posix'),'/usr/bin/git')

    def test_preflight_failure_preserves_metadata_before_any_spawn(self):
        import json
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve();candidate=root/'git.exe';candidate.write_bytes(b'inert fixture only')
            evidence=root/'preflight.json'
            with patch.object(module.subprocess,'Popen',side_effect=AssertionError('must not spawn')):
                with self.assertRaises(ValueError):module.approved_git(root,candidate,evidence_path=evidence)
            record=json.loads(evidence.read_bytes())
            self.assertEqual(record['selected_git'],str(candidate))
            self.assertIsNone(record['file'])
            self.assertIsNone(record['raw_sha256'])
            self.assertEqual(record['ancestors'],[])
            self.assertIs(record['passed'],False)
            # Existing hardlinks remain refused; metadata is diagnostic only.
            import os
            repository=root/'repository';repository.mkdir()
            os.link(candidate,root/'alias.exe')
            with patch.object(module.subprocess,'Popen',side_effect=AssertionError('must not spawn')):
                with self.assertRaisesRegex(ValueError,'nonordinary Git executable'):
                    module.approved_git(repository,candidate,evidence_path=evidence)
            record=json.loads(evidence.read_bytes())
            self.assertEqual(record['file']['nlink'],2)
            self.assertIsNone(record['raw_sha256'])
            self.assertIs(record['passed'],False)

    def test_unsafe_parent_preserves_null_hash_without_selected_file_access(self):
        import json
        from types import SimpleNamespace
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve();repository=root/'repository';repository.mkdir()
            candidate=root/'git.exe';candidate.write_bytes(b'inert fixture only');evidence=root/'preflight.json'
            real_lstat=Path.lstat;real_read=Path.read_bytes;info=real_lstat(root)
            unsafe=SimpleNamespace(**{name:getattr(info,name) for name in ('st_mode','st_dev','st_ino','st_nlink','st_size','st_mtime_ns','st_ctime_ns')},st_file_attributes=1024)
            def observe(path,*args,**kwargs):
                if path==candidate:raise AssertionError('selected file reached through unsafe parent')
                return unsafe if path==root else real_lstat(path,*args,**kwargs)
            def read(path,*args,**kwargs):
                if path==candidate:raise AssertionError('unsafe selected bytes read')
                return real_read(path,*args,**kwargs)
            with patch.object(Path,'lstat',observe),patch.object(Path,'read_bytes',read),patch.object(module.subprocess,'Popen',side_effect=AssertionError('must not spawn')):
                with self.assertRaises(ValueError):module.approved_git(repository,candidate,evidence_path=evidence)
            record=json.loads(evidence.read_bytes())
            self.assertIs(record['passed'],False);self.assertIsNone(record['raw_sha256'])
            self.assertEqual(record['ancestors'][-1]['path'],str(root))
