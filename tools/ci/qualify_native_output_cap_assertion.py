"""Hosted Windows STOCK24 qualifier; source-only preparation until separately authorized CI."""
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import stat
import subprocess
import sys
import threading
import time

BASE = Path(os.environ['QUALIFICATION_BASE'])
SOURCE = Path(os.environ['GITHUB_WORKSPACE'])
CACHE = BASE / 'pycache-prefix'
EVIDENCE = BASE / 'allocated-matrix-evidence'
REAL = Path(sys.executable)
GIT = Path('C:/Program Files/Git/bin/git.exe')
HEAD = os.environ['EXPECTED_HEAD']
TREE = os.environ['QUALIFIED_TREE']
PARENT = os.environ['QUALIFIED_PARENT']
LEDGER_SHA = os.environ['SOURCE_LEDGER_SHA256']
PS = Path('C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe')
PS_SHA = None
DRIVER = BASE / 'child-driver.py'
ORIGIN_SOURCE = r'''
def module_origins(runtime, roles, read_file, extra=None):
    """Observe/admit actual module objects against this run's selected raw map.

    This is origin consistency, not interpreter/loaded-DLL publisher attestation.
    read_file is the fixed caller's held-descriptor hash guard (inert seam only
    for separately allocated controls), never a process or authority callback.
    """
    def need(value):
        if not value:
            raise AssertionError('MODULE_ORIGIN_DENY')
    import _imp
    import importlib.machinery as machinery
    import types
    need(type(runtime) is dict and type(runtime.get('files')) is dict)
    need(len(runtime['files']) <= 20000 and len(roles) <= 2)
    cache = BASE / 'pycache-prefix'
    ordinary(cache, directory=True)
    need(not any(cache.iterdir()))
    known = {Path(name): entry for name, entry in runtime['files'].items()}
    modules = dict(sys.modules)
    for name, module in (extra or {}).items():
        need(name not in modules)
        modules[name] = module
    need(len(modules) <= 512)
    rows = []
    typing_module = modules.get('typing')
    for name, module in sorted(modules.items()):
        need(type(name) is str and 0 < len(name) <= 256 and '\x00' not in name)
        if type(module) is not types.ModuleType:
            need(name in ('typing.io', 'typing.re') and type(typing_module) is types.ModuleType
                 and module is vars(typing_module).get(name.split('.')[1])
                 and type(module) is vars(typing_module).get('_DeprecatedType')
                 and vars(module).get('__module__') == 'typing')
            rows.append({'name': name, 'kind': 'EXACT_TYPING_PSEUDO_CLASS'})
            continue
        data = vars(module)
        spec, file, cached = data.get('__spec__'), data.get('__file__'), data.get('__cached__')
        row = {'name': name, 'kind': None, 'file': file, 'sha256': None, 'cached': cached}
        if name in roles:
            role = roles[name]
            need(spec is None and file == role['path'])
            entry = role
            row['kind'] = 'EXACT_VERIFIED_SOURCE_ROLE'
        else:
            need(type(spec) is machinery.ModuleSpec)
            if spec.origin == 'built-in':
                need(spec.loader is machinery.BuiltinImporter and _imp.is_builtin(spec.name))
                row['kind'] = 'BUILTIN'
            elif spec.origin == 'frozen':
                need(spec.loader is machinery.FrozenImporter and _imp.is_frozen(spec.name))
                row['kind'] = 'FROZEN'
            else:
                need(type(spec.origin) is str and file == spec.origin
                     and type(spec.loader) in (machinery.SourceFileLoader, machinery.ExtensionFileLoader))
                row['kind'] = 'OBSERVED_RUNTIME_FILE'
            entry = known.get(Path(file)) if type(file) is str else None
        if file is not None:
            need(type(file) is str and len(file) <= 2048)
            path = Path(file)
            need(path.is_absolute() and path.suffix.lower() not in ('.pyc', '.pyo')
                 and entry is not None)
            read_file(path, entry)
            row['sha256'] = entry['sha256']
        else:
            need(row['kind'] in ('BUILTIN', 'FROZEN'))
        if cached is not None:
            need(type(cached) is str and len(cached) <= 2048
                 and Path(cached).is_absolute() and Path(cached).is_relative_to(cache)
                 and Path(cached).suffix.lower() == '.pyc')
        rows.append(row)
    ordinary(cache, directory=True)
    need(not any(cache.iterdir()))
    return {'rows': rows, 'row_count': len(rows), 'cache_empty': True,
            'claim': 'ACTUAL_MODULE_ORIGINS_ONLY_NOT_TRANSITIVE_DLL_OR_EXECUTED_BYTE_PROOF'}
'''
CHILD_SOURCE = r'''"""UNEXECUTED: one explicit stock-exception unittest, not a native fixture."""
import base64
import hashlib
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

BASE = Path(os.environ['QUALIFICATION_BASE'])
SOURCE = Path(os.environ['GITHUB_WORKSPACE'])
EVIDENCE = BASE / 'allocated-matrix-evidence'
TEMP = BASE / 'matrix-temp'
REAL = Path(sys.executable)
PS = Path('C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe')
PS_SHA = os.environ['OBSERVED_POWERSHELL_SHA256']
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
    need(0 <= before.st_size <= limit)
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
    runtime_raw = pinned(BASE / 'runtime-ledger.json', os.environ['OBSERVED_RUNTIME_LEDGER_SHA256'], 8 * 1024 * 1024)
    runtime = json.loads(runtime_raw)
    roles = {'__main__': {'path': str(Path(__file__)), 'bytes': ordinary(Path(__file__)).st_size,
                           'sha256': os.environ['OBSERVED_DRIVER_SHA256']},
             'allocated_stock_matrix_source': {'path': str(TEST), 'bytes': len(raw), 'sha256': TEST_SHA}}
    read_origin = lambda path, entry: pinned(path, entry['sha256'], entry['bytes'])
    origins_before = module_origins(runtime, roles, read_origin, {'allocated_stock_matrix_source': module})
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
               'raw_ps_output_independently_preserved': False, 'module_origins_before': origins_before}

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
    profile['module_origins_after'] = module_origins(runtime, roles, read_origin, {'allocated_stock_matrix_source': module})
    if good:
        profile['result'] = 'ONE_UNIT_24_STOCK_SUBCASES_PASS'
    data = (json.dumps(profile, sort_keys=True, separators=(',', ':')) + '\n').encode('utf8')
    need(len(data) <= 256 * 1024)
    with (EVIDENCE / 'matrix-profile.json').open('xb') as stream:
        stream.write(data)
    print(json.dumps({'profile_sha256': hashlib.sha256(data).hexdigest()}, separators=(',', ':')), flush=True)
    return 0 if good else 1


if __name__ == '__main__':
    raise SystemExit(main())
'''
CHILD_SOURCE = CHILD_SOURCE.replace('\n\ndef main():', '\n\n' + ORIGIN_SOURCE + '\n\ndef main():')
DRIVER_SHA = hashlib.sha256(CHILD_SOURCE.encode('utf8')).hexdigest()
FROZEN = {
    'tests/native_output_cap_assertion.ps1': '71818734af4f3e1badebec43afb867f106bb4cd692c3a013ad8d4f36126a6b71',
    'tests/test_installation_service.py': '7f55993256b098d109ba895098dde18a49b6dc16f882cd99e1aafc0d5bdc8039',
    'tests/test_native_output_cap_assertion.py': 'b822f4ec0d89240c1733b546eef3b00967c524da653ad802830c68b2b5f5191e',
}
TEST = SOURCE / 'tests/test_native_output_cap_assertion.py'
HELPER = SOURCE / 'tests/native_output_cap_assertion.ps1'
TEST_ID = 'native_output_cap_assertion_controls.NativeOutputCapAssertionControls.test_actual_shared_classifier_stock_exception_matrix'
CAP = 256 * 1024
WHOLE_END = None
RECORD = {'schema': 'hosted-windows-stock-matrix.v1', 'result': 'DENY',
          'source_head': HEAD, 'source_tree': TREE, 'source_parent': PARENT,
          'driver_source_sha256': DRIVER_SHA,
          'run_id': os.environ['GITHUB_RUN_ID'], 'run_attempt': os.environ['GITHUB_RUN_ATTEMPT'],
          'native_authority': False, 'fixture_import_allowed': False, 'stock_matrix_nonmain_source_load_allowed': True,
          'actual_classifier_subcases_run': 0, 'process_roles': []}
