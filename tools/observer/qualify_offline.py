"""Exact-Git scoped Observer qualification, not native/physical admission.

Creates only a new evidence directory, then executes a fresh exact-byte capsule.
No dependency installation, source database, external request or listener.
"""
import argparse
import ast
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCOPES = ('unified_system/observer/', 'tests/observer/', 'tools/observer/', 'docs/observer/')
EXTRA = {'unified_system/__init__.py', '.github/workflows/observer-offline.yml'}


def need(value, code):
    if not value: raise RuntimeError(code)


def git(*args):
    executable = shutil.which('git')
    need(executable is not None, 'GIT_REQUIRED')
    env = dict(os.environ); env['GIT_NO_LAZY_FETCH'] = '1'
    result = subprocess.run([executable, '--no-replace-objects', '-c', 'core.fsmonitor=false',
        '-C', str(ROOT), *args], capture_output=True, timeout=10, env=env)
    need(result.returncode == 0 and len(result.stdout) <= 2097152, 'READ_ONLY_GIT_FAILED')
    return result.stdout


def source(head):
    need(git('rev-parse', 'HEAD').decode().strip() == head, 'EXACT_HEAD_REQUIRED')
    held = {}; report = {}
    for row in git('ls-tree', '-r', '-z', head).split(b'\0'):
        if not row: continue
        meta, raw_name = row.split(b'\t', 1); mode, kind, oid = meta.split()
        name = raw_name.decode('utf-8')
        if not (name.startswith(SCOPES) or name in EXTRA): continue
        need(mode == b'100644' and kind == b'blob' and '..' not in Path(name).parts, 'SOURCE_ROLE')
        raw = git('cat-file', 'blob', oid.decode())
        need(hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == oid.decode(), 'PRIMARY_BLOB')
        # The unchanged parent __init__ is copied from its primary blob; the
        # original checkout version is never executed (including EOL aliases).
        if name != 'unified_system/__init__.py':
            path = ROOT/name
            need(path.is_file() and not path.is_symlink() and path.stat().st_nlink == 1, 'ORDINARY_SOURCE')
            need(path.read_bytes() == raw, 'RAW_CHECKOUT_SOURCE_MISMATCH')
        held[name] = raw; report[name] = {'bytes':len(raw), 'sha256':hashlib.sha256(raw).hexdigest(), 'git_blob':oid.decode()}
    need(0 < len(held) <= 128 and sum(map(len, held.values())) <= 2097152, 'SOURCE_PROFILE_BOUND')
    return held, report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--head', required=True); parser.add_argument('--out', required=True)
    args = parser.parse_args(); out = Path(args.out)
    need(out.is_absolute() and not out.exists() and out.parent.is_dir(), 'EXCLUSIVE_EVIDENCE_PATH')
    held, before = source(args.head)
    out.mkdir(); capsule = out/'source'; capsule.mkdir()
    for name, raw in held.items():
        path = capsule/name; path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream: stream.write(raw)
    expected = json.loads(held['docs/observer/test-inventory.json'])['ids']
    need(len(expected) == len(set(expected)) == 47, 'DECLARED_INVENTORY')
    sys.path.insert(0, str(capsule))
    suite = unittest.defaultTestLoader.discover(str(capsule/'tests/observer'))
    def ids(group):
        for item in group:
            if isinstance(item, unittest.TestSuite): yield from ids(item)
            else: yield item.id()
    collected = sorted(ids(suite)); need(collected == sorted(expected), 'EXACT_ACTUAL_INVENTORY')
    started = []; succeeded = []; subtests = []
    class Result(unittest.TextTestResult):
        def startTest(self, test): started.append(test.id()); super().startTest(test)
        def addSuccess(self, test): succeeded.append(test.id()); super().addSuccess(test)
        def addSubTest(self, test, subtest, error):
            subtests.append({'id':test.id(), 'success':error is None})
            super().addSubTest(test, subtest, error)
    clock = time.monotonic()
    with (out/'unittest.stderr.original.log').open('w', encoding='utf-8', newline='') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=Result).run(suite)
    after_held, after = source(args.head)
    need(before == after and held == after_held, 'SOURCE_POST_CHANGED')
    capsule_equal = all((capsule/name).read_bytes() == raw for name,raw in held.items())
    ok = (result.wasSuccessful() and not result.skipped and not result.expectedFailures and not result.unexpectedSuccesses
          and result.testsRun == 47 and sorted(started) == collected == sorted(succeeded) and capsule_equal)
    receipt = {'schema':'observer.offline-qualification.v1', 'head':args.head,
        'tree':git('rev-parse', args.head+'^{tree}').decode().strip(), 'scope':'OFFLINE_OBSERVER_ONLY_NOT_HOSTED_NATIVE_OR_PHYSICAL',
        'status':'SCOPED_OFFLINE_PASS' if ok else 'FAIL', 'tests':result.testsRun,
        'failures':len(result.failures), 'errors':len(result.errors), 'skips':len(result.skipped),
        'expected_failures':len(result.expectedFailures), 'unexpected_successes':len(result.unexpectedSuccesses),
        'collected':collected, 'started':started, 'succeeded':succeeded, 'subtests':subtests,
        'seconds':time.monotonic()-clock, 'source_prepost_equal':before == after,
        'capsule_equal':capsule_equal, 'source':before,
        'python_version':sys.version, 'python_executable_sha256':hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
        'runtime_assurance':'HOSTED_OR_LOCAL_STDLIB_METADATA_ONLY_NOT_NATIVE_RUNTIME_QUALIFICATION',
        'live_sources':False, 'real_telegram_delivery':False, 'listener_started':False,
        'mission_journal_opened':False, 'production_db_opened':False, 'physical_accepted':False}
    with (out/'receipt.json').open('x', encoding='utf-8') as stream: json.dump(receipt,stream,indent=2)
    print(json.dumps({k:receipt[k] for k in ('head','tree','status','tests','failures','errors','skips','seconds')}))
    return 0 if ok else 1


if __name__ == '__main__': raise SystemExit(main())
