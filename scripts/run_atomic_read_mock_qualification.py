"""Trusted reviewed-source MOCK10 only; never native qualification or hostile sandbox."""
import argparse
import base64
import csv
import hashlib
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import threading
import time

GRID_HEAD = 'fb177d14b1e6e399bd9b66ae7cb35d3838acbd81'
GRID_TREE = '2cba4b0a1ee7621ef213600d6334db8e9ac7dae1'
TEST_SHA = 'e9dfdc83b9dd10b0166bda588c0f2a328c0e1ff2142f9657565b3762d62360da'
ASSIGNMENT_SHA = '5b972b6d81eeaf6f2283584c5b0482552fa9bf0717a4379838900a72da791491'
EXPECTED_METHODS = (
    'test_mock_backend_cached_capture_is_historical_until_explicit_reobserve',
    'test_mock_backend_cancelled_snapshot_propagates_without_capture_or_retry',
    'test_mock_backend_context_loss_during_snapshot_prevents_capture',
    'test_mock_backend_existing_reobserve_guard_remains_required',
    'test_mock_backend_generation_or_principal_policy_interleaving_cannot_issue_mixed_capture',
    'test_mock_backend_open_session_retains_atomic_record_and_leader_fences',
    'test_mock_backend_policy_decoder_keeps_original_schema_target_scope_and_expiry_rejections',
    'test_mock_backend_same_authority_constructor_creates_no_native_call',
    'test_mock_backend_snapshot_inventory_acl_and_transport_fail_closed',
    'test_mock_backend_stable_read_uses_one_five_key_snapshot_and_preserves_order',
)
OUTPUT_LIMIT = 2 * 1024 * 1024
LOCKS = {
    'win32': 'requirements-windows.lock',
    'linux': 'requirements-linux.lock',
}


def inventory_ok(ids):
    expected = {'atomic_read_mock.ControlledBackendBrokerUnitTests.' + n for n in EXPECTED_METHODS}
    return len(ids) == len(set(ids)) == 10 and set(ids) == expected


def result_ok(*, ids, tests, skips, errors, failures, cleanup_ok, boundary_errors):
    return inventory_ok(ids) and tests == 10 and skips == errors == failures == boundary_errors == 0 and cleanup_ok is True


def require(value, reason):
    if not value:
        raise RuntimeError(reason)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def ordinary(path, *, runtime=False):
    path = Path(path).absolute()
    for p in (path, *path.parents):
        info = p.lstat()
        require(not stat.S_ISLNK(info.st_mode) and not getattr(info, 'st_reparse_tag', 0)
                and not getattr(info, 'st_file_attributes', 0) & 1024, 'LINK_OR_REPARSE')
    info = path.stat()
    require(path.is_file(), 'REGULAR_INPUT_REQUIRED')
    if not runtime:
        require(info.st_nlink == 1, 'SINGLE_LINK_REQUIRED')
    return info


def read_raw(path, *, expected_size=None, max_bytes=256 * 1024 * 1024, runtime=False):
    before = ordinary(path, runtime=runtime)
    size = before.st_size if expected_size is None else expected_size
    require(type(size) is int and 0 <= size <= max_bytes and before.st_size == size, 'INPUT_SIZE_BOUND')
    with Path(path).open('rb') as stream:
        opened = os.fstat(stream.fileno())
        require((opened.st_dev, opened.st_ino) == (before.st_dev, before.st_ino), 'OPENED_IDENTITY')
        raw = stream.read(size + 1)
        held = os.fstat(stream.fileno())
    after = ordinary(path, runtime=runtime)
    identity = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    require(len(raw) == size and all((v.st_dev, v.st_ino, v.st_size, v.st_mtime_ns) == identity for v in (opened, held, after)), 'INPUT_CHANGED')
    return raw


def file_fact(path, *, runtime=False, expected=None):
    raw = read_raw(path, runtime=runtime, expected_size=None if expected is None else expected['bytes'])
    fact = dict(bytes=len(raw), sha256=digest(raw))
    require(expected is None or fact == expected, 'RAW_HASH_CHANGED')
    return fact


