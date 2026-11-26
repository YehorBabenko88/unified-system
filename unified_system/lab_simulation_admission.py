"""LAB_SIMULATION startup admission (Workstream C, MASTER #111).

A separate, explicitly authorized path for local laboratory simulation only.
It does not replace or weaken the protected Windows service activation or the
``lab_runtime --execute`` gate, which stay unchanged.

Guarantees enforced here, all fail-closed:
- explicit operator authorization file, bound to the exact component identity
  (sha256 of every admitted source file) and to a short expiry;
- trading is never authorized; production credentials never reach children;
- loopback only (ports and DSNs);
- only supervisor-owned temporary resources;
- a child's admission is revoked as soon as the supervisor's pipe closes,
  the deadline passes, the temporary root identity changes or any admitted
  source file changes.
Stdlib only, importable on Windows and POSIX.
"""
import hashlib
import json
import os
import re
import stat
import threading
import time
from pathlib import Path

SCHEMA_AUTHORIZATION = 'unified.lab-simulation-authorization.v1'
SCHEMA_CAPABILITY = 'unified.lab-simulation-capability.v1'
MODULES = ('unified_system', 'market_data', 'math', 'terminan')
MAX_AUTHORIZATION_MS = 24 * 3600 * 1000
MAX_FILES = 20000
MAX_FILE_BYTES = 64 * 1024 * 1024
HEX64 = re.compile(r'[0-9a-f]{64}')
HEX40 = re.compile(r'[0-9a-f]{40}')
# Names that must never be forwarded to a LAB child, whatever their value.
FORBIDDEN_ENV = re.compile(r'(BYBIT|API_?KEY|API_?SECRET|SECRET|PASSWORD|PASSWD|PRIVATE_KEY|'
                           r'CREDENTIAL|ACCESS_KEY|AUTH_TOKEN|GITHUB_TOKEN|DATABASE_URL|_DSN$|PGPASS)', re.I)
BASE_ENV = ('SYSTEMROOT', 'WINDIR', 'SYSTEMDRIVE', 'TEMP', 'TMP', 'COMPUTERNAME', 'USERPROFILE',
            'APPDATA', 'LOCALAPPDATA', 'OS', 'PROCESSOR_ARCHITECTURE', 'PATH', 'HOME', 'LANG', 'LC_ALL')


class LabAdmissionRejected(Exception):
    """Generic refusal; never carries secrets or raw paths of the caller."""