CLOSED_FAILURE_CODES = frozenset('''
ABSOLUTE_PATH_REQUIRED UNSAFE_ANCESTOR UNSAFE_PATH UNSAFE_TYPE SOURCE_HARDLINK
CONTROLLER_WHOLE_BOUND FILE_BOUND FILE_OPEN_CHANGED FILE_READ_CHANGED FILE_CHANGED
RAW_FILE_MISMATCH PRIMARY_BLOB_MISMATCH PREPARATION_INPUT_BOUND PREPARATION_INPUT_CHANGED
PREPARATION_INPUT_OPEN_CHANGED PREPARATION_INPUT_READ_CHANGED PREPARATION_INPUT_PATH_CHANGED
PREPARATION_JSON_DUPLICATE PREPARATION_JSON_INVALID FRESH_PYCACHE_NOT_EMPTY
UNKNOWN_PROCESS_ROLE MAIN_THREAD_REQUIRED CHILD_BOUND_OR_READER_FAILURE CHILD_OUTPUT_REJECTED
INVALID_WAIT_RESULT HELD_CHILD_CLEANUP_UNCERTAIN CHILD_EVIDENCE_WRITE_FAILED
CHILD_LOCAL_COMPLETION_BOUND GIT_ARGUMENTS_NOT_ALLOWED SOURCE_GIT_FAILED
EXACT_SOURCE_OR_HELPER_PRECONDITION SOURCE_OBJECT_REDIRECTION SOURCE_COMMIT_CHANGED
SOURCE_GIT_TYPE SOURCE_GIT_INVENTORY_CHANGED SOURCE_WALK_FAILED SOURCE_EXTRA_FILE
SOURCE_MISSING_OR_EXTRA SOURCE_DIRTY FROZEN_TEST_DOCUMENT_CHANGED RUNTIME_FILE_COUNT
FIXED_TOOL_CHANGED CLOSED_RECEIPT_REQUIRED MODULE_ORIGIN_DENY STOCK_MATRIX_PROFILE_REQUIRED EXPECTED_SINGLE_PREREQUISITE_RED_REQUIRED EXPECTED_ASSERTION_MISSING
EXPECTED_ONE_FAILURE_REQUIRED UNEXPECTED_SETUP_OR_CLASSIFIER_EXECUTION
EXPLICIT_ROOT_ALLOCATION_REQUIRED FIXED_WINDOWS_CPYTHON_REQUIRED
ISOLATED_RUNTIME_AND_FRESH_PREFIX_REQUIRED EVIDENCE_FILE_BOUND
'''.split())


def need(value, code):
    if not value:
        raise AssertionError(code)


