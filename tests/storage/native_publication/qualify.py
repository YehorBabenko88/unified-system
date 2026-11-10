"""Pre-import exact Git byte guard for the isolated local suite only."""
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import runpy
import stat
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(os.environ['A4_RESULT_EVIDENCE']).resolve()
OUT.mkdir(parents=True, exist_ok=True)
ORIGINAL_REQUIRED = ('test_actual_inventory_readback.ActualInventoryReadbackTests.test_actual_all_objects_and_metadata_root_readback_has_same_read_identities', 'test_actual_inventory_readback.ActualInventoryReadbackTests.test_destination_actual_corruption_and_root_corruption_refuse_observation', 'test_actual_inventory_readback.ActualInventoryReadbackTests.test_no_public_constructor_copy_or_pickle_can_mint_native_proof', 'test_actual_inventory_readback.ActualInventoryReadbackTests.test_two_actual_local_copies_never_become_two_qualified_domains', 'test_original_intent_recovery.OriginalIntentRecoveryTests.test_append_response_loss_preserves_actual_committed_local_original', 'test_original_intent_recovery.OriginalIntentRecoveryTests.test_attempt_marker_remains_unknown_without_automatic_resend', 'test_original_intent_recovery.OriginalIntentRecoveryTests.test_corrupt_actual_sqlite_has_closed_unavailable_result', 'test_original_intent_recovery.OriginalIntentRecoveryTests.test_crash_after_durable_attempt_marker_retains_same_original', 'test_original_intent_recovery.OriginalIntentRecoveryTests.test_exact_original_bytes_survive_journal_reopen_without_native_success', 'test_original_intent_recovery.OriginalIntentRecoveryTests.test_exact_retry_does_not_duplicate_and_conflict_never_replaces', 'test_original_intent_recovery.OriginalIntentRecoveryTests.test_exhausted_journal_budget_rejects_before_new_staging_io', 'test_original_intent_recovery.OriginalIntentRecoveryTests.test_foreign_journal_record_and_wrong_schema_are_not_adopted', 'test_original_intent_recovery.OriginalIntentRecoveryTests.test_journal_tamper_fails_and_never_mints_committed_receipt', 'test_original_intent_recovery.OriginalIntentRecoveryTests.test_local_record_rejects_claimed_native_commit_or_result_receipt', 'test_original_intent_recovery.OriginalIntentRecoveryTests.test_missing_or_corrupt_staged_object_is_explicit_without_republication', 'test_original_intent_recovery.OriginalIntentRecoveryTests.test_original_byte_preflight_and_identifiers_reject_before_custom_methods', 'test_original_intent_recovery.OriginalIntentRecoveryTests.test_unknown_id_and_attempt_without_retained_original_do_not_create_state')
ORIGINAL_REQUIRED_SHA256 = '33b577e317ec44aa66ab2b0251831cef884808025dc180b98e4d8323b6017960'
FIXED_PACKET_REQUIRED = ('test_fixed_scientific_packet.FixedScientificPacketTests.test_changed_same_length_bytes_rejected_before_decode', 'test_fixed_scientific_packet.FixedScientificPacketTests.test_exact_packet_retains_bytes_and_no_authority', 'test_fixed_scientific_packet.FixedScientificPacketTests.test_numeric_alias_and_authority_escalation_cannot_enter_profile', 'test_fixed_scientific_packet.FixedScientificPacketTests.test_reviewed_digest_units_and_historical_claims', 'test_fixed_scientific_packet.FixedScientificPacketTests.test_type_size_and_reencoding_rejected_before_decode')
FIXED_PACKET_REQUIRED_SHA256 = '234b647d1f74dbbd9e8ed04f4be2d06142b7c7b020d949d2c85067701060a507'


def require(value, code):
    if not value:
        raise RuntimeError(code)


def validate_inventory(actual):
    """Closed exact IDs; a matching count alone cannot establish coverage."""
    for group, count, pinned in (
        (ORIGINAL_REQUIRED, 17, ORIGINAL_REQUIRED_SHA256),
        (FIXED_PACKET_REQUIRED, 5, FIXED_PACKET_REQUIRED_SHA256),
    ):
        require(type(group) is tuple and len(group) == count
                and all(type(item) is str for item in group), 'REQUIRED_GROUP')
        raw = ('\n'.join(group) + '\n').encode('ascii')
        require(hashlib.sha256(raw).hexdigest() == pinned, 'REQUIRED_GROUP_HASH')
    expected = ORIGINAL_REQUIRED + FIXED_PACKET_REQUIRED
    require(len(set(expected)) == len(expected), 'DUPLICATE_REQUIRED_CASES')
    require(type(actual) in (list, tuple) and all(type(item) is str for item in actual),
            'EXACT_CASES')
    require(len(set(actual)) == len(actual), 'DUPLICATE_CASES')
    require(tuple(sorted(actual)) == tuple(sorted(expected)), 'EXACT_CASES')
    return tuple(sorted(expected))


def git(*args, input=None):
    return subprocess.check_output(['git', '--no-replace-objects', *args], cwd=ROOT, input=input)