def write_json(path, value, limit=8 * 1024 * 1024):
    raw = (json.dumps(value, sort_keys=True, indent=2) + '\n').encode('ascii')
    require(len(raw) <= limit, 'RECEIPT_LIMIT')
    with Path(path).open('xb') as stream:
        stream.write(raw)


def git(root, *args):
    return subprocess.check_output(['git', '--no-replace-objects', '--no-optional-locks',
                                   '-c', 'core.fsmonitor=false', '-C', str(root), *args], timeout=20)


def source(root, head):
    root = root.absolute()
    require(git(root, 'rev-parse', 'HEAD').decode().strip() == head, 'SOURCE_HEAD')
    require(not git(root, 'status', '--porcelain', '--untracked-files=all').strip(), 'SOURCE_DIRTY')
    facts = {}
    for entry in git(root, 'ls-tree', '-r', '-z', head).split(b'\0'):
        if not entry:
            continue
        meta, name = entry.split(b'\t', 1)
        mode, kind, blob = meta.split()
        require(mode in (b'100644', b'100755') and kind == b'blob', 'SOURCE_MODE')
        path = root / name.decode('utf-8')
        fact = file_fact(path)
        require(fact['sha256'] == digest(git(root, 'cat-file', 'blob', blob.decode())), 'SOURCE_RAW')
        facts[str(path)] = fact
    return dict(root=str(root), head=head, tree=git(root, 'rev-parse', head + '^{tree}').decode().strip(), files=facts)


def dependencies(root, lock):
    require(root.is_dir() and not root.is_symlink(), 'DEPS_ROOT')
    wanted = {}
    for line in read_raw(lock, max_bytes=1024 * 1024).decode().splitlines():
        if not line or line.startswith('#'):
            continue
        item = line.split()[0]
        name, version = item.split('==')
        wanted[re.sub('[-_.]+', '-', name).lower()] = version
    found = {}
    covered = set()
    facts = {}
    records = list(root.glob('*.dist-info/RECORD'))
    require(len(records) == len(wanted) == 15, 'EXACT_FIFTEEN_DISTRIBUTIONS')
    for record in records:
        metadata = read_raw(record.parent / 'METADATA', max_bytes=4 * 1024 * 1024).decode()
        name = re.search(r'^Name: (.+)$', metadata, re.M).group(1)
        version = re.search(r'^Version: (.+)$', metadata, re.M).group(1)
        key = re.sub('[-_.]+', '-', name).lower()
        require(key not in found and wanted.get(key) == version, 'DEPENDENCY_VERSION')
        found[key] = version
        for rel, encoded, size in csv.reader(read_raw(record, max_bytes=4 * 1024 * 1024).decode().splitlines()):
            part = Path(rel)
            require(not part.is_absolute(), 'RECORD_PATH')
            if '..' in part.parts:
                require(part.parts[:2] == ('..', '..') and len(part.parts) == 4 and part.parts[2] in ('bin', 'Scripts'), 'RECORD_SCRIPT_PATH')
                path = root / part.parts[2] / part.name
            else:
                path = root / part
            require(path.is_relative_to(root) and path.is_file(), 'RECORD_MISSING')
            fact = file_fact(path)
            if encoded:
                algorithm, expected = encoded.split('=', 1)
                actual = base64.urlsafe_b64encode(bytes.fromhex(fact['sha256'])).decode().rstrip('=')
                require(algorithm == 'sha256' and actual == expected and str(fact['bytes']) == size, 'RECORD_HASH_SIZE')
            else:
                require(path == record, 'UNHASHED_DEPENDENCY')
            covered.add(path)
            facts[str(path)] = fact
    require(found == wanted, 'DEPENDENCY_SET')
    actual = {p for p in root.rglob('*') if p.is_file()}
    require(actual == covered, 'EXTRA_DEPENDENCY_FILE')
    require(not any(p.suffix in ('.pth', '.pyc', '.pyo') or p.name in ('sitecustomize.py', 'usercustomize.py') for p in actual), 'STARTUP_OR_CACHE')
    return facts