def failure_fact(error):
    """Closed normalized type/code only; never raw OS text, arguments or paths."""
    if type(error) is AssertionError:
        code = error.args[0] if len(error.args) == 1 and type(error.args[0]) is str else None
        return {'type': 'ASSERTION', 'code': code if code in CLOSED_FAILURE_CODES else 'UNEXPECTED_ASSERTION'}
    for kind, name in ((subprocess.TimeoutExpired, 'WAIT_TIMEOUT'), (OSError, 'OS_ERROR'),
                       (RuntimeError, 'RUNTIME_ERROR'), (ValueError, 'VALUE_ERROR'),
                       (TypeError, 'TYPE_ERROR'), (KeyboardInterrupt, 'INTERRUPTED')):
        if isinstance(error, kind):
            return {'type': name, 'code': 'UNEXPECTED_' + name}
    return {'type': 'UNEXPECTED', 'code': 'UNEXPECTED_FAILURE'}


def ordinary(path, directory=False, single=False):
    need(path.is_absolute(), 'ABSOLUTE_PATH_REQUIRED')
    for parent in reversed(path.parents):
        info = parent.lstat()
        need(stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode)
             and not getattr(info, 'st_file_attributes', 0) & 1024, 'UNSAFE_ANCESTOR')
    info = path.lstat()
    need(not stat.S_ISLNK(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & 1024,
         'UNSAFE_PATH')
    need(stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode), 'UNSAFE_TYPE')
    if single:
        need(info.st_nlink == 1, 'SOURCE_HARDLINK')
    return info


def clock():
    value = time.monotonic()
    need(WHOLE_END is None or value < WHOLE_END, 'CONTROLLER_WHOLE_BOUND')
    return value


def _metadata_matches(left, right, *, same_api: bool) -> bool:
    """Strict common identity; ctime comparisons stay within each API baseline."""
    if type(same_api) is not bool:
        return False
    absent = object()
    common = ('st_mode', 'st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_nlink')
    for name in common + (('st_ctime_ns',) if same_api else ()):
        first = getattr(left, name, absent)
        second = getattr(right, name, absent)
        if type(first) is not int or type(second) is not int:
            return False
        if name == 'st_mode' and not same_api:
            if stat.S_IFMT(first) != stat.S_IFMT(second):
                return False
        elif first != second:
            return False
    first_birth = getattr(left, 'st_birthtime_ns', absent)
    second_birth = getattr(right, 'st_birthtime_ns', absent)
    first_present = first_birth is not absent
    second_present = second_birth is not absent
    if same_api and first_present != second_present:
        return False
    if first_present and type(first_birth) is not int:
        return False
    if second_present and type(second_birth) is not int:
        return False
    if first_present and second_present and first_birth != second_birth:
        return False
    return True


def hash_file(path, entry=None, single=False):
    before = ordinary(path, single=single)
    limit = entry['bytes'] if entry is not None else 64 * 1024 * 1024
    need(0 <= before.st_size <= limit <= 128 * 1024 * 1024, 'FILE_BOUND')
    digest = hashlib.sha256()
    blob = hashlib.sha1(b'blob ' + str(before.st_size).encode() + b'\0')
    count = 0
    with path.open('rb', buffering=0) as stream:
        opened = os.fstat(stream.fileno())
        need(_metadata_matches(before, opened, same_api=False), 'FILE_OPEN_CHANGED')
        while True:
            clock()
            block = stream.read(65536)
            if not block:
                break
            count += len(block)
            need(count <= limit, 'FILE_BOUND')
            digest.update(block)
            blob.update(block)
        after = os.fstat(stream.fileno())
        need(_metadata_matches(opened, after, same_api=True), 'FILE_READ_CHANGED')
    need(_metadata_matches(before, path.lstat(), same_api=True) and count == before.st_size, 'FILE_CHANGED')
    result = {'bytes': count, 'sha256': digest.hexdigest(), 'git_blob': blob.hexdigest()}
    if entry is not None:
        need(result['bytes'] == entry['bytes'] and result['sha256'] == entry['sha256'], 'RAW_FILE_MISMATCH')
        if 'git_blob' in entry:
            need(result['git_blob'] == entry['git_blob'], 'PRIMARY_BLOB_MISMATCH')
    return result


def pinned_json(name, digest):
    path = BASE / name
    before = ordinary(path, single=True)  # root-first before opening any leaf
    limit = 2 * 1024 * 1024
    need(0 <= before.st_size <= limit, 'PREPARATION_INPUT_BOUND')
    flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
    with os.fdopen(os.open(path, flags), 'rb', buffering=0) as stream:
        opened = os.fstat(stream.fileno())
        need(_metadata_matches(before, opened, same_api=False), 'PREPARATION_INPUT_OPEN_CHANGED')
        chunks = []
        count = 0
        # The held descriptor reads at most declared size+1; no hash-then-reopen.
        while count <= before.st_size:
            clock()
            block = stream.read(min(65536, before.st_size + 1 - count))
            if not block:
                break
            count += len(block)
            chunks.append(block)
        after = os.fstat(stream.fileno())
        need(_metadata_matches(opened, after, same_api=True) and count == before.st_size,
             'PREPARATION_INPUT_READ_CHANGED')
    need(_metadata_matches(before, ordinary(path, single=True), same_api=True), 'PREPARATION_INPUT_PATH_CHANGED')
    raw = b''.join(chunks)
    need(hashlib.sha256(raw).hexdigest() == digest, 'PREPARATION_INPUT_CHANGED')

    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            need(key not in result, 'PREPARATION_JSON_DUPLICATE')
            result[key] = value
        return result

    try:
        return json.loads(raw, object_pairs_hook=unique_pairs,
                          parse_constant=lambda _: need(False, 'PREPARATION_JSON_INVALID'))
    except (ValueError, UnicodeError, RecursionError):
        raise AssertionError('PREPARATION_JSON_INVALID') from None