def primary():
    require(not git('for-each-ref', '--format=%(refname)', 'refs/replace').strip(), 'REPLACE_REFS')
    listing = []
    for entry in git('ls-tree', '-rz', 'HEAD').split(b'\0'):
        if not entry:
            continue
        meta, path = entry.split(b'\t', 1)
        mode, kind, blob = meta.split()
        require(mode in (b'100644', b'100755') and kind == b'blob', 'SOURCE_TYPE')
        listing.append((path.decode('utf-8'), blob))
    stream = io.BytesIO(git('cat-file', '--batch', input=b'\n'.join(blob for _, blob in listing)+b'\n'))
    bindings = {}
    for path, blob in listing:
        oid, kind, size = stream.readline().split()
        require(oid == blob and kind == b'blob', 'PRIMARY_BLOB')
        raw = stream.read(int(size))
        require(len(raw) == int(size) and stream.read(1) == b'\n', 'PRIMARY_LENGTH')
        bindings[path] = dict(blob=blob.decode(), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    require(not stream.read(), 'PRIMARY_TRAILING_BYTES')
    return bindings


def physical(expected):
    found = {}
    for parent, dirs, files in os.walk(ROOT, followlinks=False):
        if Path(parent) == ROOT:
            dirs[:] = [name for name in dirs if name != '.git']
            files = [name for name in files if name != '.git']
        for name in dirs+files:
            path = Path(parent)/name
            info = path.lstat()
            require(not path.is_symlink() and not getattr(info, 'st_file_attributes', 0) & 1024, 'SOURCE_ALIAS')
        for name in files:
            path = Path(parent)/name
            info = path.lstat()
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, 'SOURCE_LINK_OR_SPECIAL')
            rel = path.relative_to(ROOT).as_posix()
            require(rel in expected, 'UNEXPECTED_SOURCE_FILE')
            raw = path.read_bytes()
            actual = dict(blob=expected[rel]['blob'], bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
            require(actual == expected[rel], 'SOURCE_BYTES')
            found[rel] = actual
    require(found == expected, 'SOURCE_INVENTORY')
    return found


def cases(suite):
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            yield from cases(test)
        else:
            yield test.id()


def main():
    require(platform.python_version() == '3.12.10', 'CPYTHON_VERSION')
    require(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode, 'PYTHON_ISOLATION')
    require(not OUT.is_relative_to(ROOT), 'EVIDENCE_OUTSIDE_SOURCE_REQUIRED')
    head = git('rev-parse', 'HEAD').decode().strip()
    tree = git('rev-parse', 'HEAD^{tree}').decode().strip()
    require(head == os.environ['A4_RESULT_EXPECTED_HEAD'], 'EXPECTED_HEAD')
    expected = primary()
    physical(expected)  # Before project/test imports.
    require(not git('status', '--porcelain', '--untracked-files=all').strip(), 'DIRTY_SOURCE')
    sys.path[:0] = [str(ROOT)]
    controls = runpy.run_path(str(ROOT/'tests/storage/native_publication/inventory_controls.py'))
    with (OUT/'inventory-controls.log').open('w', encoding='utf-8') as log:
        control_result = unittest.TextTestRunner(stream=log, verbosity=2).run(
            controls['make_suite'](validate_inventory, (ORIGINAL_REQUIRED, FIXED_PACKET_REQUIRED)))
    require(control_result.wasSuccessful() and control_result.testsRun == 6
            and not control_result.skipped, 'INVENTORY_CONTROL_FAILURE')
    suite = unittest.TestLoader().discover(str(ROOT/'tests/storage/native_publication'))
    actual = sorted(cases(suite))
    validated_expected = validate_inventory(actual)
    with (OUT/'tests.log').open('w', encoding='utf-8') as log:
        result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    physical(expected)
    require(git('rev-parse', 'HEAD').decode().strip() == head and primary() == expected, 'SOURCE_CHANGED')
    require(not git('status', '--porcelain', '--untracked-files=all').strip(), 'DIRTY_SOURCE_AFTER')
    origins = {}
    for name, module in tuple(sys.modules.items()):
        if name == 'unified_system' or name.startswith('unified_system.'):
            path = Path(module.__file__).resolve()
            rel = path.relative_to(ROOT).as_posix()
            require(rel in expected and path.suffix == '.py', 'PROJECT_ORIGIN')
            origins[name] = rel
    passed = result.wasSuccessful() and result.testsRun == len(validated_expected) and not result.skipped
    report = dict(schema='agent4.native-publication-prerequisites.source-evidence.v1', head=head, tree=tree,
        passed=passed, tests=result.testsRun, skips=len(result.skipped), cases=actual,
        primary_git_bindings=expected, module_origins=origins, python=sys.version,
        os=platform.platform(), run_id=os.environ.get('GITHUB_RUN_ID'),
        attempt=os.environ.get('GITHUB_RUN_ATTEMPT'), replica_qualified=False,
        two_failure_domains_qualified=False, native_publication_qualified=False,
        topology_model="LOGICAL_SAME_HOST_ONLY", recovery_scope="LOCAL_JOURNAL_NOT_NATIVE",
        semantic_closure_verified=False, physical_qualified=False, production_admitted=False)
    (OUT/'qualification.json').write_text(json.dumps(report, sort_keys=True, indent=2)+'\n', encoding='utf-8')
    require(passed, 'LOCAL_TEST_FAILURE_OR_SKIP')
    print(json.dumps(dict(passed=True, head=head, tree=tree, tests=len(validated_expected), skips=0, files=len(expected))))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        (OUT/'failure.json').write_text(json.dumps(dict(status='FAILED_NO_QUALIFICATION',
            reason=str(exc), type=type(exc).__name__, production_admitted=False))+'\n', encoding='utf-8')
        raise
