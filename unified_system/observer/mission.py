"""Stable binary capture of a rollback journal; never SQL-connect the source.

Disabled until a caller explicitly admits the source and pinned reader. Source
observations confer no runtime authority. Existing MissionController validates
only the Observer-owned copy, through its existing open/projection APIs.
"""
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import threading
import time
import types
import sys

from .model import need, stamp
from .sources import MissionProjectionSource
from .store import ordinary

ENGINE_VERSION = 'e869d8365c7e54ed3da3739d9cdf15948f37f022'
ENGINE_PINS = {
    'contracts':'935f946bcf9cf64f9c4b98a9cd6f391e92e03f6db5120ad910bb11f3e1dbc9fc',
    'journal':'9f170cf33f8cdd79baef6fa633d03bebf9eb4b594c54c9cf8dd6c7cb9810bbc3',
    'mission_controller':'e4403a3bd4535aac7622f32d7b02b50379222506c86863faeb6d33f8bc81b644'}
LIMIT = 2097152
_module_lock = threading.Lock()


class PinnedExistingMissionReader:
    def __init__(self, source_directory):
        directory = Path(source_directory); ordinary(directory)
        held = {}
        for name, pin in ENGINE_PINS.items():
            path = directory/(name+'.py'); ordinary(path, False)
            need(path.stat().st_size <= 131072, 'MISSION_ENGINE_BOUND')
            raw = path.read_bytes()
            need(hashlib.sha256(raw).hexdigest() == pin, 'MISSION_ENGINE_SOURCE_PIN')
            held[name] = raw
        # Execute only the exact held existing modules. No package path search,
        # EOL aliases, new journal parser or imports from the working tree.
        alias = '_unified_observer_pinned_mission_e869'
        with _module_lock:
            need(alias not in sys.modules, 'MISSION_ENGINE_ALREADY_LOADED')
            package = types.ModuleType(alias); package.__path__ = []
            sys.modules[alias] = package
            try:
                modules = {}
                for name, raw in held.items():
                    module = types.ModuleType(alias+'.'+name)
                    module.__package__ = alias
                    sys.modules[module.__name__] = module
                    exec(compile(raw, '<pinned-existing-'+name+'>', 'exec'), module.__dict__)
                    modules[name] = module
                self.controller = modules['mission_controller'].MissionController
            finally:
                for name in held: sys.modules.pop(alias+'.'+name, None)
                sys.modules.pop(alias, None)

    def read_copy(self, path):
        controller = self.controller.open(path)
        projection = controller.projection(); continuation = controller.continuation_projection()
        need(projection['sequence'] == continuation['sequence'], 'MISSION_COPY_SEQUENCE')
        projection['continuations'] = continuation['continuations']
        projection['continuation_sequence'] = continuation['sequence']
        return projection


def _identity(info):
    # Windows Python 3.12 path-stat ctime is creation time while CRT fstat can
    # report last metadata change. Never equate these different clock semantics.
    # File ID/dev/size/mtime bind handle and path; path ctime is checked separately.
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


def _sidecars_absent(path):
    for suffix in ('-wal','-shm','-journal'):
        sidecar = Path(str(path)+suffix)
        need(not sidecar.exists() and not sidecar.is_symlink(), 'MISSION_SOURCE_BUSY_SIDECAR')


def _header(raw):
    need(100 <= len(raw) <= LIMIT and raw[:16] == b'SQLite format 3\0', 'MISSION_SOURCE_HEADER')
    need(raw[18:20] == b'\1\1', 'MISSION_SOURCE_WAL_REJECTED')
    page_size = int.from_bytes(raw[16:18], 'big'); page_size = 65536 if page_size == 1 else page_size
    need(page_size in (512,1024,2048,4096,8192,16384,32768,65536) and len(raw)%page_size == 0,
         'MISSION_SOURCE_PAGE_LAYOUT')
    need(int.from_bytes(raw[28:32], 'big')*page_size == len(raw) and raw[24:28] == raw[92:96],
         'MISSION_SOURCE_HEADER_NOT_STABLE')