def need(ok, code='LAB_ADMISSION_REJECTED'):
    if not ok:
        raise LabAdmissionRejected(code)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def _regular(path):
    info = path.lstat()
    need(not stat.S_ISLNK(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & 0x400,
         'LAB_LINK_REJECTED')
    return info


def tree_identity(root):
    """sha256 of every regular file under root. Links, reparse points and
    bytecode caches are refused rather than skipped, so stale bytecode can never
    be executed in place of admitted source."""
    root = Path(root)
    need(root.is_absolute(), 'LAB_PATH_REJECTED')
    need(stat.S_ISDIR(_regular(root).st_mode), 'LAB_PATH_REJECTED')
    files = {}
    for directory, dirs, names in os.walk(root):
        dirs.sort()
        base = Path(directory)
        for name in list(dirs):
            need(name != '__pycache__', 'LAB_BYTECODE_REJECTED')
            if name == '.git':
                dirs.remove(name)
                continue
            _regular(base / name)
        for name in sorted(names):
            need(not name.endswith(('.pyc', '.pyo')), 'LAB_BYTECODE_REJECTED')
            path = base / name
            info = _regular(path)
            need(stat.S_ISREG(info.st_mode) and info.st_size <= MAX_FILE_BYTES, 'LAB_FILE_REJECTED')
            files[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
            need(len(files) <= MAX_FILES, 'LAB_TREE_TOO_LARGE')
    need(bool(files), 'LAB_TREE_EMPTY')
    return dict(files=files, sha256=hashlib.sha256(canonical(files)).hexdigest())


def tree_fingerprint(root):
    """Cheap per-call check: (size, mtime_ns, inode) of every admitted file."""
    root = Path(root)
    result = {}
    for directory, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d != '.git')
        for name in names:
            path = Path(directory) / name
            info = path.lstat()
            result[path.relative_to(root).as_posix()] = (info.st_size, info.st_mtime_ns, info.st_ino)
    return result


def components_digest(sources):
    """sources: {module_id: {'root', 'commit', 'version', 'tree_sha256'}}"""
    need(type(sources) is dict and set(sources) <= set(MODULES) and {'market_data', 'terminan'} <= set(sources))
    body = {m: dict(commit=s['commit'], version=s['version'], tree_sha256=s['tree_sha256'])
            for m, s in sorted(sources.items())}
    return hashlib.sha256(canonical(body)).hexdigest()


def load_authorization(path, digest, *, now_ms=None):
    """The operator's explicit, digest-bound, expiring permission to start."""
    now_ms = int(time.time() * 1000) if now_ms is None else now_ms
    raw = Path(path).read_bytes()
    need(0 < len(raw) <= 4096, 'LAB_AUTHORIZATION_REJECTED')

    def unique(pairs):
        out = {}
        for k, v in pairs:
            need(k not in out, 'LAB_AUTHORIZATION_REJECTED')
            out[k] = v
        return out
    try:
        value = json.loads(raw, object_pairs_hook=unique)
    except (ValueError, UnicodeDecodeError):
        raise LabAdmissionRejected('LAB_AUTHORIZATION_REJECTED') from None
    keys = {'schema', 'mode', 'components_sha256', 'release_id', 'issued_at_ms', 'expires_at_ms',
            'loopback_only', 'trading_authorized', 'production_credentials', 'operator'}
    need(type(value) is dict and set(value) == keys, 'LAB_AUTHORIZATION_REJECTED')
    need(value['schema'] == SCHEMA_AUTHORIZATION and value['mode'] == 'LAB_SIMULATION', 'LAB_AUTHORIZATION_REJECTED')
    need(value['loopback_only'] is True and value['trading_authorized'] is False
         and value['production_credentials'] is False, 'LAB_AUTHORIZATION_SCOPE_REJECTED')
    need(type(value['components_sha256']) is str and value['components_sha256'] == digest,
         'LAB_AUTHORIZATION_COMPONENTS_MISMATCH')
    need(type(value['release_id']) is str and re.fullmatch(r'[A-Za-z0-9._-]{1,64}', value['release_id']) is not None,
         'LAB_AUTHORIZATION_REJECTED')
    need(type(value['operator']) is str and 0 < len(value['operator']) <= 128, 'LAB_AUTHORIZATION_REJECTED')
    issued, expires = value['issued_at_ms'], value['expires_at_ms']
    need(type(issued) is int and type(expires) is int and issued <= now_ms < expires
         and expires - issued <= MAX_AUTHORIZATION_MS, 'LAB_AUTHORIZATION_EXPIRED')
    return value


def child_environment(base, extra):
    """Allow-list only. Production credentials cannot be forwarded by accident."""
    env = {k: v for k, v in base.items() if k.upper() in BASE_ENV}
    for key, value in extra.items():
        need(type(key) is str and type(value) is str, 'LAB_ENV_REJECTED')
        allowed = key in ('UNIFIED_INSTANCE_TOKEN', 'MARKET_DATA_DSN', 'UNIFIED_MARKET_DATA_READ_CAPABILITY')
        need(allowed or FORBIDDEN_ENV.search(key) is None, 'LAB_ENV_CREDENTIAL_REJECTED')
        if key == 'MARKET_DATA_DSN':
            need(loopback_dsn(value), 'LAB_DSN_NOT_LOOPBACK')
        env[key] = value
    env.update(UNIFIED_DEPLOYMENT_MODE='LAB_SIMULATION', UNIFIED_ORDER_MODE='PAPER_ONLY',
               UNIFIED_TRADING_AUTHORIZED='false', PYTHONDONTWRITEBYTECODE='1')
    return env


def loopback_dsn(dsn):
    m = re.fullmatch(r'postgresql://([A-Za-z0-9_]{1,63}):([A-Za-z0-9]{16,128})@(127\.0\.0\.1|localhost):([0-9]{1,5})/'
                     r'([A-Za-z0-9_]{1,63})', dsn)
    return m is not None and 1 <= int(m[4]) <= 65535 and int(m[4]) != 5432


class LabGrant:
    """Child-side live admission. require_current() returns exactly True or raises."""

    def __init__(self, capability, *, watch_stream=None, clock=time.time):
        need(type(capability) is dict and capability.get('schema') == SCHEMA_CAPABILITY)
        need(capability.get('module_id') in ('market_data', 'terminan'))
        need(type(capability.get('instance_token')) is str and HEX64.fullmatch(capability['instance_token']) is not None)
        need(type(capability.get('deadline_ms')) is int)
        sources = capability.get('sources')
        need(type(sources) is dict and {'market_data', 'terminan'} <= set(sources) <= set(MODULES))
        self._capability = capability
        self._clock = clock
        self._revoked = threading.Event()
        temp = Path(capability['temp_root'])
        info = temp.lstat()
        need(stat.S_ISDIR(info.st_mode) and [info.st_dev, info.st_ino] == capability['temp_identity'],
             'LAB_TEMP_IDENTITY_REJECTED')
        self._temp = temp
        self._fingerprints = {}
        for module_id, source in sources.items():
            need(type(source) is dict and HEX40.fullmatch(source.get('commit', '')) is not None
                 and HEX64.fullmatch(source.get('tree_sha256', '')) is not None)
            need(tree_identity(source['root'])['sha256'] == source['tree_sha256'], 'LAB_COMPONENT_IDENTITY_REJECTED')
            self._fingerprints[module_id] = tree_fingerprint(source['root'])
        if watch_stream is not None:
            threading.Thread(target=self._watch, args=(watch_stream,), daemon=True).start()

    def _watch(self, stream):
        try:
            while stream.read(1):
                pass
        finally:
            self.revoke()

    def revoke(self):
        self._revoked.set()

    @property
    def revoked(self):
        return self._revoked.is_set()

    def require_current(self):
        need(not self._revoked.is_set(), 'LAB_ADMISSION_REVOKED')
        need(self._clock() * 1000 < self._capability['deadline_ms'], 'LAB_ADMISSION_EXPIRED')
        info = self._temp.lstat()
        need([info.st_dev, info.st_ino] == self._capability['temp_identity'], 'LAB_TEMP_IDENTITY_CHANGED')
        for module_id, expected in self._fingerprints.items():
            need(tree_fingerprint(self._capability['sources'][module_id]['root']) == expected,
                 'LAB_COMPONENT_CHANGED')
        return True

    def source_identity(self, module_id):
        self.require_current()
        need(module_id in self._capability['sources'])
        source = self._capability['sources'][module_id]
        return dict(commit=source['commit'], version=source['version'], tree_sha256=source['tree_sha256'])