def cache_empty():
    ordinary(CACHE, directory=True)
    need(not any(CACHE.iterdir()), 'FRESH_PYCACHE_NOT_EMPTY')


def environment(git=False):
    result = {key: value for key, value in os.environ.items()
              if key.upper() in {'SYSTEMDRIVE', 'PROGRAMDATA', 'TEMP', 'TMP', 'USERPROFILE', 'LOCALAPPDATA', 'APPDATA'}}
    result.update(SYSTEMROOT='C:\\Windows', WINDIR='C:\\Windows', PYTHONDONTWRITEBYTECODE='1')
    if not git:
        result.update(QUALIFICATION_BASE=str(BASE), GITHUB_WORKSPACE=str(SOURCE),
                      OBSERVED_POWERSHELL_SHA256=PS_SHA,
                      OBSERVED_RUNTIME_LEDGER_SHA256=RECORD['runtime_ledger_sha256'],
                      OBSERVED_DRIVER_SHA256=DRIVER_SHA)
    if git:
        result.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_SYSTEM=os.devnull,
                      GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_COUNT='0',
                      GIT_NO_REPLACE_OBJECTS='1', GIT_NO_LAZY_FETCH='1',
                      GIT_TERMINAL_PROMPT='0', GIT_OPTIONAL_LOCKS='0', LC_ALL='C', LANG='C')
    return result


def capture(command, role, label, seconds):
    """Bounded direct-child handles, finite readers, no unrelated PID discovery."""
    need(role in ('source_git_inspection', 'actual_classifier_unit_python'), 'UNKNOWN_PROCESS_ROLE')
    need(threading.current_thread() is threading.main_thread(), 'MAIN_THREAD_REQUIRED')
    start = clock()
    end = min(start + seconds, WHOLE_END)
    work_end = end - 1  # cleanup reservation is inside the child deadline
    child = None
    threads = []
    stopped = threading.Event()
    failed = threading.Event()
    events = queue.Queue(maxsize=8)
    reserved = [0]
    reserve_lock = threading.Lock()
    content = {'stdout': bytearray(), 'stderr': bytearray()}
    record = {'role': role, 'label': label, 'direct_child': True,
              'seconds_bound_including_cleanup': seconds, 'combined_output_cap': CAP,
              'cleanup_uncertain': False, 'reader_threads_retired': False,
              'primary_body_failure': None, 'cleanup_failures': [],
              'evidence_failures': [], 'local_bound_failures': [], 'denied': True,
              'observed_elapsed_including_cleanup_evidence': None}
    RECORD['process_roles'].append(record)

    def send(value):
        while not stopped.is_set():
            try:
                events.put(value, timeout=.02)
                return
            except queue.Full:
                continue

    def reader(stream, name):
        buffer = bytearray(65536)
        try:
            while not stopped.is_set():
                count = stream.readinto(buffer)
                if not count:
                    break
                with reserve_lock:
                    if count > CAP - reserved[0]:
                        failed.set()
                        return
                    reserved[0] += count
                send((name, bytes(memoryview(buffer)[:count])))
            send(('done', name))
        except BaseException:
            failed.set()

    # Every post-Popen operation, including first clock and thread setup, is
    # protected by the same unconditional held-handle cleanup path.
    try:
        child = subprocess.Popen(command, cwd=SOURCE, env=environment(role == 'source_git_inspection'),
                                 stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 shell=False, close_fds=True, bufsize=0,
                                 creationflags=subprocess.CREATE_NO_WINDOW)
        record['pid'] = child.pid  # descriptive only; never used for termination
        for stream, name in ((child.stdout, 'stdout'), (child.stderr, 'stderr')):
            thread = threading.Thread(target=reader, args=(stream, name), daemon=True)
            threads.append(thread)
            thread.start()
        done = 0
        while True:
            need(clock() < work_end and not failed.is_set(), 'CHILD_BOUND_OR_READER_FAILURE')
            status = child.poll()
            if done == 2 and status is not None:
                record['returncode'] = status
                break
            try:
                name, data = events.get(timeout=.02)
            except queue.Empty:
                continue
            if name == 'done':
                done += 1
            else:
                content[name].extend(data)
        need(not failed.is_set(), 'CHILD_OUTPUT_REJECTED')
    except BaseException as error:
        # Preserve the primary failure before finally can report another cause.
        record['primary_body_failure'] = failure_fact(error)
        raise
    finally:
        stopped.set()
        uncertain = False
        if child is not None:
            try:
                status = child.poll()
            except BaseException as error:
                uncertain = True
                status = None
                record['cleanup_failures'].append({'stage': 'poll', **failure_fact(error)})
            if status is None:
                try:
                    child.kill()
                    record['kill_attempted'] = True
                except BaseException as error:
                    uncertain = True
                    record['cleanup_failures'].append({'stage': 'kill', **failure_fact(error)})
            try:
                retired = child.wait(timeout=.4)
                need(type(retired) is int, 'INVALID_WAIT_RESULT')
                record['retired_returncode'] = retired
            except BaseException as error:
                uncertain = True
                record['cleanup_failures'].append({'stage': 'wait', **failure_fact(error)})
            for stream, stream_name in ((child.stdout, 'stdout_close'), (child.stderr, 'stderr_close')):
                if stream is not None:
                    try:
                        stream.close()
                    except BaseException as error:
                        uncertain = True
                        record['cleanup_failures'].append({'stage': stream_name, **failure_fact(error)})
        for thread in threads:
            try:
                thread.join(timeout=.15)
                uncertain = uncertain or thread.is_alive()
            except BaseException as error:
                uncertain = True
                record['cleanup_failures'].append({'stage': 'thread_join', **failure_fact(error)})
        try:
            record['reader_threads_retired'] = all(not thread.is_alive() for thread in threads)
        except BaseException as error:
            uncertain = True
            record['cleanup_failures'].append({'stage': 'thread_state', **failure_fact(error)})
        uncertain = uncertain or not record['reader_threads_retired']
        record['observed_output_bytes'] = reserved[0]
        record['cleanup_uncertain'] = uncertain
        # Preserve partial output even when custody/reader/clock observations fail.
        for name, data in content.items():
            try:
                with (EVIDENCE / (label + '.' + name + '.original.bin')).open('xb') as stream:
                    stream.write(data)
            except BaseException as error:
                record['evidence_write_failed'] = True
                record['evidence_failures'].append({'stage': name, **failure_fact(error)})
        # Observe completion AFTER unconditional cleanup and evidence attempts.
        # Late/unknown completion is sticky DENY, never a reason to skip cleanup.
        try:
            finished = time.monotonic()
            finite = type(finished) in (int, float) and float('-inf') < finished < float('inf')
            within = finite and start <= finished <= end
            record['observed_elapsed_including_cleanup_evidence'] = finished - start if finite else None
            record['local_completion_within_bound'] = within
            if not within:
                record['local_bound_failures'].append({'type': 'ASSERTION', 'code': 'CHILD_LOCAL_COMPLETION_BOUND'})
        except BaseException as error:
            within = False
            record['local_completion_within_bound'] = False
            record['local_bound_failures'].append(failure_fact(error))
        record['denied'] = bool(record['primary_body_failure'] or uncertain
                                or record['evidence_failures'] or not within)
        need(not uncertain, 'HELD_CHILD_CLEANUP_UNCERTAIN')
        need(not record.get('evidence_write_failed'), 'CHILD_EVIDENCE_WRITE_FAILED')
        need(within, 'CHILD_LOCAL_COMPLETION_BOUND')
    return bytes(content['stdout']), bytes(content['stderr']), record['returncode']


