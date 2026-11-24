"""Source-bound combined inventory; frozen Stage1 runner stays unchanged."""
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT/"tests")]
from storage.run_stage1 import CASES, inventory

RUNTIME = {
    "storage.runtime.test_object_store.ObjectStoreTests": (
        "test_actual_bytes_are_content_addressed_and_survive_reopen",
        "test_corruption_is_not_repaired_by_duplicate_put",
        "test_duplicate_and_concurrent_publication_do_not_replace_bytes",
        "test_existing_directory_is_not_implicitly_adopted",
        "test_failed_fsync_never_returns_an_object_receipt",
        "test_hardlinked_object_and_request_paths_are_rejected",
        "test_interrupted_link_leaves_only_invisible_staging",
        "test_local_size_limit_never_bypasses_full_object_verification",
        "test_missing_object_is_explicit_not_empty_data",
        "test_short_writes_are_completed_and_zero_write_fails",
        "test_verification_identity_comes_from_same_verified_read",
        "test_wrong_store_identity_and_changed_root_are_rejected"),
    "storage.runtime.test_backup.BackupTests": (
        "test_actual_three_root_roundtrip_and_inventory_binding",
        "test_copy_alone_is_not_restore_success",
        "test_corrupted_backup_cannot_pass_restore",
        "test_missing_or_wrong_length_inventory_fails",
        "test_same_store_alias_empty_duplicate_and_unbounded_inventory_rejected"),
}


def git(*args):
    return subprocess.check_output(["git", "--no-replace-objects", "-C", str(ROOT), *args])


def bindings():
    result = {}
    for base in ("unified_system/storage", "tests/storage", "docs/storage"):
        for p in sorted((ROOT/base).rglob("*")):
            if p.is_dir():
                continue
            if p.suffix not in (".py", ".md", ".json") and p.name != ".gitattributes":
                continue
            if p.is_symlink() or p.stat().st_nlink != 1:
                raise RuntimeError("SOURCE_ALIAS_REJECTED")
            raw = p.read_bytes()
            result[p.relative_to(ROOT).as_posix()] = dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    return result


def main():
    if git("for-each-ref", "--format=%(refname)", "refs/replace").strip():
        raise RuntimeError("REPLACE_REFS_REJECTED")
    expected = sorted(["storage."+group+"."+name for group, names in CASES.items() for name in names] +
                      [group+"."+name for group, names in RUNTIME.items() for name in names])
    before = bindings()
    suite = unittest.defaultTestLoader.discover(str(ROOT/"tests/storage"), top_level_dir=str(ROOT/"tests"))
    actual = sorted(inventory(suite))
    if actual != expected or len(expected) != 43:
        raise RuntimeError("EXACT_CASE_INVENTORY_MISMATCH")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if bindings() != before:
        raise RuntimeError("SOURCE_CHANGED_DURING_TESTS")
    passed = result.wasSuccessful() and not result.skipped and result.testsRun == 43
    print(json.dumps(dict(schema="storage.isolated-fs.evidence.review1", passed=passed,
        head=git("rev-parse", "HEAD").decode().strip(), tree=git("rev-parse", "HEAD^{tree}").decode().strip(),
        dirty=bool(git("status", "--porcelain").strip()), platform=platform.platform(), python=sys.version,
        cases=actual, tests_run=result.testsRun, skips=len(result.skipped), source_bindings=before,
        production_admission=False, pilot_rollback_qualified=False), sort_keys=True, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