def runtime_inventory():
    import sysconfig
    roots = {Path(sysconfig.get_path('stdlib')).absolute(), Path(sys.base_prefix).absolute() / 'DLLs'}
    facts = {str(Path(sys.executable).resolve()): file_fact(Path(sys.executable).resolve(), runtime=True)}
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob('*'):
            if 'site-packages' in path.parts or '__pycache__' in path.parts:
                continue
            if path.is_file() and path.suffix.lower() in ('.py', '.pyd', '.dll', '.so', '.zip'):
                facts[str(path.absolute())] = file_fact(path, runtime=True)
    return facts


def exact_owned_tree(root, files, *, git_metadata=False):
    expected = {name for name in files if Path(name).is_relative_to(root)}
    actual = set()
    for current, directories, names in os.walk(root, followlinks=False):
        for name in list(directories):
            path = Path(current) / name
            if git_metadata and Path(current) == root and name == '.git':
                directories.remove(name)
                continue
            info = path.lstat()
            require(not path.is_symlink() and not getattr(info, 'st_reparse_tag', 0), 'EXTRA_OR_LINK_DIRECTORY')
        for name in names:
            path = Path(current) / name
            if git_metadata and Path(current) == root and name == '.git':
                continue
            require(str(path) in expected, 'UNADMITTED_EXTRA_FILE')
            actual.add(str(path))
    require(actual == expected, 'EXACT_OWNED_TREE')


def check_all(files):
    for name, expected in files.items():
        require(file_fact(Path(name), runtime=True, expected=expected) == expected, 'ADMITTED_RAW_CHANGED')