def git(args, label):
    allowed = args == ('rev-parse', 'HEAD', 'HEAD^{tree}', 'HEAD^')
    allowed = allowed or args == ('ls-tree', '-rlz', '--full-tree', HEAD)
    allowed = allowed or args == ('status', '--porcelain=v1', '--untracked-files=all')
    need(allowed, 'GIT_ARGUMENTS_NOT_ALLOWED')
    command = [str(GIT), '--no-replace-objects', '--no-optional-locks',
               '-c', 'core.hooksPath=NUL', '-c', 'core.fsmonitor=false',
               '-c', 'core.useReplaceRefs=false', '-c', 'protocol.allow=never', *args]
    output, error, status = capture(command, 'source_git_inspection', label, 10)
    need(status == 0 and not error, 'SOURCE_GIT_FAILED')
    return output


def snapshot(ledger, phase):
    clock()
    need(len(ledger) == 1875 and 'tests/native_output_cap_assertion.ps1' in ledger,
         'EXACT_SOURCE_OR_HELPER_PRECONDITION')
    ordinary(SOURCE, directory=True)
    ordinary(SOURCE / '.git', directory=True)
    for name in ('objects/info/alternates', 'objects/info/http-alternates', 'refs/replace', 'info/grafts', 'commondir'):
        path = SOURCE / '.git' / name
        need(not path.exists() and not path.is_symlink(), 'SOURCE_OBJECT_REDIRECTION')
    ids = git(('rev-parse', 'HEAD', 'HEAD^{tree}', 'HEAD^'), phase + '-git-identities').decode('ascii').splitlines()
    need(ids == [HEAD, TREE, PARENT], 'SOURCE_COMMIT_CHANGED')
    listing = git(('ls-tree', '-rlz', '--full-tree', HEAD), phase + '-git-inventory')
    entries = {}
    for row in listing.split(b'\0'):
        if not row:
            continue
        meta, name = row.split(b'\t', 1)
        mode, kind, oid, size = meta.split()
        need(kind == b'blob' and mode in (b'100644', b'100755'), 'SOURCE_GIT_TYPE')
        entries[name.decode('utf8')] = (mode.decode(), oid.decode(), int(size))
    need(entries == {name: (value['mode'], value['git_blob'], value['bytes'])
                     for name, value in ledger.items()}, 'SOURCE_GIT_INVENTORY_CHANGED')
    files = set()
    directories = set()
    expected_dirs = {parent.as_posix() for name in ledger for parent in Path(name).parents if parent.as_posix() != '.'}
    for folder, dirs, names in os.walk(SOURCE, followlinks=False, onerror=lambda _: need(False, 'SOURCE_WALK_FAILED')):
        clock()
        parent = Path(folder)
        if parent == SOURCE:
            dirs[:] = [name for name in dirs if name != '.git']
            names = [name for name in names if name != '.git']
        for name in dirs:
            path = parent / name
            ordinary(path, directory=True)
            directories.add(path.relative_to(SOURCE).as_posix())
        for name in names:
            path = parent / name
            relative = path.relative_to(SOURCE).as_posix()
            need(relative in ledger, 'SOURCE_EXTRA_FILE')
            hash_file(path, ledger[relative], single=True)
            files.add(relative)
    need(files == set(ledger) and directories == expected_dirs, 'SOURCE_MISSING_OR_EXTRA')
    need(not git(('status', '--porcelain=v1', '--untracked-files=all'), phase + '-git-clean'), 'SOURCE_DIRTY')
    for name, digest in FROZEN.items():
        need(ledger[name]['sha256'] == digest, 'FROZEN_TEST_DOCUMENT_CHANGED')
    return {'files': len(files), 'head': HEAD, 'tree': TREE, 'raw_git_and_physical_match': True,
            'source_single_links': True, 'no_extras': True, 'helper_present_and_pinned': True}


