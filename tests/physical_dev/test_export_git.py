"""Fixed-origin exporter controls use only owned inert fixtures."""
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.physical_dev import export_git
from tools.physical_dev import package as integrity
from test_materialize import assert_owned_close_failure


class GitExportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.source=self.root/"installed-git";self.source.mkdir()
        (self.source/"cmd").mkdir();self.main=self.source/"cmd/git.exe";self.main.write_bytes(b"INERT_NOT_AN_EXECUTABLE")
        (self.source/"bin").mkdir();os.link(self.main,self.source/"bin/git.exe")
        (self.source/".hidden").write_bytes(b"hidden")
        self.parent=self.root/"private-evidence";self.parent.mkdir();self.destination=self.parent/"ls5-git-export-fixture"
        for name,value in (("FIXED_SOURCE",self.source),("FIXED_EVIDENCE_PARENT",self.parent),("PINNED_GIT_EXE_SHA256",hashlib.sha256(self.main.read_bytes()).hexdigest())):
            control=patch.object(export_git,name,value);control.start();self.addCleanup(control.stop)

    def test_existing_hardlinked_source_becomes_independent_singlelink_outputs(self):
        before=self.main.stat();receipt=export_git.export_git(self.destination)
        first=self.destination/"cmd/git.exe";second=self.destination/"bin/git.exe"
        self.assertEqual(first.read_bytes(),self.main.read_bytes());self.assertEqual(second.read_bytes(),self.main.read_bytes())
        self.assertEqual(first.stat().st_nlink,1);self.assertEqual(second.stat().st_nlink,1)
        self.assertNotEqual(first.stat().st_ino,second.stat().st_ino)
        self.assertNotEqual(first.stat().st_ino,self.main.stat().st_ino)
        self.assertEqual(self.main.stat().st_nlink,before.st_nlink);self.assertEqual(self.main.stat().st_mtime_ns,before.st_mtime_ns)
        self.assertEqual(receipt["source_hardlink_file_count"],2)
        self.assertIn(".hidden",receipt["files"])
        self.assertEqual(receipt["files"]["cmd/git.exe"]["sha256"],export_git.PINNED_GIT_EXE_SHA256)

    def test_wrong_fixed_main_pin_refuses_before_any_output(self):
        with patch.object(export_git,"PINNED_GIT_EXE_SHA256","0"*64):
            with self.assertRaises(export_git.ExportError):export_git.export_git(self.destination)
        self.assertFalse(self.destination.exists())

    def test_main_pin_is_rechecked_after_complete_prewrite_snapshot(self):
        original=export_git._snapshot;changed=False
        def change_after_early_pin(root):
            nonlocal changed
            if not changed:
                changed=True;before=self.main.stat();self.main.write_bytes(b"X"*before.st_size)
                os.utime(self.main,ns=(before.st_atime_ns,before.st_mtime_ns))
            return original(root)
        with patch.object(export_git,"_snapshot",side_effect=change_after_early_pin):
            with self.assertRaises(export_git.ExportError):export_git.export_git(self.destination)
        self.assertFalse(self.destination.exists())

    def test_missing_main_refuses_before_output(self):
        self.main.unlink()
        with self.assertRaises(export_git.ExportError):export_git.export_git(self.destination)
        self.assertFalse(self.destination.exists())

    def test_fixed_parent_name_and_existing_output_not_adopted(self):
        for destination in (self.root/"ls5-git-export-outside",self.parent/"other-prefix"):
            with self.subTest(destination=destination),self.assertRaises(export_git.ExportError):export_git.export_git(destination)
            self.assertFalse(destination.exists())
        self.destination.mkdir();foreign=self.destination/"foreign";foreign.write_bytes(b"keep")
        with self.assertRaises(export_git.ExportError):export_git.export_git(self.destination)
        self.assertEqual(foreign.read_bytes(),b"keep")

    def test_public_api_has_no_origin_or_pin_override(self):
        with self.assertRaises(TypeError):export_git.export_git(self.destination,source=self.source)
        with self.assertRaises(TypeError):export_git.export_git(self.destination,pin=export_git.PINNED_GIT_EXE_SHA256)

    def test_source_growth_during_copy_keeps_partial_evidence(self):
        original=os.read;changed=False
        def mutate(fd,count):
            nonlocal changed
            data=original(fd,count)
            if not changed and self.destination.exists() and os.fstat(fd).st_ino==self.main.stat().st_ino:
                changed=True
                with self.main.open("ab") as stream:stream.write(b"change")
            return data
        with patch.object(export_git.os,"read",side_effect=mutate):
            with self.assertRaises(export_git.ExportError):export_git.export_git(self.destination)
        self.assertTrue(changed);self.assertTrue(self.destination.exists())

    def test_write_failure_preserves_partial_output(self):
        with patch.object(export_git.os,"write",side_effect=OSError("owned fixture full disk")):
            with self.assertRaises(export_git.ExportError):export_git.export_git(self.destination)
        self.assertTrue(self.destination.exists());self.assertTrue(any(p.is_file() for p in self.destination.rglob("*")))

    def test_new_source_member_during_copy_is_not_omitted(self):
        original=os.read;changed=False
        def add(fd,count):
            nonlocal changed
            data=original(fd,count)
            if not changed and self.destination.exists():changed=True;(self.source/".late").write_bytes(b"new")
            return data
        with patch.object(export_git.os,"read",side_effect=add):
            with self.assertRaises(export_git.ExportError):export_git.export_git(self.destination)
        self.assertTrue(changed);self.assertTrue(self.destination.exists())

    def test_noncanonical_source_alias_is_not_normalized_or_adopted(self):
        (self.source/"walk").mkdir()
        with patch.object(export_git,"FIXED_SOURCE",self.source/"walk"/".."):
            with self.assertRaises(export_git.ExportError):export_git.export_git(self.destination)
        self.assertFalse(self.destination.exists())

    def test_entire_tree_limits_are_refusals_not_omissions(self):
        for name,value in (("MAX_FILES",1),("MAX_BYTES",1)):
            with patch.object(export_git,name,value):
                with self.subTest(limit=name),self.assertRaises(export_git.ExportError):export_git.export_git(self.destination)
            self.assertFalse(self.destination.exists())

    def test_reparse_control_refuses_without_output(self):
        original=Path.lstat
        class Reparse:
            st_file_attributes=1024
        def reparse(path,*args,**kwargs):
            return Reparse() if path==self.main else original(path,*args,**kwargs)
        with patch.object(Path,"lstat",reparse):
            with self.assertRaises(export_git.ExportError):export_git.export_git(self.destination)
        self.assertFalse(self.destination.exists())

    def test_receipt_is_data_external_to_tree_and_never_attests_vendor_or_dlls(self):
        receipt=export_git.export_git(self.destination)
        self.assertEqual(receipt["status"],"EXPORTED_DEPENDENCY_BYTES_ONLY")
        self.assertEqual(receipt["publisher_attestation"],"NOT_ESTABLISHED")
        self.assertEqual(receipt["loaded_dll_attestation"],"NOT_ESTABLISHED")
        self.assertIs(receipt["runtime_admission"],False);self.assertIs(receipt["physical_execution_authorization"],False)
        self.assertEqual(receipt["public_submit"],"DENY")
        self.assertEqual(set(receipt["files"]),{p.relative_to(self.destination).as_posix() for p in self.destination.rglob("*") if p.is_file()})

    def test_empty_source_directories_are_not_omitted(self):
        (self.source/"empty/subdirectory").mkdir(parents=True)
        receipt=export_git.export_git(self.destination)
        self.assertTrue((self.destination/"empty/subdirectory").is_dir())
        self.assertIn("empty/subdirectory",receipt["directories"])

    def test_export_target_close_failure_still_attempts_source_close(self):
        target=self.root/"export-target-close.exe"
        identity=integrity._signature(self.main.lstat())
        assert_owned_close_failure(self,lambda:export_git._hash_copy(self.main,identity,target))
        self.assertTrue(target.exists())

    def test_export_prior_write_failure_preserved_despite_target_close_failure(self):
        target=self.root/"export-write-close.exe"
        identity=integrity._signature(self.main.lstat())
        assert_owned_close_failure(self,lambda:export_git._hash_copy(self.main,identity,target),write_failure=True)
        self.assertTrue(target.exists())

    def test_export_caller_handled_exception_cannot_hide_new_close_failure(self):
        target=self.root/"export-caller-except.exe";identity=integrity._signature(self.main.lstat())
        try:raise LookupError("inert caller handled error")
        except LookupError:
            assert_owned_close_failure(self,lambda:export_git._hash_copy(self.main,identity,target))


if __name__=="__main__":unittest.main()
