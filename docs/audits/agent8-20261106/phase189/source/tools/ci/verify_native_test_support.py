"""Bounded, read-only SOURCE DATA verification. Never a fixture permit or loader."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import queue
import re
import signal
import stat
import subprocess
import sys
import threading
import time


ERROR_CODES = frozenset({'UNKNOWN_SCHEMA','GRAPH_SHA_MISMATCH','INVALID_DESCRIPTOR','INVALID_PATH',
    'UNSAFE_FILE','INVENTORY_SHA_MISMATCH','WRONG_HEAD','WRONG_TREE','RAW_MISMATCH','EXTRA_SOURCE_FILE',
    'MISSING_HISTORICAL_OBJECT','ORIGIN_CONFLICT','GIT_VERIFICATION_FAILED'})
_ROLES = ('grid', 'unified_native_support')
_JSON_LIMIT = 2 * 1024 * 1024
_BLOB_LIMIT = 20 * 1024 * 1024
_PRIMARY_LIMIT = 64 * 1024 * 1024
_STDOUT_LIMIT = 72 * 1024 * 1024
_STDERR_LIMIT = 1024 * 1024
_GIT_EXE = Path('C:/Program Files/Git/cmd/git.exe' if os.name == 'nt' else '/usr/bin/git')
_PLATFORM = os.name
_SYSTEM = sys.platform


class NativeSupportVerificationError(ValueError):
    def __init__(self, code):
        self.code = code if code in ERROR_CODES else 'INVALID_DESCRIPTOR'
        super().__init__(self.code)


def _fail(code):
    raise NativeSupportVerificationError(code)


def _need(condition, code='INVALID_DESCRIPTOR'):
    if not condition:
        _fail(code)


class _Budget:
    def __init__(self):
        self.start = time.monotonic()
        self.end = self.start + 90
        self.used = {'stdout': 0, 'stderr': 0}
        self.lock = threading.Lock()

    def check(self):
        now = time.monotonic()
        _need(self.start <= now < self.end, 'GIT_VERIFICATION_FAILED')
        return self.end - now

    def take(self, stream, count):
        with self.lock:
            self.check()
            limit = _STDOUT_LIMIT if stream == 'stdout' else _STDERR_LIMIT
            _need(type(count) is int and 0 <= count <= limit - self.used[stream], 'GIT_VERIFICATION_FAILED')
            self.used[stream] += count


def _ordinary(path, *, directory=None):
    try:
        for part in (path, *path.parents):
            info = part.lstat()
            _need(not stat.S_ISLNK(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & 1024, 'UNSAFE_FILE')
        info = path.lstat()
        if directory is True:
            _need(stat.S_ISDIR(info.st_mode), 'UNSAFE_FILE')
        elif directory is False:
            _need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, 'UNSAFE_FILE')
        return info
    except NativeSupportVerificationError:
        raise
    except (OSError, ValueError):
        _fail('UNSAFE_FILE')


def _canonical(value, *, directory):
    _need(isinstance(value, Path) and value.is_absolute(), 'INVALID_PATH')
    _need(not str(value).startswith(('\\\\','//')), 'INVALID_PATH')
    _need(len(str(value).encode('utf-8')) <= 4096 and len(value.parts) <= 128, 'INVALID_PATH')
    try:
        _ordinary(value, directory=directory)
        _need(str(value) == str(value.resolve(strict=True)), 'INVALID_PATH')
    except (OSError, RuntimeError):
        _fail('INVALID_PATH')
    return value


def _rel(value):
    _need(type(value) is str and 0 < len(value.encode('utf-8')) <= 512, 'INVALID_PATH')
    _need(not value.startswith('/') and '\\' not in value and ':' not in value and not any(ord(c) < 32 or ord(c) == 127 for c in value), 'INVALID_PATH')
    parts = value.split('/')
    for part in parts:
        _need(part not in ('', '.', '..', '.git') and not part.endswith((' ', '.')), 'INVALID_PATH')
        _need(not re.fullmatch(r'(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?', part, re.I), 'INVALID_PATH')
    _need(PurePosixPath(value).as_posix() == value, 'INVALID_PATH')
    return value


def _hex(value, size):
    return type(value) is str and re.fullmatch('[0-9a-f]{' + str(size) + '}', value) is not None


def _keys(value, expected):
    _need(type(value) is dict and set(value) == set(expected))


def _integer(value, maximum):
    return type(value) is int and 0 <= value <= maximum


def _read(path, limit, budget):
    before = _ordinary(path, directory=False)
    _need(before.st_size <= limit, 'INVALID_DESCRIPTOR')
    flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
    try:
        with os.fdopen(os.open(path, flags), 'rb', buffering=0) as source:
            opened = os.fstat(source.fileno())
            _need((opened.st_dev, opened.st_ino, opened.st_size) == (before.st_dev, before.st_ino, before.st_size), 'UNSAFE_FILE')
            chunks = []
            count = 0
            while count < opened.st_size:
                budget.check()
                data = source.read(min(65536, opened.st_size - count))
                _need(bool(data), 'RAW_MISMATCH')
                chunks.append(data)
                count += len(data)
            _need(source.read(1) == b'', 'RAW_MISMATCH')
            after = os.fstat(source.fileno())
        current = path.lstat()
        _need((after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) ==
              (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) and
              (current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns) ==
              (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns), 'RAW_MISMATCH')
        return b''.join(chunks)
    except NativeSupportVerificationError:
        raise
    except OSError:
        _fail('UNSAFE_FILE')


def _json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            _need(key not in result)
            result[key] = value
        return result
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                          parse_constant=lambda _: _fail('INVALID_DESCRIPTOR'))
    except NativeSupportVerificationError:
        raise
    except (ValueError, UnicodeError, RecursionError):
        _fail('INVALID_DESCRIPTOR')


def _metadata(root, budget):
    """Allow ordinary linked-worktree administration, never object redirection."""
    marker = root / '.git'
    _ordinary(marker)
    if marker.is_file():
        raw = _read(marker, 4096, budget)
        _need(raw.startswith(b'gitdir: ') and raw.count(b'\n') <= 1, 'GIT_VERIFICATION_FAILED')
        try:
            gitdir = Path(raw[8:].decode('utf-8').strip())
        except UnicodeError:
            _fail('GIT_VERIFICATION_FAILED')
        _canonical(gitdir, directory=True)
    else:
        gitdir = marker
        _ordinary(gitdir, directory=True)
    common = gitdir
    if (gitdir / 'commondir').exists():
        try:
            joined = gitdir / _read(gitdir / 'commondir', 4096, budget).decode('utf-8').strip()
            _need(not str(joined).startswith(('\\\\','//')), 'INVALID_PATH')
            # Check lexical ancestors before resolve can erase a symlink/reparse alias.
            # Ordinary ../.. linked-worktree administration remains supported.
            _ordinary(joined, directory=True)
            common = joined.resolve(strict=True)
        except (OSError, UnicodeError):
            _fail('GIT_VERIFICATION_FAILED')
        _canonical(common, directory=True)
    objects = common / 'objects'
    _ordinary(objects, directory=True)
    for base in {gitdir, common}:
        for forbidden in ('objects/info/alternates', 'objects/info/http-alternates', 'info/grafts', 'refs/replace'):
            _need(not (base / forbidden).exists() and not (base / forbidden).is_symlink(), 'GIT_VERIFICATION_FAILED')
        for filename in ('config', 'config.worktree'):
            path = base / filename
            if path.exists():
                config = _read(path, _JSON_LIMIT, budget)
                _need(not re.search(rb'(?im)^\s*\[include(?:if)?(?:\s|\])|^\s*(?:partialclone|alternaterefscommand)\s*=', config), 'GIT_VERIFICATION_FAILED')
        packed = base / 'packed-refs'
        if packed.exists():
            _need(b' refs/replace/' not in _read(packed, _JSON_LIMIT, budget), 'GIT_VERIFICATION_FAILED')
    count = 0
    for folder, dirs, files in os.walk(objects,followlinks=False):
        budget.check()
        for name in dirs + files:
            count += 1
            _need(count <= 100000 and not name.endswith('.promisor'), 'GIT_VERIFICATION_FAILED')
            _ordinary(Path(folder)/name,directory=name in dirs)
    return gitdir


def _git_environment():
    environment = {'GIT_CONFIG_NOSYSTEM':'1', 'GIT_CONFIG_SYSTEM':os.devnull, 'GIT_CONFIG_GLOBAL':os.devnull,
        'GIT_NO_REPLACE_OBJECTS':'1', 'GIT_NO_LAZY_FETCH':'1', 'GIT_TERMINAL_PROMPT':'0',
        'GIT_OPTIONAL_LOCKS':'0', 'GIT_CONFIG_COUNT':'0', 'LC_ALL':'C', 'LANG':'C'}
    if os.name == 'nt':
        environment.update(SYSTEMROOT='C:/Windows', WINDIR='C:/Windows')
    return environment


def _qualify_git_custody():
    # WINDOWS_GIT_FAMILY_CONTAINMENT_UNQUALIFIED. No Job/native API or shim fallback.
    _need(_PLATFORM == 'posix' and _SYSTEM == 'linux', 'GIT_VERIFICATION_FAILED')
    _need(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode and sys.pycache_prefix is None,
          'GIT_VERIFICATION_FAILED')
    _need(threading.current_thread() is threading.main_thread() and
          threading.enumerate() == [threading.main_thread()], 'GIT_VERIFICATION_FAILED')
    _need(all(callable(getattr(os,name,None)) for name in ('getpgid','getsid','killpg','waitid')) and
          all(hasattr(os,name) for name in ('P_PID','WNOWAIT','WNOHANG','WEXITED')) and
          hasattr(signal,'SIGCHLD') and hasattr(signal,'SIGKILL') and signal.getsignal(signal.SIGCHLD) == signal.SIG_DFL,
          'GIT_VERIFICATION_FAILED')


class _Git:
    def __init__(self, root, budget):
        _qualify_git_custody()
        self.root = root
        self.budget = budget
        self.gitdir = _metadata(root, budget)
        _canonical(_GIT_EXE, directory=False)

    def call(self, args, *, data=None, cap=None):
        _qualify_git_custody()
        allowed = args in (('rev-parse','HEAD'), ('rev-parse','HEAD^{tree}'), ('cat-file','--batch'))
        allowed = allowed or len(args) == 4 and args[:3] == ('ls-tree','-rz','--full-tree') and _hex(args[3],40)
        _need(allowed, 'GIT_VERIFICATION_FAILED')
        _need(data is None or args == ('cat-file','--batch') and type(data) is bytes and len(data) <= 4096*41 and
              re.fullmatch(rb'(?:[0-9a-f]{40}\n){1,4096}',data) is not None, 'GIT_VERIFICATION_FAILED')
        cap = _STDOUT_LIMIT if cap is None else cap
        _need(_integer(cap, _STDOUT_LIMIT), 'GIT_VERIFICATION_FAILED')
        remaining = self.budget.check()
        _need(remaining > 1, 'GIT_VERIFICATION_FAILED')
        command_end = min(time.monotonic() + 30, self.budget.end)
        deadline = command_end - 1  # retain cleanup time inside both bounds
        command = [str(_GIT_EXE),'--no-replace-objects','--no-optional-locks','--git-dir',str(self.gitdir),
            '--work-tree',str(self.root),'-c','core.fsmonitor=false','-c','core.hooksPath=',
            '-c','core.pager=cat','-c','protocol.allow=never','-c','core.useReplaceRefs=false', *args]
        process = None
        threads = []
        stopped = threading.Event()
        failed = threading.Event()
        events = queue.Queue(maxsize=8)
        out = []
        total = [0]
        pid = None
        return_code = None

        def unreaped_exit():
            # WNOWAIT preserves the leader PID: never poll()/reap before group retirement.
            value = os.waitid(os.P_PID,pid,os.WEXITED | os.WNOHANG | os.WNOWAIT)
            _need(value is None or value.si_pid == pid, 'GIT_VERIFICATION_FAILED')
            return value is not None

        def own_group():
            unreaped_exit()  # also proves this is still our waitable child
            _need(os.getpgid(pid) == pid and os.getsid(pid) == pid, 'GIT_VERIFICATION_FAILED')

        def send(value):
            while not stopped.is_set():
                try:
                    events.put(value, timeout=.025)
                    return
                except queue.Full:
                    continue

        def drain(stream, label):
            buffer = bytearray(65536)
            try:
                while not stopped.is_set():
                    count = stream.readinto(buffer)
                    if not count:
                        break
                    self.budget.take(label, count)  # reserve BEFORE copying or retaining bytes
                    if label == 'stdout':
                        _need(count <= cap - total[0], 'GIT_VERIFICATION_FAILED')
                        total[0] += count
                        send(('data', bytes(memoryview(buffer)[:count])))
                send(('done', label))
            except BaseException:
                failed.set()

        try:
            process = subprocess.Popen(command, cwd=self.root, env=_git_environment(), shell=False,
                stdin=subprocess.PIPE if data is not None else subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0, close_fds=True,
                start_new_session=True)
            pid = process.pid
            _need(type(pid) is int and 1 < pid < 2**31, 'GIT_VERIFICATION_FAILED')
            own_group()
            for stream, label in ((process.stdout,'stdout'), (process.stderr,'stderr')):
                thread = threading.Thread(target=drain,args=(stream,label),daemon=True)
                threads.append(thread)
                thread.start()
            if data is not None:
                # Bounded request is small, but writing still has its own watchdog thread.
                def write():
                    try:
                        view = memoryview(data)
                        while view and not stopped.is_set():
                            count = process.stdin.write(view)
                            _need(type(count) is int and count > 0, 'GIT_VERIFICATION_FAILED')
                            view = view[count:]
                        process.stdin.close()
                    except BaseException:
                        failed.set()
                writer = threading.Thread(target=write,daemon=True)
                threads.append(writer)
                writer.start()
            done = 0
            while done != 2 or not unreaped_exit():
                self.budget.check()
                _need(not failed.is_set() and time.monotonic() < deadline, 'GIT_VERIFICATION_FAILED')
                try:
                    kind, value = events.get(timeout=min(.025,max(.001,deadline-time.monotonic())))
                except queue.Empty:
                    continue
                if kind == 'data':
                    out.append(value)
                else:
                    done += 1
            _need(not failed.is_set(), 'GIT_VERIFICATION_FAILED')
        except NativeSupportVerificationError:
            raise
        except BaseException:
            _fail('GIT_VERIFICATION_FAILED')
        finally:
            stopped.set()
            cleanup_ok = True
            if process is not None:
                try:
                    own_group()
                    # Retire the new session's owned group even on normal completion.
                    # The unreaped leader reserves PGID. Never signal by PGID after wait().
                    os.killpg(pid,signal.SIGKILL)
                    while not unreaped_exit():
                        _need(time.monotonic() < command_end, 'GIT_VERIFICATION_FAILED')
                        stopped.wait(.002)
                except BaseException:
                    cleanup_ok = False
                for stream in (process.stdin,process.stdout,process.stderr):
                    if stream is not None:
                        try:
                            stream.close()
                        except BaseException:
                            cleanup_ok = False
            for thread in threads:
                thread.join(timeout=max(0,min(.1,command_end-time.monotonic())))
                cleanup_ok = cleanup_ok and not thread.is_alive()
            if process is not None and cleanup_ok:
                try:
                    _need(time.monotonic() < command_end, 'GIT_VERIFICATION_FAILED')
                    return_code = process.wait(timeout=max(.001,min(.1,command_end-time.monotonic())))
                    _need(type(return_code) is int,'GIT_VERIFICATION_FAILED')
                except BaseException:
                    cleanup_ok = False
            _need(cleanup_ok, 'GIT_VERIFICATION_FAILED')
        _need(return_code == 0,'GIT_VERIFICATION_FAILED')
        return b''.join(out)


def _meta(value):
    _keys(value, ('bytes','git_blob','mode','sha256'))
    _need(_integer(value['bytes'],_BLOB_LIMIT) and _hex(value['git_blob'],40) and
          value['mode'] in ('100644','100755') and _hex(value['sha256'],64))


def _tree_id(entries):
    folders = {}
    for path, entry in entries.items():
        node = folders
        parts = path.split('/')
        for part in parts[:-1]:
            _need(part not in node or type(node[part]) is dict, 'ORIGIN_CONFLICT')
            node = node.setdefault(part,{})
        _need(parts[-1] not in node, 'ORIGIN_CONFLICT')
        node[parts[-1]] = (entry['mode'],entry['git_blob'])
    def tree(node):
        raw = bytearray()
        for name, value in sorted(node.items(),key=lambda x:(x[0]+('/' if type(x[1]) is dict else '')).encode('utf-8')):
            mode, value_oid = ('40000',tree(value)) if type(value) is dict else value
            raw.extend(mode.encode()+b' '+name.encode('utf-8')+b'\0'+bytes.fromhex(value_oid))
        return hashlib.sha1(b'tree '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    return tree(folders)


def _objects(git, requests, code='GIT_VERIFICATION_FAILED'):
    _need(0 < len(requests) <= 4096)
    cap = sum(size+128 for _,_,size in requests)
    raw = git.call(('cat-file','--batch'),data=b''.join(value.encode()+b'\n' for value,_,_ in requests),cap=cap)
    cursor = 0
    result = {}
    for value, kind, maximum in requests:
        end = raw.find(b'\n',cursor,cursor+128)
        _need(end >= 0, code)
        header = raw[cursor:end].split()
        _need(len(header) == 3 and header[:2] == [value.encode(),kind.encode()] and
              re.fullmatch(rb'[0-9]{1,8}',header[2]) is not None, code)
        size = int(header[2])
        _need(size <= maximum <= _BLOB_LIMIT, code)
        start = end+1
        _need(start+size < len(raw) and raw[start+size:start+size+1] == b'\n', code)
        blob = raw[start:start+size]
        _need(hashlib.sha1(kind.encode()+b' '+str(size).encode()+b'\0'+blob).hexdigest() == value, code)
        result[value] = blob
        cursor = start+size+1
    _need(cursor == len(raw), code)
    return result


def _commit_listing(git, head, expected_tree, code):
    commit = _objects(git,[(head,'commit',65536)],code)[head]
    first = commit.split(b'\n',1)[0]
    _need(first == b'tree '+expected_tree.encode(), code)
    raw = git.call(('ls-tree','-rz','--full-tree',head),cap=4*1024*1024)
    result = {}
    seen = set()
    for item in raw.split(b'\0'):
        if not item:
            continue
        try:
            meta, name = item.split(b'\t',1)
            mode, kind, value_oid = meta.split()
            path = _rel(name.decode('utf-8'))
            entry = dict(mode=mode.decode(),git_blob=value_oid.decode())
        except (ValueError, UnicodeError):
            _fail(code)
        _need(kind == b'blob' and entry['mode'] in ('100644','100755') and _hex(entry['git_blob'],40), code)
        _need(path.casefold() not in seen, 'ORIGIN_CONFLICT')
        seen.add(path.casefold())
        result[path] = entry
        _need(len(result) <= 4096, code)
    _need(raw.endswith(b'\0') or not raw, code)
    _need(_tree_id(result) == expected_tree, code)
    return result


def _inventory(path, source, budget):
    raw = _read(path,_JSON_LIMIT,budget)
    _need(hashlib.sha256(raw).hexdigest() == source['inventory_sha256'],'INVENTORY_SHA_MISMATCH')
    inv = _json(raw)
    _keys(inv,('files','head','tracked_blobs','tree'))
    _need(inv['head'] == source['head'] and inv['tree'] == source['tree'] and
          type(inv['files']) is dict and type(inv['tracked_blobs']) is int and
          0 < len(inv['files']) == inv['tracked_blobs'] == source['tracked_blobs'] <= 4096)
    seen = set()
    for path, entry in inv['files'].items():
        _rel(path)
        _need(path.casefold() not in seen, 'ORIGIN_CONFLICT')
        seen.add(path.casefold())
        _meta(entry)
    _need(_tree_id(inv['files']) == source['tree'], 'WRONG_TREE')
    return inv


def _working(root, files, budget):
    expected_dirs = {str(PurePosixPath(path).parent) for path in files}
    expected_dirs |= {str(parent) for path in files for parent in PurePosixPath(path).parents}
    found = set()
    for directory, dirs, names in os.walk(root,followlinks=False):
        budget.check()
        current = Path(directory)
        if current == root:
            dirs[:] = [name for name in dirs if name != '.git']
            names = [name for name in names if name != '.git']
        for name in dirs:
            path = current/name
            _ordinary(path,directory=True)
            relative = path.relative_to(root).as_posix()
            _need(relative in expected_dirs and name not in ('__pycache__','.pytest_cache'),'EXTRA_SOURCE_FILE')
        for name in names:
            path = current/name
            relative = path.relative_to(root).as_posix()
            info = _ordinary(path,directory=False)
            _need(relative in files and path.suffix not in ('.pyc','.pyo'),'EXTRA_SOURCE_FILE')
            _need(info.st_size == files[relative]['bytes'],'RAW_MISMATCH')
            data = _read(path,files[relative]['bytes'],budget)
            _need(len(data) == files[relative]['bytes'] and hashlib.sha256(data).hexdigest() == files[relative]['sha256'],'RAW_MISMATCH')
            found.add(relative)
    _need(found == set(files),'RAW_MISMATCH')


def _verify(graph_path, expected_graph_sha256, source_roots, budget):
    _canonical(graph_path,directory=False)
    _need(_hex(expected_graph_sha256,64))
    raw = _read(graph_path,_JSON_LIMIT,budget)
    _need(hashlib.sha256(raw).hexdigest() == expected_graph_sha256,'GRAPH_SHA_MISMATCH')
    graph = _json(raw)
    _need(type(graph) is dict)
    _need(graph.get('schema') == 'grid.native-test-support-source-graph.v1-proposed','UNKNOWN_SCHEMA')
    fixed = {
        'scope':'ELIGIBLE_FOR_PURE_SOURCE_VERIFICATION_ONLY_NOT_HA_RUNTIME_OR_FIXTURE_IMPORT',
        'actual_native_positive_api':'NONE','strict_time':'OPTION1_LOGICAL_MUTATIONS_DISABLED',
        'legacy_unified_source':'e0c2ea20aa4f1bd9476d1046e7e4b41f1b12d8e9_RETAINED_FOR_EXISTING_GROUP_PENDING_ROOT_OWNED_COMPATIBILITY_NO_GLOBAL_REPLACEMENT',
        'whole336file_generic_suite_compatibility':'NOT_PROVEN',
        'complete_platform_python_dependency_wheel_closure':'PENDING_OWNER_LOCK_INCLUDES_EXISTING_RUNTIME_PLUS_PYTEST_SUPPORT_NO_UNPINNED_FALLBACK',
        'consul_artifact_provenance':'PENDING_APPROVED_ARCHIVE_URL_MEMBER_ARCHIVE_SHA_SIZE_PLATFORM_AND_LEAF_CHAIN; NO_DOWNLOAD'}
    _keys(graph, {'schema','sources','module_origins_for_named_native_group_only','historical_objects',
        'existing_support_locks_reference_only','known_consul_leaf_sha256_reference_only','artifact_closure',
        'fixture_import_allowed','native_fixture_authorization','source_runtime_adoption', *fixed})
    for key, value in fixed.items():
        _need(graph[key] == value)
    for key in ('fixture_import_allowed','native_fixture_authorization','source_runtime_adoption'):
        _need(graph[key] is False)
    closure = {'status':'INCOMPLETE_SOURCE_DATA_ONLY','fixture_import_allowed':False,
        'binary_archive_publisher_closure':'NONE_APPROVED_IN_THIS_GRAPH',
        'dependency_archive_and_install_closure':'NONE_APPROVED_FOR_BROAD_MATRIX'}
    _need(graph['artifact_closure'] == closure)
    _keys(graph['known_consul_leaf_sha256_reference_only'],('linux','windows'))
    _need(all(_hex(x,64) for x in graph['known_consul_leaf_sha256_reference_only'].values()))
    _keys(graph['sources'],_ROLES)
    _need(type(source_roots) is dict and set(source_roots) == set(_ROLES),'INVALID_PATH')
    roots = {role:_canonical(source_roots[role],directory=True) for role in _ROLES}
    _need(roots['grid'] != roots['unified_native_support'] and
          not any(roots[a] in roots[b].parents for a,b in (('grid','unified_native_support'),('unified_native_support','grid'))),'ORIGIN_CONFLICT')
    inventories = {}
    for role in _ROLES:
        source = graph['sources'][role]
        _keys(source,('head','tree','repository','tracked_blobs','inventory','inventory_sha256'))
        _need(_hex(source['head'],40) and _hex(source['tree'],40) and _hex(source['inventory_sha256'],64) and
              type(source['tracked_blobs']) is int and 0 < source['tracked_blobs'] <= 4096)
        _need(source['repository'] == ('YehorBabenko88/bybit-cluster-grid' if role == 'grid' else 'YehorBabenko88/unified-system'))
        inventories[role] = _inventory(graph_path.parent/_rel(source['inventory']),source,budget)
    _need(sum(meta['bytes'] for inv in inventories.values() for meta in inv['files'].values()) <= _PRIMARY_LIMIT)
    origins = graph['module_origins_for_named_native_group_only']
    _need(type(origins) is dict and 0 < len(origins) <= 128)
    seen_names = set()
    seen_paths = set()
    for module, entry in origins.items():
        _need(type(module) is str and len(module) <= 128 and re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*(?:\.[A-Za-z_][A-Za-z_0-9]*)*',module),'ORIGIN_CONFLICT')
        _keys(entry,('bytes','git_blob','mode','sha256','role','path'))
        role = entry['role']
        _need(role in _ROLES and role == ('grid' if module.startswith('grid.') or module == 'native_snapshot_consul_lab' else 'unified_native_support'),'ORIGIN_CONFLICT')
        path = _rel(entry['path'])
        _need(module.casefold() not in seen_names and (role,path.casefold()) not in seen_paths,'ORIGIN_CONFLICT')
        seen_names.add(module.casefold())
        seen_paths.add((role,path.casefold()))
        _need({k:entry[k] for k in ('bytes','git_blob','mode','sha256')} == inventories[role]['files'].get(path),'ORIGIN_CONFLICT')
    locks = graph['existing_support_locks_reference_only']
    _need(type(locks) is dict and len(locks) <= 16)
    for path, entry in locks.items():
        _rel(path)
        _meta(entry)
        _need(entry == inventories['unified_native_support']['files'].get(path),'ORIGIN_CONFLICT')
    history = graph['historical_objects']
    _need(type(history) is list and 0 < len(history) <= 16)
    seen_history = set()
    for item in history:
        _keys(item,('bytes','git_blob','head','object_repository_role','path','role','sha256','tree'))
        _need(item['object_repository_role'] in _ROLES and _hex(item['head'],40) and _hex(item['tree'],40) and
              _hex(item['git_blob'],40) and _hex(item['sha256'],64) and _integer(item['bytes'],_BLOB_LIMIT))
        _rel(item['path'])
        _need(item['role'] in ('DYNAMIC_TLS_FIXTURE_BYTES_NOT_EXECUTED','HISTORICAL_SOURCE_GUARD_REFERENCE_NOT_EXECUTED'))
        key = (item['object_repository_role'],item['head'],item['path'].casefold())
        _need(key not in seen_history,'ORIGIN_CONFLICT')
        seen_history.add(key)
    git_instances = {}
    source_results = []
    for role in _ROLES:
        root = roots[role]
        _metadata(root,budget)
        git = _Git(root,budget)
        git_instances[role] = git
        source = graph['sources'][role]
        _need(git.call(('rev-parse','HEAD'),cap=64).strip() == source['head'].encode(),'WRONG_HEAD')
        _need(git.call(('rev-parse','HEAD^{tree}'),cap=64).strip() == source['tree'].encode(),'WRONG_TREE')
        listing = _commit_listing(git,source['head'],source['tree'],'GIT_VERIFICATION_FAILED')
        files = inventories[role]['files']
        _need(listing == {path:{k:entry[k] for k in ('mode','git_blob')} for path,entry in files.items()},'RAW_MISMATCH')
        blobs = _objects(git,[(entry['git_blob'],'blob',entry['bytes']) for entry in files.values()])
        for entry in files.values():
            blob = blobs[entry['git_blob']]
            _need(len(blob) == entry['bytes'] and hashlib.sha256(blob).hexdigest() == entry['sha256'],'RAW_MISMATCH')
        del blobs
        _working(root,files,budget)
        source_results.append(dict(role=role,head=source['head'],tree=source['tree'],raw_files=len(files),
            inventory_sha256=source['inventory_sha256'],raw_match=True))
    historical = []
    historic_listings = {}
    for item in history:
        role = item['object_repository_role']
        git = git_instances[role]
        key = (role,item['head'],item['tree'])
        if key not in historic_listings:
            historic_listings[key] = _commit_listing(git,item['head'],item['tree'],'MISSING_HISTORICAL_OBJECT')
        listing = historic_listings[key]
        _need(listing.get(item['path'],{}).get('git_blob') == item['git_blob'],'MISSING_HISTORICAL_OBJECT')
        raw = _objects(git,[(item['git_blob'],'blob',item['bytes'])],'MISSING_HISTORICAL_OBJECT')[item['git_blob']]
        _need(len(raw) == item['bytes'] and hashlib.sha256(raw).hexdigest() == item['sha256'],'MISSING_HISTORICAL_OBJECT')
        historical.append(dict(role=role,head=item['head'],path=item['path'],blob=item['git_blob'],sha256=item['sha256'],raw_match=True))
    # Reobserve worktree files and identities before returning a point-in-time DATA result.
    for role in _ROLES:
        budget.check()
        _metadata(roots[role],budget)
        _need(git_instances[role].call(('rev-parse','HEAD'),cap=64).strip() == graph['sources'][role]['head'].encode(),'WRONG_HEAD')
        _working(roots[role],inventories[role]['files'],budget)
    budget.check()
    return dict(schema='grid.native-test-support-verification.v1',graph_sha256=expected_graph_sha256,
        status='SOURCE_MATCH_DATA_ONLY',sources=source_results,
        historical_objects=sorted(historical,key=lambda x:(x['role'],x['head'],x['path'])),
        module_origins=[dict(module=name,role=origins[name]['role'],path=origins[name]['path'],sha256=origins[name]['sha256'],raw_match=True) for name in sorted(origins)],
        artifact_closure=closure,unresolved_codes=[],fixture_import_allowed=False,native_execution_allowed=False)


def verify_native_test_support(graph_path: Path, *, expected_graph_sha256: str, source_roots: dict[str, Path]) -> dict:
    """Verify externally pinned local source DATA only; does not select or import it."""
    budget = _Budget()
    try:
        return _verify(graph_path,expected_graph_sha256,source_roots,budget)
    except NativeSupportVerificationError:
        raise
    except BaseException:
        raise NativeSupportVerificationError('INVALID_DESCRIPTOR') from None
