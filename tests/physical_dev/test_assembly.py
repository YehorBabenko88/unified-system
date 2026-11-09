"""Owned fixture copy-plan DATA; no assembly/execution/native qualification."""
import copy
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.physical_dev import assembly


class AssemblyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.source=self.root/"source";self.source.mkdir()
        (self.source/"data").write_bytes(b"fixture")
        self.destination=self.root/"new-private-package"

    def component(self,**changes):
        return dict(dict(name="source",source_root=str(self.source),destination_prefix="sources/unified",profile="closed-tree"),**changes)

    def plan(self,components=None,**limits):
        return assembly.plan_assembly(components or [self.component()],self.destination,**limits)

    def test_closed_tree_includes_hidden_git_and_binary_files_without_writes(self):
        (self.source/".git").mkdir();(self.source/".git/config").write_bytes(b"inert config")
        (self.source/"binary.dll").write_bytes(b"\0\xff")
        before={p.relative_to(self.source).as_posix():p.read_bytes() for p in self.source.rglob("*") if p.is_file()}
        plan=self.plan()
        self.assertEqual(set(plan["files"]),{"sources/unified/data","sources/unified/.git/config","sources/unified/binary.dll"})
        self.assertEqual(plan["selected_file_count"],3);self.assertEqual(plan["skipped_entry_count"],0)
        self.assertEqual(plan["files"]["sources/unified/data"]["sha256"],hashlib.sha256(b"fixture").hexdigest())
        self.assertFalse(self.destination.exists())
        self.assertEqual(before,{p.relative_to(self.source).as_posix():p.read_bytes() for p in self.source.rglob("*") if p.is_file()})

    def test_python_profile_excludes_precise_caches_but_preserves_dll_closure(self):
        for name in ("python.exe","DLLs/stdlib.pyd","DLLs/helper.dll","Lib/os.py","Lib/site-packages/vendor/private.py","Lib/__pycache__/os.pyc","nested/cache.pyc","nested/cache.pyo","site-packages/included.txt"):
            path=self.source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b"inert")
        plan=self.plan([self.component(profile="python-stdlib",destination_prefix="python")])
        self.assertIn("python/DLLs/stdlib.pyd",plan["files"]);self.assertIn("python/DLLs/helper.dll",plan["files"])
        self.assertIn("python/Lib/os.py",plan["files"]);self.assertIn("python/site-packages/included.txt",plan["files"])
        self.assertEqual(plan["skipped_entry_count"],4);self.assertEqual(plan["skipped_subtree_count"],2)
        self.assertEqual({item["relative_path"] for item in plan["skipped"]},{"Lib/site-packages","Lib/__pycache__","nested/cache.pyc","nested/cache.pyo"})
        self.assertFalse(any("private.py" in key for key in plan["files"]))

    def test_excluded_subtrees_are_not_enumerated(self):
        path=self.source/"Lib/site-packages";path.mkdir(parents=True)
        original=os.scandir
        def selected_only(directory):
            if Path(directory)==path:raise AssertionError("excluded subtree enumerated")
            return original(directory)
        with patch.object(assembly.os,"scandir",side_effect=selected_only):
            plan=self.plan([self.component(profile="python-stdlib")])
        self.assertEqual(plan["skipped_subtree_count"],1)

    def test_no_silent_cap_or_bool_limits(self):
        (self.source/"second").write_bytes(b"more")
        for limits in (dict(max_files=1),dict(max_bytes=5),dict(max_files=True),dict(max_bytes=True),dict(max_files=20001),dict(max_bytes=1073741825)):
            with self.subTest(limits=limits),self.assertRaises(assembly.AssemblyError):self.plan(**limits)
        self.assertFalse(self.destination.exists())

    def test_existing_or_alias_destination_is_not_adopted(self):
        self.destination.mkdir()
        with self.assertRaises(assembly.AssemblyError):self.plan()
        self.destination.rmdir();(self.root/"walk").mkdir()
        for destination in (Path("relative"),self.root/"walk"/".."/"new",self.source/"inside-source"):
            with self.subTest(destination=destination),self.assertRaises(assembly.AssemblyError):assembly.plan_assembly([self.component()],destination)

    def test_source_overlap_unsafe_prefix_and_actual_destination_aliases_refused(self):
        second=self.root/"second";second.mkdir();(second/"data").write_bytes(b"other")
        for change in (dict(source_root=str(self.source)),dict(source_root=str(second),destination_prefix="SOURCES/unified"),dict(source_root=str(second),destination_prefix="../outside")):
            with self.subTest(change=change),self.assertRaises(assembly.AssemblyError):self.plan([self.component(),self.component(name="second",**change)])

    def test_disjoint_nested_prefixes_allow_tooling_lock_seed_and_modules(self):
        seed=self.root/"lock-seed";seed.mkdir();(seed/"package-lock.json").write_bytes(b"inert lock")
        components=[self.component(destination_prefix="tooling/node_modules"),self.component(name="lock",source_root=str(seed),destination_prefix="tooling")]
        plan=self.plan(components)
        self.assertEqual(set(plan["files"]),{"tooling/node_modules/data","tooling/package-lock.json"})
        self.assertEqual(plan["selected_file_count"],2);self.assertEqual(plan["selected_bytes"],17)
        self.assertFalse(self.destination.exists())

    def test_duplicate_final_file_is_refused_before_dictionary_overwrite(self):
        second=self.root/"second";second.mkdir()
        components=[self.component(destination_prefix="tooling"),self.component(name="second",source_root=str(second),destination_prefix="tooling")]
        for raw in (b"fixture",b"different"):
            (second/"data").write_bytes(raw)
            with self.subTest(raw=raw),self.assertRaises(assembly.AssemblyError):self.plan(components)
        self.assertFalse(self.destination.exists())

    def test_equal_directory_prefixes_are_allowed_for_disjoint_final_files(self):
        second=self.root/"second";second.mkdir();(second/"other").write_bytes(b"inert")
        plan=self.plan([self.component(destination_prefix="tooling"),self.component(name="second",source_root=str(second),destination_prefix="tooling")])
        self.assertEqual(set(plan["files"]),{"tooling/data","tooling/other"})
        self.assertEqual(plan["selected_file_count"],2)

    def test_nested_prefix_cannot_turn_a_file_into_a_directory(self):
        second=self.root/"second";second.mkdir();(second/"child").write_bytes(b"inert")
        components=[self.component(destination_prefix="tooling"),self.component(name="second",source_root=str(second),destination_prefix="tooling/data")]
        with self.assertRaises(assembly.AssemblyError):self.plan(components)

    def test_shared_directory_case_alias_rejected_with_disjoint_leaf_names(self):
        second=self.root/"second";second.mkdir();(second/"other").write_bytes(b"inert")
        components=[self.component(destination_prefix="tooling/NODE"),self.component(name="second",source_root=str(second),destination_prefix="tooling/node")]
        with self.assertRaises(assembly.AssemblyError):self.plan(components)

    def test_global_byte_and_file_limits_cover_all_components(self):
        second=self.root/"second";second.mkdir();(second/"data").write_bytes(b"other")
        components=[self.component(),self.component(name="second",source_root=str(second),destination_prefix="other")]
        with self.assertRaises(assembly.AssemblyError):self.plan(components,max_files=1)
        with self.assertRaises(assembly.AssemblyError):self.plan(components,max_bytes=8)

    def test_closed_profiles_and_fields(self):
        for component in (self.component(profile="auto-install"),dict(self.component(),approved=True),self.component(name="bad\nname")):
            with self.subTest(component=component),self.assertRaises(assembly.AssemblyError):self.plan([component])

    def test_hardlinks_fail_even_for_excluded_cache_entries(self):
        alias=self.source/"alias.pyc";os.link(self.source/"data",alias)
        with self.assertRaises(assembly.AssemblyError):self.plan([self.component(profile="python-stdlib")])

    def test_plan_never_attests_git_acl_or_execution(self):
        plan=self.plan()
        self.assertEqual(plan["mode"],"COPY_PLAN_DATA_ONLY")
        self.assertEqual(plan["source_provenance"],"ROOT_PRIMARY_VERIFIER_REQUIRED")
        self.assertEqual(plan["destination_parent_acl"],"UNKNOWN")
        self.assertEqual(plan["public_submit"],"DENY")
        self.assertIs(plan["runtime_admission"],False);self.assertIs(plan["physical_execution_authorization"],False)
        self.assertTrue(plan["requires_exclusive_destination_creation"])

    def test_mutation_during_hash_refused(self):
        original=os.read;changed=False
        def mutate(fd,count):
            nonlocal changed
            result=original(fd,count)
            if not changed:
                changed=True
                with (self.source/"data").open("ab") as stream:stream.write(b"changed")
            return result
        with patch.object(assembly.integrity.os,"read",side_effect=mutate):
            with self.assertRaises(assembly.AssemblyError):self.plan()

    def test_destination_appearing_during_planning_is_not_adopted(self):
        original=os.read;changed=False
        def foreign_create(fd,count):
            nonlocal changed
            data=original(fd,count)
            if not changed:changed=True;self.destination.mkdir()
            return data
        with patch.object(assembly.integrity.os,"read",side_effect=foreign_create):
            with self.assertRaises(assembly.AssemblyError):self.plan()
        self.assertTrue(self.destination.is_dir())

    def test_added_source_member_during_hash_refused(self):
        original=os.read;changed=False
        def extra(fd,count):
            nonlocal changed
            data=original(fd,count)
            if not changed:changed=True;(self.source/".extra").write_bytes(b"new")
            return data
        with patch.object(assembly.integrity.os,"read",side_effect=extra):
            with self.assertRaises(assembly.AssemblyError):self.plan()

    def test_visited_entry_bound_refuses_empty_tree_expansion(self):
        for name in ("one","two","three"):(self.source/name).mkdir()
        with patch.object(assembly,"MAX_ENTRIES",2):
            with self.assertRaises(assembly.AssemblyError):self.plan()

    def test_python_rules_are_casefolded_and_closed_tree_has_no_exclusions(self):
        path=self.source/"LIB/SITE-PACKAGES/file";path.parent.mkdir(parents=True);path.write_bytes(b"inert")
        (self.source/"cached.PYC").write_bytes(b"inert")
        python=self.plan([self.component(profile="python-stdlib")])
        self.assertEqual(python["selected_file_count"],1)
        self.assertEqual(python["skipped_entry_count"],2)
        closed=self.plan()
        self.assertEqual(closed["selected_file_count"],3);self.assertEqual(closed["skipped_entry_count"],0)

    def test_earlier_component_mutated_while_later_component_hashes_is_refused(self):
        second=self.root/"second";second.mkdir();other=second/"data";other.write_bytes(b"second")
        components=[self.component(name="first"),self.component(name="second",source_root=str(second),destination_prefix="other")]
        original=os.read;changed=False
        def mutate_first(fd,count):
            nonlocal changed
            result=original(fd,count)
            if not changed and os.fstat(fd).st_ino==other.stat().st_ino:
                changed=True;target=self.source/"data";before=target.stat();target.write_bytes(b"drifted")
                os.utime(target,ns=(before.st_atime_ns,before.st_mtime_ns+1000000000))
            return result
        with patch.object(assembly.integrity.os,"read",side_effect=mutate_first):
            with self.assertRaises(assembly.AssemblyError):self.plan(components)


if __name__=="__main__":unittest.main()
