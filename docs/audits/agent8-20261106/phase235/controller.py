"""UNEXECUTED Root allocation proposal: one stock-exception unittest / 24 subcases only."""
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

BASE = Path('C:/Users/LS-5/.codex/native-output-cap-matrix-d69b699-20261111')
SOURCE = BASE / 'source'
CACHE = BASE / 'pycache-prefix'
EVIDENCE = BASE / 'allocated-matrix-evidence'
REAL = Path('C:/Users/LS-5/AppData/Local/Python/pythoncore-3.12-64/python.exe')
GIT = Path('C:/Program Files/Git/bin/git.exe')
HEAD = 'd69b699466fb8b15785e0a4e886cbf60c8c91dd3'
TREE = 'c1fef5f97d1ec475ddcc7d1be02a1d3cd69d8b9c'
PARENT = '756a6701421e804a116a50f997bc015643af341c'
LEDGER_SHA = 'd93374a6e732c48f9fc609a1cc411b6506c497a8a95d1da33913344aeca81ccd'
RUNTIME_SHA = '3625b1be9c8ac3309ba2c974ad35a6b62c7f53e07031a6b4bc3e75b86d4f0046'
REAL_SHA = '4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a'
GIT_SHA = '78211c7ed73988da93a6d8a33d47ec6187f464d7ea2a9a00c182bbd7a1ecf30f'
PS = Path('C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe')
PS_SHA = '60c9b29843624dd8af6b6a7b26147753be6aeef65098b9a503cc50850afe410f'
DRIVER = BASE / 'child-driver.py'
DRIVER_SHA = '720b8562bc0372c576e99b1ca5adf5c3dba308fe7d068ca646b2fd108b2fc6e2'
FROZEN = {
    'tests/native_output_cap_assertion.ps1': '71818734af4f3e1badebec43afb867f106bb4cd692c3a013ad8d4f36126a6b71',
    'tests/test_installation_service.py': '7f55993256b098d109ba895098dde18a49b6dc16f882cd99e1aafc0d5bdc8039',
    'tests/test_native_output_cap_assertion.py': 'b822f4ec0d89240c1733b546eef3b00967c524da653ad802830c68b2b5f5191e',
    'docs/ci/native-output-cap-assertion-review1.md': 'ed62abd890c1192a1162b0fedeeecfbecf002b350048d3d2c69ab53e106e4a28',
}
TEST = SOURCE / 'tests/test_native_output_cap_assertion.py'
HELPER = SOURCE / 'tests/native_output_cap_assertion.ps1'
TEST_ID = 'native_output_cap_assertion_controls.NativeOutputCapAssertionControls.test_actual_shared_classifier_stock_exception_matrix'
CAP = 256 * 1024
WHOLE_END = None
RECORD = {'schema': 'native-output-cap-stock-matrix.v1', 'result': 'DENY',
          'source_head': HEAD, 'source_tree': TREE, 'source_parent': PARENT,
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
FIXED_TOOL_CHANGED STOCK_MATRIX_PROFILE_REQUIRED EXPECTED_SINGLE_PREREQUISITE_RED_REQUIRED EXPECTED_ASSERTION_MISSING
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
    need(len(ledger) == 1873 and 'tests/native_output_cap_assertion.ps1' in ledger,
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


def runtime_snapshot(runtime):
    need(len(runtime['files']) == 841, 'RUNTIME_FILE_COUNT')
    for name, entry in runtime['files'].items():
        hash_file(Path(name), entry, single=True)
    need(hash_file(REAL, single=True)['sha256'] == REAL_SHA and hash_file(GIT, single=True)['sha256'] == GIT_SHA, 'FIXED_TOOL_CHANGED')
    # Only this exact System32 servicing role permits multiple ordinary hardlinks.
    need(ordinary(PS).st_nlink >= 1 and hash_file(PS)['sha256'] == PS_SHA, 'FIXED_TOOL_CHANGED')
    need(hash_file(DRIVER, single=True)['sha256'] == DRIVER_SHA, 'FIXED_TOOL_CHANGED')
    cache_empty()
    return {'bound_files': 841, 'real_python_sha256': REAL_SHA,
            'empty_external_pycache_prefix': True, 'transitive_os_dll_release_closure': 'NOT_PROVEN'}


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
        'subcases', 'elapsed_seconds'}, 'STOCK_MATRIX_PROFILE_REQUIRED')
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
    RECORD['actual_stock_matrix_profile'] = profile
    RECORD['actual_classifier_subcases_run'] = 24

def main():
    global WHOLE_END
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
        runtime = pinned_json('runtime-ledger.json', RUNTIME_SHA)
        RECORD['runtime_before'] = runtime_snapshot(runtime)
        RECORD['source_before'] = snapshot(ledger, 'pre')
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
        if (RECORD.get('actual_stock_matrix_observed') and RECORD.get('source_after')
                and RECORD.get('runtime_after') and not RECORD.get('failure_type')
                and not RECORD.get('post_verification_failed') and cleanup_ok
                and not RECORD['remaining_new_threads'] and len(expected) == 1
                and len(RECORD['process_roles']) == 7
                and sum(r['role'] == 'source_git_inspection' for r in RECORD['process_roles']) == 6
                and RECORD['elapsed_seconds'] < 120):
            RECORD['result'] = 'ONE_UNIT_24_STOCK_SUBCASES_QUALIFIED'
            exit_code = 0
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
        with (EVIDENCE / 'receipt.json').open('x', encoding='utf8') as stream:
            stream.write(json.dumps(RECORD, sort_keys=True, indent=2) + '\n')
        print(json.dumps({'result': RECORD['result'], 'actual_classifier_subcases_run': RECORD['actual_classifier_subcases_run'],
                          'expected_python_children': len(expected), 'scope': 'STOCK_EXCEPTION_UNIT_ONLY_NOT_NATIVE_FIXTURE'}), flush=True)
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