def child(manifest_path, manifest_sha):
    require(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode, 'ISOLATED_CHILD')
    raw = read_raw(manifest_path, max_bytes=8 * 1024 * 1024)
    require(digest(raw) == manifest_sha and len(raw) <= 8 * 1024 * 1024, 'MANIFEST_BINDING')
    c = json.loads(raw)
    files = c['files']
    check_all(files)
    for key in ('unified', 'grid', 'deps'):
        exact_owned_tree(Path(c[key]), files, git_metadata=key != 'deps')
    require(file_fact(Path(__file__)) == c['helper'], 'HELPER_BINDING')
    cache = Path(c['cache'])
    require(sys.pycache_prefix == str(cache) and not any(cache.iterdir()), 'EMPTY_CACHE')
    sys.path[:] = [c['unified'], c['grid'], c['deps'], *c['stdlib_paths']]
    origins = {}
    def origin(name, path):
        if path in ('built-in', 'frozen'):
            return
        require(type(path) is str and str(Path(path).absolute()) in files, 'UNADMITTED_IMPORT_ORIGIN')
        absolute = str(Path(path).absolute())
        require(file_fact(Path(absolute), runtime=True, expected=files[absolute]) == files[absolute], 'IMPORT_RAW')
        origins[name] = absolute
    class Loader:
        def __init__(self, spec):
            self.spec = spec
            self.delegate = spec.loader
        def create_module(self, spec):
            origin(spec.name, spec.origin)
            return self.delegate.create_module(spec) if hasattr(self.delegate, 'create_module') else None
        def exec_module(self, module):
            origin(self.spec.name, self.spec.origin)
            if self.spec.origin.endswith('.py'):
                expected = files[str(Path(self.spec.origin).absolute())]
                raw = read_raw(Path(self.spec.origin), expected_size=expected['bytes'], runtime=True)
                require(digest(raw) == expected['sha256'], 'EXECUTED_SOURCE_HASH')
                exec(compile(raw, self.spec.origin, 'exec'), module.__dict__)
            else:
                self.delegate.exec_module(module)
        def __getattr__(self, name):
            return getattr(self.delegate, name)
    class Finder:
        def find_spec(self, name, path=None, target=None):
            spec = importlib.machinery.PathFinder.find_spec(name, path, target)
            if spec:
                require(spec.loader is not None, 'NAMESPACE_PACKAGE')
                origin(name, spec.origin)
                spec.loader = Loader(spec)
            return spec
    sys.meta_path[:] = [m for m in sys.meta_path if m is not importlib.machinery.PathFinder] + [Finder()]
    effects = {}
    owned_sockets = []
    def selfpipe(event, args):
        frame = sys._getframe(2)
        fallback = None
        pipe = False
        while frame:
            filename = str(Path(frame.f_code.co_filename).absolute())
            if filename in files:
                if Path(filename).name == 'socket.py' and frame.f_code.co_name == '_fallback_socketpair':
                    fallback = frame
                if '/asyncio/' in filename.replace('\\', '/') and frame.f_code.co_name == '_make_self_pipe':
                    pipe = True
            frame = frame.f_back
        if not (fallback and pipe):
            return False
        sock, address = args
        if event == 'socket.bind':
            return sock is fallback.f_locals.get('lsock') and address in (('127.0.0.1', 0), ('::1', 0))
        return (sock is fallback.f_locals.get('csock') and address == (fallback.f_locals.get('addr'), fallback.f_locals.get('port'))
                and address[0] in ('127.0.0.1', '::1') and type(address[1]) is int and 0 < address[1] < 65536)
    def audit(event, args):
        if event.startswith(('subprocess.', 'os.exec', 'os.spawn')) or event in ('os.system', 'os.fork', 'os.forkpty', 'ctypes.dlopen', 'ctypes.dlsym'):
            raise RuntimeError('CHILD_OR_DYNAMIC_LOADER_FORBIDDEN')
        if event.startswith(('socket.getaddrinfo', 'socket.gethostby', 'socket.getnameinfo')) or event == 'socket.sendto':
            raise RuntimeError('DNS_OR_DATAGRAM_FORBIDDEN')
        if event in ('socket.connect', 'socket.bind'):
            require(selfpipe(event, args), 'ONLY_ASYNCIO_SELFPIPE_PERMITTED')
            owned_sockets.append(args[0])
            effects[event] = effects.get(event, 0) + 1
    sys.addaudithook(audit)
    import asyncio
    import unittest
    loops = []
    baseline_threads = {id(t) for t in threading.enumerate()}
    original_loop = asyncio.events.new_event_loop
    def observed_loop():
        loop = original_loop()
        loops.append(loop)
        return loop
    asyncio.events.new_event_loop = observed_loop
    result = None
    ids = []
    boundary = []
    receipt = dict(state='MOCK_FAILED', native22='NOT_RUN', negative21='NOT_RUN', physical='NOT_RUN', native_grants=False)
    try:
        test = Path(c['unified']) / 'tests/test_research_identity_atomic_snapshot_unit.py'
        require(file_fact(test)['sha256'] == TEST_SHA, 'TEST_HASH')
        spec = importlib.util.spec_from_file_location('atomic_read_mock', test)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(module.ControlledBackendBrokerUnitTests)
        ids = [t.id() for t in suite]
        require(inventory_ok(ids), 'EXACT_TEN_REQUIRED')
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    except BaseException as error:
        boundary.append(type(error).__name__)
        print('MOCK_EXECUTION_OR_BOUNDARY_FAILURE', file=sys.stderr)
    finally:
        asyncio.events.new_event_loop = original_loop
        try:
            for name, mod in tuple(sys.modules.items()):
                spec = getattr(mod, '__spec__', None)
                if spec:
                    origin(name, spec.origin)
            check_all(files)
            for key in ('unified', 'grid', 'deps'):
                exact_owned_tree(Path(c[key]), files, git_metadata=key != 'deps')
        except BaseException as error:
            boundary.append(type(error).__name__)
        cleanup = dict(loops=len(loops), loops_closed=all(l.is_closed() for l in loops),
                       tasks_done=all(all(t.done() for t in asyncio.all_tasks(l)) for l in loops),
                       new_threads=sum(id(t) not in baseline_threads for t in threading.enumerate()),
                       selfpipe_closed=all(s.fileno() == -1 for s in owned_sockets), cache_empty=not any(cache.iterdir()))
        clean = cleanup['loops_closed'] and cleanup['tasks_done'] and cleanup['new_threads'] == 0 and cleanup['selfpipe_closed'] and cleanup['cache_empty']
        passed = result is not None and result_ok(ids=ids, tests=result.testsRun, skips=len(result.skipped), errors=len(result.errors),
                                                   failures=len(result.failures), cleanup_ok=bool(clean), boundary_errors=len(boundary))
        receipt.update(state='HOSTED_CONTROLLED_BACKEND_MOCK10_PASS' if passed else 'MOCK_FAILED', ids=ids,
                       tests=None if result is None else result.testsRun,
                       errors=None if result is None else len(result.errors), failures=None if result is None else len(result.failures),
                       skips=None if result is None else len(result.skipped), cleanup=cleanup, effects=effects,
                       boundary_errors=boundary, origins=origins, source_prepost_equal=not boundary,
                       limitations=['Trusted reviewed source only', 'No hostile DSO/process-family containment', 'No transitive DLL publisher closure'])
        write_json(Path(c['output']) / 'child-result.json', receipt)
    return 0 if passed else 1


