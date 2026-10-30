"""Negative provenance controls use disposable Git repositories, never source clones."""
import importlib
import importlib.util
import os
import py_compile
import sys
import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch


class SourceGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.git('init','-q')
        (self.root/'pkg').mkdir();(self.root/'pkg/__init__.py').write_text('VALUE=1\n')
        (self.root/'.gitignore').write_text('*.py\n__pycache__/\n')
        self.git('add','-f','pkg/__init__.py','.gitignore')
        self.git('-c','user.name=Source Test','-c','user.email=source@example.invalid','commit','-qm','fixture')
    def git(self,*args):
        return subprocess.check_output(['git','-C',str(self.root),*args],text=True).strip()
    def guard(self):
        self.assertTrue((Path(__file__).resolve().parents[1]/'integration/source_guard.py').is_file(),'source guard is missing')
        return importlib.import_module('integration.source_guard')
    def test_dirty_tracked_source_is_unqualified(self):
        api=self.guard();(self.root/'pkg/__init__.py').write_text('VALUE=2\n')
        with self.assertRaisesRegex(api.SourceQualificationError,'TRACKED_BYTES'):
            api.SourceFence(self.root).check()
    def test_ignored_untracked_import_shadow_is_rejected(self):
        api=self.guard();(self.root/'pkg/shadow.py').write_text('VALUE=99\n')
        with self.assertRaisesRegex(api.SourceQualificationError,'UNTRACKED_SOURCE'):
            api.SourceFence(self.root).check()
    def test_post_run_mutation_is_rejected(self):
        api=self.guard();fence=api.SourceFence(self.root);fence.check()
        (self.root/'pkg/__init__.py').write_text('VALUE=2\n')
        with self.assertRaisesRegex(api.SourceQualificationError,'TRACKED_BYTES'):fence.finish()
    def test_imported_module_must_belong_to_expected_tracked_tree(self):
        api=self.guard();fence=api.SourceFence(self.root);fence.check()
        external=tempfile.TemporaryDirectory();self.addCleanup(external.cleanup)
        wrong=Path(external.name)/'wrong.py';wrong.write_text('VALUE=99\n')
        with self.assertRaisesRegex(api.SourceQualificationError,'IMPORT_ORIGIN'):
            fence.module(SimpleNamespace(__file__=str(wrong)))
    def test_clean_source_pre_post_and_import_are_qualified(self):
        api=self.guard();fence=api.SourceFence(self.root);before=fence.check()
        self.assertEqual(before['head'],self.git('rev-parse','HEAD'))
        fence.module(SimpleNamespace(__file__=str(self.root/'pkg/__init__.py')))
        self.assertEqual(fence.finish(),before)
    def test_git_canonical_crlf_checkout_matches_head_blob(self):
        api=self.guard();self.git('config','core.autocrlf','true')
        (self.root/'pkg/__init__.py').write_bytes(b'VALUE=1\r\n')
        fence=api.SourceFence(self.root);fence.check()
        fence.module(SimpleNamespace(__file__=str(self.root/'pkg/__init__.py')))
        fence.finish()
    def test_clean_filter_cannot_hide_modified_runtime_bytes(self):
        api=self.guard()
        (self.root/'.gitattributes').write_text('pkg/__init__.py filter=restore\n')
        self.git('add','.gitattributes')
        self.git('-c','user.name=Source Test','-c','user.email=source@example.invalid','commit','-qm','filter fixture')
        self.git('config','filter.restore.clean','git show HEAD:pkg/__init__.py')
        (self.root/'pkg/__init__.py').write_text('VALUE=99\n')
        with self.assertRaises(api.SourceQualificationError):api.SourceFence(self.root).check()
    def test_replace_ref_is_rejected(self):
        api=self.guard()
        replacement=subprocess.check_output(['git','-C',str(self.root),'hash-object','-w','--stdin'],input=b'VALUE=99\n').decode().strip()
        self.git('replace',self.git('rev-parse','HEAD:pkg/__init__.py'),replacement)
        with self.assertRaises(api.SourceQualificationError):api.SourceFence(self.root).check()
    def test_environment_repository_override_is_rejected(self):
        api=self.guard()
        with patch.dict('os.environ',{'GIT_DIR':str(self.root/'.git')}):
            with self.assertRaises(api.SourceQualificationError):api.SourceFence(self.root).check()
    def test_forged_timestamp_bytecode_denied_and_fresh_cache_loads_real_source(self):
        api=self.guard();source=self.root/'pkg/__init__.py';original=source.stat()
        source.write_text('VALUE=9\n');os.utime(source,ns=(original.st_atime_ns,original.st_mtime_ns))
        py_compile.compile(str(source),doraise=True)
        source.write_text('VALUE=1\n');os.utime(source,ns=(original.st_atime_ns,original.st_mtime_ns))
        spec=importlib.util.spec_from_file_location('unsafe_probe',source)
        unsafe=importlib.util.module_from_spec(spec);spec.loader.exec_module(unsafe)
        self.assertEqual(unsafe.VALUE,9,'fixture must prove forged cache actually loads')
        with self.assertRaisesRegex(api.SourceQualificationError,'UNTRACKED_SOURCE'):api.SourceFence(self.root).check()
        with tempfile.TemporaryDirectory() as cache,patch.object(sys,'pycache_prefix',cache):
            fence=api.SourceFence(self.root,isolated_cache=cache);fence.check()
            spec=importlib.util.spec_from_file_location('safe_probe',source)
            safe=importlib.util.module_from_spec(spec);spec.loader.exec_module(safe)
            self.assertEqual(safe.VALUE,1)
            fence.module(safe);fence.finish()
    def test_lexical_short_alias_of_same_canonical_root_is_accepted(self):
        api=self.guard();actual=self.root.resolve();alias=actual.parent/'SHORT~1'
        absolute=Path.absolute
        def lexical_alias(path):
            value=absolute(path)
            try:return alias/value.relative_to(actual)
            except ValueError:return value
        lstat=Path.lstat
        def alias_stat(path):
            try:path=actual/Path(path).relative_to(alias)
            except ValueError:pass
            return lstat(path)
        # Model Windows RUNNER~1 lexical paths while resolving/reading the actual
        # temporary files. No alternate source bytes or import mocks are used.
        fence=api.SourceFence(self.root);fence.check()
        with patch.object(Path,'absolute',lexical_alias),patch.object(Path,'lstat',alias_stat):
            fence.module(SimpleNamespace(__file__=str(self.root/'pkg/__init__.py')))
            fence.finish()
    def test_reparse_ancestor_is_rejected_even_if_canonical_bytes_match(self):
        api=self.guard();fence=api.SourceFence(self.root);fence.check();lstat=Path.lstat
        def reparse_stat(path):
            value=lstat(path)
            if Path(path)==self.root/'pkg':return SimpleNamespace(st_mode=value.st_mode,st_file_attributes=1024)
            return value
        with patch.object(Path,'lstat',reparse_stat):
            with self.assertRaises(api.SourceQualificationError):fence.module(SimpleNamespace(__file__=str(self.root/'pkg/__init__.py')))
