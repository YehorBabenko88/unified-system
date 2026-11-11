"""UNEXECUTED: one explicit stock-exception unittest, not a native fixture."""
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import time
import types
import unittest

BASE = Path('C:/Users/LS-5/.codex/native-output-cap-matrix-d69b699-20261111')
SOURCE = BASE / 'source'
EVIDENCE = BASE / 'allocated-matrix-evidence'
TEMP = BASE / 'matrix-temp'
REAL = Path('C:/Users/LS-5/AppData/Local/Python/pythoncore-3.12-64/python.exe')
PS = Path('C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe')
PS_SHA = '60c9b29843624dd8af6b6a7b26147753be6aeef65098b9a503cc50850afe410f'
TEST = SOURCE / 'tests/test_native_output_cap_assertion.py'
TEST_SHA = 'b822f4ec0d89240c1733b546eef3b00967c524da653ad802830c68b2b5f5191e'
HELPER = SOURCE / 'tests/native_output_cap_assertion.ps1'
HELPER_SHA = '71818734af4f3e1badebec43afb867f106bb4cd692c3a013ad8d4f36126a6b71'
TEST_ID = 'native_output_cap_assertion_controls.NativeOutputCapAssertionControls.test_actual_shared_classifier_stock_exception_matrix'
CASES = ('accept_leaf', 'accept_aggregate_single', 'accept_aggregate_all_cap',
         'accept_method_aggregate', 'accept_target_method_aggregate', 'accept_max_depth',
         'accept_max_nodes', 'reject_null', 'reject_truthy_nonexception', 'reject_deadline',
         'reject_drain_deadline', 'reject_launch_failure', 'reject_unrelated', 'reject_wrong_case',
         'reject_cap_prefix', 'reject_unknown_wrapper', 'reject_nonleaf_cap',
         'reject_empty_aggregate', 'reject_mixed_aggregate', 'reject_nested_mixed',
         'reject_cycle', 'reject_depth', 'reject_nodes', 'reject_oversized_message')


def need(value):
    if not value:
        raise AssertionError('STOCK_MATRIX_DRIVER_DENY')