def supervise(command, output):
    """90s child phase, then bounded retirement/readers; not whole-lane90s."""
    started = time.monotonic()
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
                               env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'},
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    total = 0
    lock = threading.Lock()
    exceeded = threading.Event()
    errors = []
    def reader(pipe, path):
        nonlocal total
        try:
            with path.open('xb') as stream:
                while True:
                    block = pipe.read(4096)
                    if not block:
                        break
                    with lock:
                        allowed = max(0, OUTPUT_LIMIT - total)
                        total += len(block)
                    stream.write(block[:allowed])
                    if total > OUTPUT_LIMIT:
                        exceeded.set()
        except BaseException as error:
            errors.append(type(error).__name__)
        finally:
            pipe.close()
    readers = [threading.Thread(target=reader, args=(pipe, output / name), daemon=True)
               for pipe, name in ((process.stdout, 'stdout.original.bin'), (process.stderr, 'stderr.original.bin'))]
    for thread in readers:
        thread.start()
    reason = None
    while process.poll() is None:
        if exceeded.is_set() or time.monotonic() - started > 90:
            reason = 'OUTPUT_LIMIT' if exceeded.is_set() else 'CHILD_TIMEOUT'
            process.kill()
            break
        time.sleep(.05)
    retired = True
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        retired = False
        reason = 'RETIREMENT_UNKNOWN'
    observed_completion = time.monotonic() - started
    if reason is None and observed_completion > 90:
        reason = 'COMPLETION_OBSERVED_AFTER_CHILD_BUDGET'
    for thread in readers:
        thread.join(timeout=1)
    readers_retired = all(not t.is_alive() for t in readers)
    ok = retired and readers_retired and not errors and reason is None and not exceeded.is_set() and process.returncode == 0
    write_json(output / 'outer-result.json', dict(scope='TRUSTED_MOCK_ONLY_NOT_HOSTILE_FAMILY', returncode=process.returncode,
               reason=reason, direct_child_retired=retired, readers_retired=readers_retired, reader_errors=errors,
               observed_output_bytes=total, completion_observed_seconds=observed_completion, total_observed_seconds=time.monotonic() - started, passed=ok))
    return ok


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--unified', type=Path)
    parser.add_argument('--grid', type=Path)
    parser.add_argument('--deps', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--expected-head')
    parser.add_argument('--child-manifest', type=Path)
    parser.add_argument('--manifest-sha')
    args = parser.parse_args(argv)
    if args.child_manifest is not None:
        return child(args.child_manifest, args.manifest_sha)
    require(all(v is not None for v in (args.unified, args.grid, args.deps, args.output, args.expected_head)), 'EXPLICIT_INPUTS')
    output = args.output.absolute()
    output.mkdir(exist_ok=False)
    status = dict(state='NOT_RUN', scope='CONTROLLED_BACKEND_MOCK10_ONLY', native22='NOT_RUN', negative21='NOT_RUN', physical='NOT_RUN')
    code = 1
    try:
        require(sys.version_info[:3] == (3, 12, 10) and sys.maxsize > 2**32 and sys.platform in LOCKS, 'RUNTIME_PROFILE')
        require(re.fullmatch('[0-9a-f]{40}', args.expected_head) is not None, 'EXACT_HEAD')
        unified = source(args.unified.absolute(), args.expected_head)
        grid = source(args.grid.absolute(), GRID_HEAD)
        require(grid['tree'] == GRID_TREE, 'GRID_TREE')
        require(unified['files'][str(args.unified.absolute() / 'tests/test_research_identity_atomic_snapshot_unit.py')]['sha256'] == TEST_SHA, 'TEST_HASH')
        require(grid['files'][str(args.grid.absolute() / 'grid/authority_assignment_v1.py')]['sha256'] == ASSIGNMENT_SHA, 'GRID_HELPER')
        lock = args.unified.absolute() / 'docs/intelligence/research-identity' / LOCKS[sys.platform]
        deps = dependencies(args.deps.absolute(), lock)
        runtime = runtime_inventory()
        files = {**unified['files'], **grid['files'], **deps, **runtime}
        cache = output / 'cache'
        cache.mkdir()
        stdpaths = [p for p in sys.path if p and Path(p).is_absolute() and
                    not any(part in ('site-packages', 'dist-packages') for part in Path(p).parts) and
                    (str(Path(p).absolute()).startswith(str(Path(sys.base_prefix).absolute()) + os.sep))]
        require(stdpaths, 'STDLIB_PATHS')
        capsule = dict(unified=unified['root'], grid=grid['root'], deps=str(args.deps.absolute()), output=str(output),
                       cache=str(cache), stdlib_paths=stdpaths, files=files, helper=file_fact(Path(__file__)),
                       heads=dict(unified=unified['head'], tree=unified['tree'], grid=GRID_HEAD, grid_tree=GRID_TREE),
                       runtime=dict(executable=sys.executable, version=sys.version, platform=sys.platform),
                       lock=file_fact(lock), setup_scope='Checkout and hashlocked installation are separate CI effects')
        write_json(output / 'capsule.json', capsule)
        command = [sys.executable, '-I', '-S', '-B', '-X', 'pycache_prefix=' + str(cache), str(Path(__file__).absolute()),
                   '--child-manifest', str(output / 'capsule.json'), '--manifest-sha', digest(read_raw(output / 'capsule.json', max_bytes=8 * 1024 * 1024))]
        status['state'] = 'EXECUTION_FAILED'
        ok = supervise(command, output)
        check_all(files)
        result_path = output / 'child-result.json'
        require(result_path.is_file() and result_path.stat().st_size <= 8 * 1024 * 1024, 'CHILD_RECEIPT')
        result = json.loads(read_raw(result_path, max_bytes=8 * 1024 * 1024))
        ok = ok and result.get('state') == 'HOSTED_CONTROLLED_BACKEND_MOCK10_PASS'
        status.update(state='HOSTED_CONTROLLED_BACKEND_MOCK10_PASS' if ok else 'FAILED', heads=capsule['heads'],
                      tests=result.get('tests'), test_sha=TEST_SHA, source_prepost_equal=True, platform=sys.platform)
        code = 0 if ok else 1
    except BaseException as error:
        status['failure_type'] = type(error).__name__
        print('MOCK_PREREQUISITE_OR_EXECUTION_FAILURE', file=sys.stderr)
    finally:
        write_json(output / 'status.json', status)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
