"""Pre-import exact Git byte guard for the isolated local suite only."""
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import stat
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(os.environ['A4_RESULT_EVIDENCE']).resolve()
OUT.mkdir(parents=True, exist_ok=True)
EXPECTED = sorted('test_local_closure.LocalClosureTests.'+name for name in (
    'test_actual_copy_reopen_readback_has_no_replica_or_domain_admission',
    'test_corrupt_source_is_not_repaired_or_counted',
    'test_exact_numeric_payload_is_never_reencoded_and_claim_stays_untrusted',
    'test_graph_missing_duplicate_unknown_cycle_and_role_requirements_reject',
    'test_interrupted_copy_has_no_success_observation_and_keeps_prior_objects',
    'test_local_observation_closed_schema_never_accepts_verified_flags',
    'test_native_capture_commit_and_reconcile_remain_unconditionally_closed',
    'test_raw_types_empty_and_total_bounds_are_independent',
    'test_same_instance_and_reopened_same_root_cannot_copy',
    'test_strict_claim_rejects_unknown_noncanonical_duplicate_and_numeric_length',
    'test_wrong_payload_or_missing_source_is_rejected_before_copy'))


def require(value, code):
    if not value:
        raise RuntimeError(code)


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
    suite = unittest.TestLoader().discover(str(ROOT/'tests/storage/result_publication'))
    actual = sorted(cases(suite))
    require(actual == EXPECTED, 'EXACT_CASES')
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
    passed = result.wasSuccessful() and result.testsRun == 11 and not result.skipped
    report = dict(schema='agent4.local-result-byte-source-evidence.v1', head=head, tree=tree,
        passed=passed, tests=result.testsRun, skips=len(result.skipped), cases=actual,
        primary_git_bindings=expected, module_origins=origins, python=sys.version,
        os=platform.platform(), run_id=os.environ.get('GITHUB_RUN_ID'),
        attempt=os.environ.get('GITHUB_RUN_ATTEMPT'), replica_qualified=False,
        two_failure_domains_qualified=False, native_publication_qualified=False,
        semantic_closure_verified=False, physical_qualified=False, production_admitted=False)
    (OUT/'qualification.json').write_text(json.dumps(report, sort_keys=True, indent=2)+'\n', encoding='utf-8')
    require(passed, 'LOCAL_TEST_FAILURE_OR_SKIP')
    print(json.dumps(dict(passed=True, head=head, tree=tree, tests=11, skips=0, files=len(expected))))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        (OUT/'failure.json').write_text(json.dumps(dict(status='FAILED_NO_QUALIFICATION',
            reason=str(exc), type=type(exc).__name__, production_admitted=False))+'\n', encoding='utf-8')
        raise