exec(compile(ORIGIN_SOURCE, '<sealed-module-origin-admission>', 'exec'), globals())


def collect_runtime():
    root = Path(sys.base_prefix)
    ordinary(root, directory=True)
    need(root.is_absolute() and not root.is_relative_to(SOURCE)
         and REAL.is_relative_to(root) and sys.prefix == sys.base_prefix, 'FIXED_TOOL_CHANGED')
    entries, pending, count, total, directories = {}, [root], 0, 0, 0
    # Full selected setup-Python tree; exclude only site packages and bytecode.
    while pending:
        clock()
        folder = pending.pop()
        directories += 1
        need(directories <= 20000, 'RUNTIME_FILE_COUNT')
        ordinary(folder, directory=True)
        for path in folder.iterdir():
            clock()
            info = path.lstat()
            need(not stat.S_ISLNK(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & 1024, 'UNSAFE_PATH')
            info = ordinary(path, directory=stat.S_ISDIR(info.st_mode))
            if stat.S_ISDIR(info.st_mode):
                if path.name == '__pycache__' or path == root / 'Lib/site-packages':
                    continue
                pending.append(path)
            elif path.suffix.lower() not in ('.pyc', '.pyo'):
                count += 1
                need(count <= 20000, 'RUNTIME_FILE_COUNT')
                entry = hash_file(path, single=True)
                entries[str(path)] = entry
                total += entry['bytes']
                need(total <= 1024 ** 3, 'FILE_BOUND')
    return {'root': str(root), 'files': entries}


def runtime_snapshot(runtime):
    current = collect_runtime()
    need(current == runtime, 'FIXED_TOOL_CHANGED')
    tools = {}
    for name, path in (('python', REAL), ('git', GIT), ('powershell', PS)):
        need(path.is_absolute() and not path.is_relative_to(SOURCE), 'FIXED_TOOL_CHANGED')
        info = ordinary(path, single=name != 'powershell')
        need(info.st_nlink >= 1, 'FIXED_TOOL_CHANGED')
        entry = hash_file(path, single=name != 'powershell')
        tools[name] = dict(entry, path=str(path), nlink=info.st_nlink, mode=info.st_mode,
                           dev=info.st_dev, inode=info.st_ino, mtime_ns=info.st_mtime_ns,
                           ctime_ns=info.st_ctime_ns, attributes=getattr(info, 'st_file_attributes', 0))
    need(hash_file(DRIVER, single=True)['sha256'] == DRIVER_SHA, 'FIXED_TOOL_CHANGED')
    cache_empty()
    return {'bound_files': len(runtime['files']), 'root': runtime['root'], 'tools': tools,
            'runtime_map_sha256': hashlib.sha256(json.dumps(runtime, sort_keys=True).encode()).hexdigest(),
            'version': sys.version, 'empty_external_pycache_prefix': True,
            'excluded': ['Lib/site-packages', '**/__pycache__', '**/*.pyc', '**/*.pyo'],
            'transitive_os_dll_release_closure': 'NOT_PROVEN', 'publisher_attestation': False}

def classify_matrix(output, error, status):
    need(status == 0 and len(output) < 256, 'STOCK_MATRIX_PROFILE_REQUIRED')
    # Exactly one closed digest observation; the independently sealed driver
    # produces this profile. It is evidence consistency, never permission.
    match = re.fullmatch(rb'\{"profile_sha256":"([0-9a-f]{64})"\}\r?\n', output)
    need(match is not None, 'STOCK_MATRIX_PROFILE_REQUIRED')
    profile = pinned_json('allocated-matrix-evidence/matrix-profile.json', match[1].decode('ascii'))
    need(type(profile) is dict and set(profile) == {
        'schema', 'result', 'test_id', 'test_sha256', 'helper_sha256', 'powershell_sha256',
        'native_authority', 'raw_ps_output_independently_preserved', 'primary_failure_type',
        'attempts', 'child_retirement', 'actual_return_records', 'started_ids', 'succeeded_ids',
        'subcases', 'elapsed_seconds', 'module_origins_before', 'module_origins_after'}, 'STOCK_MATRIX_PROFILE_REQUIRED')
    need(profile['schema'] == 'stock-matrix-observation.v1'
         and profile['result'] == 'ONE_UNIT_24_STOCK_SUBCASES_PASS'
         and profile['test_id'] == TEST_ID and profile['primary_failure_type'] is None
         and profile['native_authority'] is False
         and profile['raw_ps_output_independently_preserved'] is False
         and profile['test_sha256'] == FROZEN['tests/test_native_output_cap_assertion.py']
         and profile['helper_sha256'] == FROZEN['tests/native_output_cap_assertion.ps1']
         and profile['powershell_sha256'] == PS_SHA, 'STOCK_MATRIX_PROFILE_REQUIRED')
    cases = ('accept_leaf', 'accept_aggregate_single', 'accept_aggregate_all_cap',
             'accept_method_aggregate', 'accept_target_method_aggregate', 'accept_max_depth',
             'accept_max_nodes', 'reject_null', 'reject_truthy_nonexception', 'reject_deadline',
             'reject_drain_deadline', 'reject_launch_failure', 'reject_unrelated', 'reject_wrong_case',
             'reject_cap_prefix', 'reject_unknown_wrapper', 'reject_nonleaf_cap',
             'reject_empty_aggregate', 'reject_mixed_aggregate', 'reject_nested_mixed',
             'reject_cycle', 'reject_depth', 'reject_nodes', 'reject_oversized_message')
    need(profile['started_ids'] == profile['succeeded_ids'] == [TEST_ID]
         and profile['subcases'] == [{'id': case, 'passed': True} for case in cases]
         and profile['actual_return_records'] == {
             case: 'TRUE' if case in cases[:7] else 'FALSE' for case in cases}, 'STOCK_MATRIX_PROFILE_REQUIRED')
    attempts, cleanup = profile['attempts'], profile['child_retirement']
    need(type(attempts) is list and type(cleanup) is list and len(attempts) == len(cleanup) == 1,
         'STOCK_MATRIX_PROFILE_REQUIRED')
    need(type(attempts[0]) is dict and set(attempts[0]) == {'returned_handle', 'pid'}
         and attempts[0]['returned_handle'] is True and type(attempts[0]['pid']) is int
         and attempts[0]['pid'] > 0, 'STOCK_MATRIX_PROFILE_REQUIRED')
    need(type(cleanup[0]) is dict and set(cleanup[0]) == {'pid', 'cleanup_needed', 'uncertain', 'returncode'}
         and cleanup[0]['pid'] == attempts[0]['pid'] and cleanup[0]['cleanup_needed'] is False
         and cleanup[0]['uncertain'] is False and type(cleanup[0]['returncode']) is int
         and cleanup[0]['returncode'] == 0, 'STOCK_MATRIX_PROFILE_REQUIRED')
    elapsed = profile['elapsed_seconds']
    need(type(elapsed) in (int, float) and 0 <= elapsed < 12, 'STOCK_MATRIX_PROFILE_REQUIRED')
    text = error.decode('utf8')
    need(TEST_ID in text and re.search(r'Ran 1 test in [0-9.]+s', text) is not None
         and text.rstrip().endswith('OK') and 'FAIL' not in text and 'ERROR:' not in text
         and 'skipped' not in text, 'STOCK_MATRIX_PROFILE_REQUIRED')
    for phase in ('module_origins_before', 'module_origins_after'):
        observation = profile[phase]
        need(type(observation) is dict and set(observation) == {'rows', 'row_count', 'cache_empty', 'claim'}
             and observation['cache_empty'] is True and type(observation['rows']) is list
             and type(observation['row_count']) is int and 0 < observation['row_count'] <= 512
             and observation['row_count'] == len(observation['rows']), 'MODULE_ORIGIN_DENY')
    RECORD['actual_stock_matrix_profile'] = profile
    RECORD['actual_classifier_subcases_run'] = 24

def main():
    global WHOLE_END, PS_SHA
    need(sys.argv[1:] == ['--allocated-stock-matrix-controller'], 'EXPLICIT_ROOT_ALLOCATION_REQUIRED')
    ordinary(BASE, directory=True)
    EVIDENCE.mkdir(exist_ok=False)  # consumed once; no overwrite or automatic repeat
    with (EVIDENCE / 'bootstrap.json').open('x', encoding='utf8') as stream:
        stream.write(json.dumps({'stage': 'ALLOCATED_CONTROLLER_ENTERED', 'result': 'DENY',
                                 'source_head': HEAD, 'actual_classifier_subcases_run': 0}) + '\n')
    started = time.monotonic()
    WHOLE_END = started + 120
    initial_threads = {thread.ident for thread in threading.enumerate()}
    before = False
    exit_code = 1
    try:
        need(os.name == 'nt' and sys.version_info[:3] == (3, 12, 10), 'FIXED_WINDOWS_CPYTHON_REQUIRED')
        executable = Path(sys.executable)
        need(executable.is_absolute() and str(executable) == str(REAL),
             'ISOLATED_RUNTIME_AND_FRESH_PREFIX_REQUIRED')
        ordinary(REAL)  # root-first; do not resolve/follow an executable alias
        need(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
             and sys.pycache_prefix is not None and Path(sys.pycache_prefix) == CACHE
             and executable == REAL,
             'ISOLATED_RUNTIME_AND_FRESH_PREFIX_REQUIRED')
        ledger = pinned_json('source-ledger.json', LEDGER_SHA)
        with DRIVER.open('xb') as stream:
            stream.write(CHILD_SOURCE.encode('utf8'))
        runtime = collect_runtime()
        runtime_raw = (json.dumps(runtime, sort_keys=True, indent=2) + '\n').encode('utf8')
        need(len(runtime_raw) <= 8 * 1024 * 1024, 'FILE_BOUND')
        with (BASE / 'runtime-ledger.json').open('xb') as stream:
            stream.write(runtime_raw)
        RECORD['runtime_ledger_sha256'] = hashlib.sha256(runtime_raw).hexdigest()
        RECORD['runtime_before'] = runtime_snapshot(runtime)
        PS_SHA = RECORD['runtime_before']['tools']['powershell']['sha256']
        RECORD['source_before'] = snapshot(ledger, 'pre')
        origin_roles = {'__main__': {'path': str(Path(__file__)), 'bytes': ordinary(Path(__file__)).st_size,
                                   'sha256': os.environ['QUALIFIER_SHA256']}}
        read_origin = lambda path, entry: hash_file(path, entry, single=True)
        RECORD['module_origins_before'] = module_origins(runtime, origin_roles, read_origin)
        before = True
        command = [str(REAL), '-I', '-S', '-B', '-X', 'pycache_prefix=' + str(CACHE),
                   str(DRIVER), '--allocated-stock-classifier-matrix']
        output, error, status = capture(command, 'actual_classifier_unit_python', 'stock-matrix-unit', 15)
        classify_matrix(output, error, status)
        RECORD['actual_stock_matrix_observed'] = True
    except BaseException as error:
        fact = failure_fact(error)
        RECORD['failure_type'] = fact['type']
        RECORD['failure_code'] = fact['code']
    finally:
        if before:
            try:
                RECORD['source_after'] = snapshot(ledger, 'post')
                RECORD['runtime_after'] = runtime_snapshot(runtime)
                need(RECORD['runtime_after'] == RECORD['runtime_before'], 'FIXED_TOOL_CHANGED')
                RECORD['module_origins_after'] = module_origins(runtime, origin_roles, read_origin)
            except BaseException as error:
                RECORD['post_verification_failed'] = True
                RECORD['post_verification_failure'] = failure_fact(error)
        RECORD['remaining_new_threads'] = sum(thread.is_alive() and thread.ident not in initial_threads
                                              for thread in threading.enumerate())
        RECORD['elapsed_seconds'] = time.monotonic() - started
        expected = [r for r in RECORD['process_roles'] if r['role'] == 'actual_classifier_unit_python']
        cleanup_ok = all(not r['denied'] and not r['cleanup_uncertain']
                         and r['reader_threads_retired'] and r['local_completion_within_bound']
                         for r in RECORD['process_roles'])
        RECORD['candidate_checks_passed'] = False
        if (RECORD.get('actual_stock_matrix_observed') and RECORD.get('source_after')
                and RECORD.get('runtime_after') and RECORD.get('module_origins_before')
                and RECORD.get('module_origins_after') and not RECORD.get('failure_type')
                and not RECORD.get('post_verification_failed') and cleanup_ok
                and not RECORD['remaining_new_threads'] and len(expected) == 1
                and len(RECORD['process_roles']) == 7
                and sum(r['role'] == 'source_git_inspection' for r in RECORD['process_roles']) == 6
                and RECORD['elapsed_seconds'] < 120):
            RECORD['candidate_checks_passed'] = True
        RECORD['observed_owned_powershell_children'] = 1 if RECORD.get('actual_stock_matrix_observed') else 'UNKNOWN'
        RECORD['scope'] = 'One Python unittest / 24 stock managed exception subcases and one owned PowerShell child; six separate source Git roles. No native C#Run, installation, service, family-hardwall or hostwide process qualification.'
        # Failure evidence must still be attempted after the whole qualification
        # deadline. Finite artifact reads do not resurrect a DENY result.
        RECORD['artifacts'] = {}
        for path in EVIDENCE.iterdir():
            if not path.is_file():
                continue
            try:
                need(path.stat().st_size <= CAP, 'EVIDENCE_FILE_BOUND')
                with path.open('rb') as stream:
                    raw = stream.read(CAP + 1)
                need(len(raw) <= CAP, 'EVIDENCE_FILE_BOUND')
                RECORD['artifacts'][path.name] = hashlib.sha256(raw).hexdigest()
            except BaseException:
                RECORD['result'] = 'DENY'
                RECORD['artifact_hash_failed'] = True
                exit_code = 1
        # Candidate facts are NOT terminal qualification. Artifact work is inside
        # the measured gate; a late/failed artifact phase is sticky DENY.
        try:
            observed = time.monotonic()
            within = (type(observed) in (int, float) and float('-inf') < observed < float('inf')
                      and started <= observed < WHOLE_END)
            RECORD['post_artifact_elapsed_seconds'] = observed - started if within else None
            RECORD['post_artifact_within_observed_bound'] = within
            candidate = (RECORD['candidate_checks_passed'] and within
                         and not RECORD.get('artifact_hash_failed'))
            RECORD['result'] = 'CANDIDATE_REQUIRES_EXTERNAL_VERIFICATION' if candidate else 'DENY'
            RECORD['terminal_publication_self_attested'] = False
            raw = (json.dumps(RECORD, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf8')
            need(len(raw) <= 2 * 1024 * 1024, 'EVIDENCE_FILE_BOUND')
            with (EVIDENCE / 'receipt.json').open('xb') as stream:
                stream.write(raw)
            digest = hashlib.sha256(raw).hexdigest()
            closed = pinned_json('allocated-matrix-evidence/receipt.json', digest)
            need(closed == RECORD, 'CLOSED_RECEIPT_REQUIRED')
            closed_at = time.monotonic()
            ready = candidate and started <= closed_at < WHOLE_END
            completion = {'schema': 'stock24-closed-candidate.v1',
                          'result': 'CLOSED_CANDIDATE_READBACK' if ready else 'DENY',
                          'receipt_sha256': digest, 'source_head': HEAD,
                          'controller_started_monotonic': started,
                          'elapsed_through_closed_readback': closed_at - started,
                          'terminal_publication_self_attested': False,
                          'requires_actual_successful_producer_exit_and_external_readback': True}
            completion_raw = (json.dumps(completion, sort_keys=True, allow_nan=False) + '\n').encode('utf8')
            with (EVIDENCE / 'completion.json').open('xb') as stream:
                stream.write(completion_raw)
            print(json.dumps({'result': completion['result'],
                              'completion_sha256': hashlib.sha256(completion_raw).hexdigest(),
                              'scope': 'CANDIDATE_NOT_TERMINAL_OR_HARDWALL_PROOF'}), flush=True)
            # This return is still not a self-proof of terminal publication:
            # the workflow separately requires actual step success and reads
            # the closed files. A late final write/print cannot return PASS.
            exit_code = 0 if ready and started <= time.monotonic() < WHOLE_END else 1
        except BaseException as error:
            exit_code = 1
            failure = {'result': 'DENY', 'phase': 'CLOSED_CANDIDATE_PUBLICATION',
                       'failure': failure_fact(error), 'source_head': HEAD}
            try:
                with (EVIDENCE / 'completion-failure.json').open('x', encoding='utf8') as stream:
                    stream.write(json.dumps(failure, sort_keys=True) + '\n')
            except BaseException:
                pass  # actual nonzero producer exit is mandatory; no silent PASS
            print(json.dumps(failure), flush=True)
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
