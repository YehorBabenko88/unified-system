"""Test-only source-bound inventory runner; never a Storage runtime factory."""
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

CASES = {
    "test_contracts.ClaimTests": (
        "test_parse_is_untrusted_and_cannot_promote", "test_parser_rejects_duplicate_numbers_nonascii_and_noncanonical_bytes",
        "test_parser_bounds_and_counterfeit_primitive_types", "test_decoded_copy_cannot_rewrite_original_claim"),
    "test_segments.SegmentTests": (
        "test_python_equality_objects_cannot_impersonate_typed_fields",
        "test_matching_bytes_are_not_authoritative_verification", "test_corruption_and_truncation_cannot_match_original",
        "test_matching_digest_does_not_waive_framing", "test_other_instrument_and_end_boundary_reject",
        "test_count_and_size_and_input_limit_are_independent", "test_claim_rejects_coercion_unknown_fields_and_invalid_lineage",
        "test_claim_detaches_mutable_instrument_input", "test_framed_bytes_do_not_claim_source_completeness",
        "test_caller_cannot_construct_verified_byte_result"),
    "test_retention.RetentionTests": (
        "test_candidate_is_never_an_executable_delete_permission", "test_last_copy_and_missing_verified_survivors_are_retained",
        "test_pins_and_unknown_closure_cannot_be_waived_by_age", "test_file_exists_or_unavailable_or_wrong_hash_does_not_count",
        "test_same_node_or_volume_cannot_supply_independent_survivors", "test_duplicate_identity_and_bool_budget_and_mutable_pin_inputs_reject",
        "test_unknown_target_never_becomes_candidate"),
    "test_checkpoint_vectors.CheckpointVectorTests": (
        "test_exact_owner_schema_and_mapping_snapshots_are_bound", "test_confirmed_unknown_time_is_still_only_an_untrusted_claim",
        "test_observation_does_not_rewrite_content_or_enable_effect", "test_unconfirmed_and_counterfeit_evidence_cannot_promote",
        "test_disposable_file_corruption_is_checked_by_real_bytes"),
}


def inventory(suite):
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            yield from inventory(test)
        else:
            yield test.id()


def source_hashes():
    result = {}
    for prefix in ("unified_system/storage", "tests/storage", "docs/storage"):
        for path in sorted((ROOT / prefix).rglob("*")):
            if path.suffix not in (".py", ".json", ".md") and path.name != ".gitattributes":
                continue
            if path.is_symlink() or path.stat().st_nlink != 1:
                raise RuntimeError("SOURCE_ALIAS_REJECTED")
            raw = path.read_bytes()
            result[path.relative_to(ROOT).as_posix()] = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    return result


def source_git(*args):
    # Caller environment/config is not an authority to reinterpret pinned objects.
    return subprocess.check_output(["git", "--no-replace-objects", "-C", str(ROOT), *args])


def main():
    if source_git("for-each-ref", "--format=%(refname)", "refs/replace").strip():
        raise RuntimeError("REPLACE_REFS_REJECTED_BEFORE_TESTS")
    before = source_hashes()
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests/storage"), top_level_dir=str(ROOT / "tests"))
    actual = sorted(inventory(suite))
    expected = sorted("storage." + group + "." + name for group, names in CASES.items() for name in names)
    if actual != expected:
        raise RuntimeError("EXACT_CASE_INVENTORY_MISMATCH")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    after = source_hashes()
    if before != after:
        raise RuntimeError("SOURCE_CHANGED_DURING_TESTS")
    head = source_git("rev-parse", "HEAD").decode().strip()
    tree = source_git("rev-parse", "HEAD^{tree}").decode().strip()
    dirty = bool(source_git("status", "--porcelain").strip())
    passed = result.wasSuccessful() and not result.skipped and result.testsRun == len(expected)
    print(json.dumps(dict(schema="unified.storage-stage1.local-evidence.v1", evidence_class="NONPRODUCTION_STANDARD_LIBRARY_TESTS",
                         os=platform.platform(), python=sys.version,
                         head=head, tree=tree, working_tree_dirty=dirty, physical_source_hashes=before,
                         cases=actual, tests_run=result.testsRun, skipped=len(result.skipped), passed=passed,
                         runtime_replication_backup_acceptance=False), sort_keys=True, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