def ordinary(path, directory=False, system32=False):
    need(path.is_absolute())
    for parent in reversed(path.parents):
        info = parent.lstat()
        need(stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode)
             and not getattr(info, 'st_file_attributes', 0) & 1024)
    info = path.lstat()
    need(not getattr(info, 'st_file_attributes', 0) & 1024 and not stat.S_ISLNK(info.st_mode))
    need(stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
    if not directory:
        need(info.st_nlink >= 1 if system32 and path == PS else info.st_nlink == 1)
    return info


def matches(a, b, same_api):
    for key in ('st_mode', 'st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_nlink'):
        x, y = getattr(a, key), getattr(b, key)
        need(type(x) is int and type(y) is int)
        if key == 'st_mode' and not same_api:
            need(stat.S_IFMT(x) == stat.S_IFMT(y))
        else:
            need(x == y)
    if same_api:
        need(type(a.st_ctime_ns) is int and type(b.st_ctime_ns) is int and a.st_ctime_ns == b.st_ctime_ns)
    absent = object()
    x, y = getattr(a, 'st_birthtime_ns', absent), getattr(b, 'st_birthtime_ns', absent)
    need(not same_api or (x is absent) == (y is absent))
    need(x is absent or type(x) is int)
    need(y is absent or type(y) is int)
    need(x is absent or y is absent or x == y)


def pinned(path, digest, limit, system32=False):
    before = ordinary(path, system32=system32)
    need(0 < before.st_size <= limit)
    with path.open('rb', buffering=0) as stream:
        opened = os.fstat(stream.fileno())
        matches(before, opened, False)
        raw = stream.read(before.st_size + 1)
        matches(opened, os.fstat(stream.fileno()), True)
    matches(before, ordinary(path, system32=system32), True)
    need(len(raw) == before.st_size and hashlib.sha256(raw).hexdigest() == digest)
    return raw


class Result(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.started_ids = []
        self.succeeded_ids = []
        self.subcases = []

    def startTest(self, test):
        self.started_ids.append(test.id())
        super().startTest(test)

    def addSuccess(self, test):
        self.succeeded_ids.append(test.id())
        super().addSuccess(test)

    def addSubTest(self, test, subtest, err):
        self.subcases.append({'id': subtest.params.get('case'), 'passed': err is None})
        super().addSubTest(test, subtest, err)


def main():
    need(sys.argv[1:] == ['--allocated-stock-classifier-matrix'])
    need(os.name == 'nt' and sys.version_info[:3] == (3, 12, 10)
         and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
         and Path(sys.executable) == REAL and sys.pycache_prefix is not None
         and Path(sys.pycache_prefix) == BASE / 'pycache-prefix')
    ordinary(BASE, directory=True)
    ordinary(EVIDENCE, directory=True)
    ordinary(BASE / 'pycache-prefix', directory=True)
    need(not any((BASE / 'pycache-prefix').iterdir()))
    pinned(HELPER, HELPER_SHA, 65536)
    pinned(PS, PS_SHA, 64 * 1024 * 1024, system32=True)
    raw = pinned(TEST, TEST_SHA, 65536)
    module = types.ModuleType('allocated_stock_matrix_source')
    module.__file__ = str(TEST)
    # Exact SHA is checked on this SAME buffer. Non-main only; no project import.
    exec(compile(raw, str(TEST), 'exec'), module.__dict__)
    need(tuple(module.CASE_IDS) == CASES and module.ACCEPT_IDS == frozenset(CASES[:7]))
    need(module.POWERSHELL == PS and module.HELPER == HELPER and module.ROOT == SOURCE)
    suite = module.make_suite()
    need(suite.countTestCases() == 1 and [test.id() for test in suite] == [TEST_ID])
    TEMP.mkdir(exist_ok=False)
    ordinary(TEMP, directory=True)
    previous_temp = tempfile.tempdir
    tempfile.tempdir = str(TEMP)  # only this owned process's two inert capture files
    original_popen, original_matrix = subprocess.Popen, module._run_matrix
    held, attempts, observations = [], [], []
    cleanup = []
    result = None
    primary = None
    stopped = False
    start = time.monotonic()
    profile = {'schema': 'stock-matrix-observation.v1', 'result': 'DENY',
               'test_id': TEST_ID, 'test_sha256': TEST_SHA, 'helper_sha256': HELPER_SHA,
               'powershell_sha256': PS_SHA, 'native_authority': False,
               'raw_ps_output_independently_preserved': False}

    def observed_popen(command, **kwargs):
        need(not stopped and not attempts)
        expected = [str(PS), '-NoProfile', '-NonInteractive', '-EncodedCommand',
                    base64.b64encode(module.PS_MATRIX.encode('utf-16le')).decode('ascii')]
        need(command == expected and set(kwargs) == {'cwd', 'env', 'stdin', 'stdout', 'stderr', 'creationflags'})
        need(kwargs['cwd'] == SOURCE and kwargs['stdin'] == subprocess.DEVNULL
             and kwargs['creationflags'] == subprocess.CREATE_NO_WINDOW)
        environment = {key: value for key, value in os.environ.items()
                       if key.upper() in {'SYSTEMDRIVE', 'PROGRAMDATA', 'TEMP', 'TMP', 'USERPROFILE', 'LOCALAPPDATA', 'APPDATA'}}
        environment.update(SYSTEMROOT='C:\\Windows', WINDIR='C:\\Windows',
                           PSModulePath='C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\Modules',
                           UNIFIED_OUTPUT_CAP_HELPER=str(HELPER))
        need(kwargs['env'] == environment)
        for key in ('stdout', 'stderr'):
            info = os.fstat(kwargs[key].fileno())
            need(stat.S_ISREG(info.st_mode) and info.st_size == 0)
        pinned(PS, PS_SHA, 64 * 1024 * 1024, system32=True)
        attempts.append({'returned_handle': False})  # reserve before backend
        child = original_popen(command, **kwargs)
        held.append(child)  # custody immediately, before any post-constructor assertion
        attempts[0].update(returned_handle=True, pid=child.pid)
        return child

    def observed_matrix():
        need(not observations)
        records = original_matrix()  # observe actual RETURN, never copy classifier
        need(type(records) is dict and tuple(records) == CASES)
        need(all(type(value) is str and value in ('TRUE', 'FALSE', 'NOT_BOOL') for value in records.values()))
        observations.append(dict(records))
        return records

    try:
        subprocess.Popen = observed_popen
        module._run_matrix = observed_matrix
        result = unittest.TextTestRunner(stream=sys.stderr, verbosity=2, resultclass=Result).run(suite)
    except BaseException as error:
        primary = type(error).__name__  # no raw exception text/PS stderr
    finally:
        stopped = True
        subprocess.Popen = original_popen
        module._run_matrix = original_matrix
        tempfile.tempdir = previous_temp
        for child in held:
            fact = {'pid': child.pid, 'cleanup_needed': False, 'uncertain': False, 'returncode': None}
            try:
                status = child.poll()
            except BaseException:
                status = None
                fact['uncertain'] = True
            if status is None:
                fact['cleanup_needed'] = True
                try:
                    child.kill()
                except BaseException:
                    fact['uncertain'] = True
            try:
                status = child.wait(timeout=2)
                fact['returncode'] = status if type(status) is int else None
                if type(status) is not int:
                    fact['uncertain'] = True
            except BaseException:
                fact['uncertain'] = True
            cleanup.append(fact)
        profile.update(primary_failure_type=primary, attempts=attempts, child_retirement=cleanup,
                       actual_return_records=observations[0] if len(observations) == 1 else None,
                       started_ids=result.started_ids if result else [],
                       succeeded_ids=result.succeeded_ids if result else [],
                       subcases=result.subcases if result else [],
                       elapsed_seconds=time.monotonic() - start)
    good = (primary is None and result is not None and result.wasSuccessful()
            and result.testsRun == 1 and not result.skipped
            and result.started_ids == [TEST_ID] and result.succeeded_ids == [TEST_ID]
            and result.subcases == [{'id': case, 'passed': True} for case in CASES]
            and len(observations) == 1 and observations[0] == {
                case: 'TRUE' if case in CASES[:7] else 'FALSE' for case in CASES}
            and len(attempts) == len(held) == len(cleanup) == 1
            and attempts[0]['returned_handle']
            and not cleanup[0]['uncertain'] and not cleanup[0]['cleanup_needed']
            and cleanup[0]['returncode'] == 0 and profile['elapsed_seconds'] < 12)
    # Post-pins cannot bypass finally custody. Any mismatch prevents a PASS profile.
    pinned(TEST, TEST_SHA, 65536)
    pinned(HELPER, HELPER_SHA, 65536)
    pinned(PS, PS_SHA, 64 * 1024 * 1024, system32=True)
    if good:
        profile['result'] = 'ONE_UNIT_24_STOCK_SUBCASES_PASS'
    data = (json.dumps(profile, sort_keys=True, separators=(',', ':')) + '\n').encode('utf8')
    need(len(data) <= 65536)
    with (EVIDENCE / 'matrix-profile.json').open('xb') as stream:
        stream.write(data)
    print(json.dumps({'profile_sha256': hashlib.sha256(data).hexdigest()}, separators=(',', ':')), flush=True)
    return 0 if good else 1


if __name__ == '__main__':
    raise SystemExit(main())