class MissionJournalCopySource:
    def __init__(self, policy, source, snapshot_directory, reader, *, read_copy_admitted=False):
        need(read_copy_admitted is True, 'MISSION_COPY_ADMISSION_REQUIRED')
        need(policy.kind == 'mission_projection' and policy.source_version == ENGINE_VERSION,
             'MISSION_COPY_POLICY_PIN')
        need(type(reader) is PinnedExistingMissionReader, 'PINNED_EXISTING_MISSION_READER_REQUIRED')
        self.policy, self.path, self.reader = policy, Path(source), reader
        ordinary(self.path, False)
        self.directory = Path(snapshot_directory); ordinary(self.directory)
        need(not self.path.resolve().is_relative_to(self.directory.resolve()),
             'MISSION_SOURCE_INSIDE_SNAPSHOT_DIRECTORY')
        if not self.directory.exists():
            self.directory.mkdir()
            with (self.directory/'observer-snapshots.json').open('x', encoding='utf-8') as stream:
                stream.write(json.dumps({'schema':'observer.mission-copies.v1','source_version':ENGINE_VERSION}))
        self._lock = threading.Lock()

    def _capture(self):
        path = self.path; ordinary(path, False); _sidecars_absent(path)
        before = path.stat(); need(100 <= before.st_size <= LIMIT, 'MISSION_SOURCE_BOUND')
        deadline = time.monotonic()+2
        with path.open('rb') as stream:
            need(_identity(os.fstat(stream.fileno())) == _identity(before), 'MISSION_SOURCE_REPLACED')
            first = stream.read(LIMIT+1); _header(first)
            stream.seek(0); second = stream.read(LIMIT+1)
            need(time.monotonic() <= deadline and first == second, 'MISSION_SOURCE_CHANGED')
            need(_identity(os.fstat(stream.fileno())) == _identity(before), 'MISSION_SOURCE_CHANGED')
        ordinary(path, False); _sidecars_absent(path)
        after = path.stat()
        need(_identity(after) == _identity(before) and after.st_ctime_ns == before.st_ctime_ns,
             'MISSION_SOURCE_CHANGED')
        return first, hashlib.sha256(first).hexdigest()

    def read(self, now):
        with self._lock:
            raw, digest = self._capture()
            ordinary(self.directory)
            marker = self.directory/'observer-snapshots.json'; ordinary(marker, False)
            need(marker.read_bytes() == json.dumps({'schema':'observer.mission-copies.v1',
                 'source_version':ENGINE_VERSION}).encode(), 'MISSION_SNAPSHOT_OWNER')
            children = list(self.directory.iterdir())
            need(len(children) <= 3, 'MISSION_SNAPSHOT_RETENTION')
            copies=[]
            for path in children:
                ordinary(path, False)
                if path == marker: continue
                need(len(path.name) == 71 and path.name.endswith('.sqlite') and
                     all(c in '0123456789abcdef' for c in path.stem), 'MISSION_SNAPSHOT_FOREIGN_FILE')
                need(path.stat().st_size <= LIMIT and hashlib.sha256(path.read_bytes()).hexdigest() == path.stem,
                     'MISSION_SNAPSHOT_INTEGRITY')
                copies.append(path)
            target = self.directory/(digest+'.sqlite')
            if not target.exists():
                if len(copies) == 2:
                    # Only this adapter's validated private content-addressed copy.
                    min(copies, key=lambda p:p.stat().st_mtime_ns).unlink()
                with target.open('xb') as stream: stream.write(raw)
            projection = self.reader.read_copy(target)
            need(target.read_bytes() == raw, 'MISSION_OWN_COPY_CHANGED')
            _sidecars_absent(target)
            # All raw requirements, private paths and receipts stay in own copy;
            # existing export reducer emits only explicitly whitelisted summaries.
            envelope = json.dumps({'schema':'unified.observer.mission-export.v1',
                'source_version':ENGINE_VERSION, 'observed_at':stamp(now), 'projection':projection}).encode()
            parser = MissionProjectionSource(self.policy, target)
            facts = parser.parse_bytes(envelope, now)
            return [replace(f, digest=digest) for f in facts]
