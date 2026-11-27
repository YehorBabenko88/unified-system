"""Bounded local byte capture over existing ObjectStore/Journal, not authority.

Root owns one private context, no external writers, and actual runtime admission.
Logical observations/headroom are NOT a physical disk quota or crash guarantee.
"""
from dataclasses import dataclass
import hashlib
import json
import re
import threading

from ..journal import Journal
from .contracts import StorageBlocked, require
from .object_store import ObjectStore, _parents, _plain

SCHEMA = 'unified.storage.local-raw-capture-link.v1'
FIELDS = frozenset(('schema', 'classification', 'observation_sha256',
                    'observation_byte_count', 'payload_sha256', 'payload_byte_count'))


def _sha(value):
    return type(value) is str and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('ascii')


def _pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, 'RAW_CAPTURE_INPUT_INVALID')
        result[key] = value
    return result


def _integer(token):
    require(re.fullmatch(r'0|[1-9][0-9]*', token) is not None and len(token) <= 7,
            'RAW_CAPTURE_INPUT_INVALID')
    return int(token)


def _no_number(_):
    raise StorageBlocked('RAW_CAPTURE_INPUT_INVALID')


def decode_local_link(raw):
    """Closed canonical local receipt, NOT the opaque Grid observation codec."""
    require(type(raw) is bytes and 0 < len(raw) <= 1024, 'RAW_CAPTURE_INPUT_INVALID')
    try:
        value = json.loads(raw.decode('ascii'), object_pairs_hook=_pairs,
                           parse_int=_integer, parse_float=_no_number, parse_constant=_no_number)
        require(type(value) is dict and set(value) == FIELDS, 'RAW_CAPTURE_INPUT_INVALID')
        require(value['schema'] == SCHEMA and value['classification'] == 'LOCAL_UNATTESTED',
                'RAW_CAPTURE_INPUT_INVALID')
        require(_sha(value['observation_sha256']), 'RAW_CAPTURE_INPUT_INVALID')
        require(type(value['observation_byte_count']) is int
                and 1 <= value['observation_byte_count'] <= 16384, 'RAW_CAPTURE_INPUT_INVALID')
        require(value['payload_sha256'] is None or _sha(value['payload_sha256']),
                'RAW_CAPTURE_INPUT_INVALID')
        require(type(value['payload_byte_count']) is int
                and 0 <= value['payload_byte_count'] <= 1048576, 'RAW_CAPTURE_INPUT_INVALID')
        require(value['payload_sha256'] is not None or value['payload_byte_count'] == 0,
                'RAW_CAPTURE_INPUT_INVALID')
        require(_canonical(value) == raw, 'RAW_CAPTURE_INPUT_INVALID')
        return value
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise StorageBlocked('RAW_CAPTURE_INPUT_INVALID') from None


@dataclass(frozen=True)
class RawCaptureProfile:
    max_observations: int = 16
    max_payload_occurrence_bytes: int = 4194304
    max_state_bytes: int = 16777216
    sqlite_headroom_bytes: int | None = None
    inventory_file_limit: int | None = None

    def check(self):
        for value, ceiling in ((self.max_observations, 16),
                (self.max_payload_occurrence_bytes, 4194304),
                (self.max_state_bytes, 16777216),
                (self.sqlite_headroom_bytes, self.max_state_bytes),
                (self.inventory_file_limit, 128)):
            require(type(value) is int and type(ceiling) is int and 1 <= value <= ceiling,
                    'RAW_CAPTURE_PROFILE_REQUIRED')


@dataclass(frozen=True)
class LocalRawCaptureReadback:
    observation_bytes: bytes
    payload_bytes: bytes | None
    observation_sha256: str
    observation_byte_count: int
    payload_sha256: str | None
    payload_byte_count: int
    journal_record_digest: str

    classification = property(lambda self: 'LOCAL_UNATTESTED')
    local_content_verified = property(lambda self: True)
    publication_confirmed = property(lambda self: False)
    native_authority_verified = property(lambda self: False)
    replica_eligible = property(lambda self: False)
    durability = property(lambda self: 'UNKNOWN')


class RawCaptureAdapter:
    def __init__(self, owned_store, private_journal, profile):
        require(type(owned_store) is ObjectStore and type(private_journal) is Journal,
                'RAW_CAPTURE_LINK_UNAVAILABLE')
        self._store, self._journal, self._profile = owned_store, private_journal, profile
        self._busy = threading.Lock()
        self._failed = False

    def _layout(self):
        require(type(self._profile) is RawCaptureProfile, 'RAW_CAPTURE_PROFILE_REQUIRED')
        self._profile.check()
        ObjectStore._check(self._store)
        path = self._journal.path
        require(path.is_absolute() and '..' not in path.parts
                and path.parent == self._store._root.parent,
                'RAW_CAPTURE_LINK_UNAVAILABLE')
        _parents(path.parent)
        info = _plain(path, directory=False)
        require(info.st_size <= self._profile.max_state_bytes, 'RAW_CAPTURE_CAPACITY_EXCEEDED')
        for suffix in ('-wal', '-shm', '-journal'):
            sidecar = path.with_name(path.name + suffix)
            require(not sidecar.exists() and not sidecar.is_symlink(), 'RAW_CAPTURE_LINK_UNAVAILABLE')
        return info.st_dev, info.st_ino

    def _records(self):
        try:
            identity = self._layout()
            rows = Journal.read(self._journal)
            require(self._layout() == identity, 'RAW_CAPTURE_LINK_UNAVAILABLE')
            require(len(rows) <= self._profile.max_observations, 'RAW_CAPTURE_CAPACITY_EXCEEDED')
            links = {}
            for row in rows:
                require(row['state'] == 'OBSERVING', 'RAW_CAPTURE_LINK_UNAVAILABLE')
                link = decode_local_link(_canonical(row['receipt']))
                key = link['observation_sha256']
                require(key not in links, 'RAW_CAPTURE_LINK_UNAVAILABLE')
                # Existing Journal.read verifies stored digests but returns only
                # the canonical body. Derive that same verified record digest.
                links[key] = (link, hashlib.sha256(_canonical(row)).hexdigest())
            require(sum(link['payload_byte_count'] for link, _ in links.values())
                    <= self._profile.max_payload_occurrence_bytes, 'RAW_CAPTURE_CAPACITY_EXCEEDED')
            return links
        except StorageBlocked:
            raise
        except Exception:
            raise StorageBlocked('RAW_CAPTURE_LINK_UNAVAILABLE') from None

    def _inventory(self, links):
        """Conservative named-file size, not disk allocation or physical quota."""
        self._layout()
        root, store = self._journal.path.parent, self._store._root
        require({p.name for p in self._entries(root)} == {store.name, self._journal.path.name},
                'RAW_CAPTURE_LINK_UNAVAILABLE')
        expected = set()
        for link, _ in links.values():
            expected.add(link['observation_sha256'])
            if link['payload_sha256'] is not None:
                expected.add(link['payload_sha256'])
        require(not any((store/'staging').iterdir()), 'RAW_CAPTURE_LINK_UNAVAILABLE')
        objects, size, count = set(), 0, 0
        for folder in (root, store, store/'objects'):
            for path in self._entries(folder):
                # Expected directories were identity checked by ObjectStore.
                if path in (store, store/'objects', store/'staging'):
                    continue
                count += 1
                require(count <= self._profile.inventory_file_limit, 'RAW_CAPTURE_CAPACITY_EXCEEDED')
                info = _plain(path, directory=False)
                size += info.st_size
                if folder == store/'objects':
                    require(_sha(path.name), 'RAW_CAPTURE_LINK_UNAVAILABLE')
                    objects.add(path.name)
                elif folder == store:
                    require(path.name == 'owned-root.json', 'RAW_CAPTURE_LINK_UNAVAILABLE')
        require(objects == expected, 'RAW_CAPTURE_LINK_UNAVAILABLE')
        require(size <= self._profile.max_state_bytes, 'RAW_CAPTURE_CAPACITY_EXCEEDED')
        return size, objects, count

    def _entries(self, folder):
        entries = []
        for path in folder.iterdir():
            require(len(entries) < self._profile.inventory_file_limit + 3,
                    'RAW_CAPTURE_CAPACITY_EXCEEDED')
            entries.append(path)
        return entries

    def _read(self, link, digest):
        obs = ObjectStore.read(self._store, link['observation_sha256'],
                               max_bytes=link['observation_byte_count'])
        payload = None if link['payload_sha256'] is None else ObjectStore.read(
            self._store, link['payload_sha256'], max_bytes=link['payload_byte_count'])
        require(len(obs) == link['observation_byte_count']
                and (payload is None or len(payload) == link['payload_byte_count']),
                'RAW_CAPTURE_LINK_UNAVAILABLE')
        return LocalRawCaptureReadback(obs, payload, link['observation_sha256'], len(obs),
            link['payload_sha256'], 0 if payload is None else len(payload), digest)

    async def read_capture(self, observation_sha256):
        require(_sha(observation_sha256), 'RAW_CAPTURE_INPUT_INVALID')
        require(self._busy.acquire(blocking=False), 'RAW_CAPTURE_BUSY')
        try:
            links = self._records()
            require(observation_sha256 in links, 'RAW_CAPTURE_LINK_UNAVAILABLE')
            return self._read(*links[observation_sha256])
        except StorageBlocked:
            raise
        except Exception:
            raise StorageBlocked('RAW_CAPTURE_LINK_UNAVAILABLE') from None
        finally:
            self._busy.release()

    async def store_capture(self, *, observation_bytes, payload_bytes):
        require(type(observation_bytes) is bytes and 1 <= len(observation_bytes) <= 16384
                and (payload_bytes is None or type(payload_bytes) is bytes
                     and len(payload_bytes) <= 1048576), 'RAW_CAPTURE_INPUT_INVALID')
        require(self._busy.acquire(blocking=False), 'RAW_CAPTURE_BUSY')
        try:
            require(not self._failed, 'RAW_CAPTURE_WRITE_OUTCOME_UNKNOWN')
            links = self._records()
            key = hashlib.sha256(observation_bytes).hexdigest()
            payload_sha = None if payload_bytes is None else hashlib.sha256(payload_bytes).hexdigest()
            payload_count = 0 if payload_bytes is None else len(payload_bytes)
            link = dict(schema=SCHEMA, classification='LOCAL_UNATTESTED',
                        observation_sha256=key, observation_byte_count=len(observation_bytes),
                        payload_sha256=payload_sha, payload_byte_count=payload_count)
            if key in links:
                require(links[key][0] == link, 'RAW_CAPTURE_BINDING_CONFLICT')
                return self._read(*links[key])
            size, objects, file_count = self._inventory(links)
            require(len(links) < self._profile.max_observations
                    and sum(x['payload_byte_count'] for x, _ in links.values()) + payload_count
                    <= self._profile.max_payload_occurrence_bytes, 'RAW_CAPTURE_CAPACITY_EXCEEDED')
            new_objects = {key: len(observation_bytes)}
            if payload_sha is not None:
                new_objects[payload_sha] = payload_count
            new_objects = {sha: size for sha, size in new_objects.items() if sha not in objects}
            # Include a temporary alias even for a zero-byte object. A single
            # serial ObjectStore.put creates at most one such alias at a time.
            require(file_count + len(new_objects) + (1 if new_objects else 0)
                    <= self._profile.inventory_file_limit, 'RAW_CAPTURE_CAPACITY_EXCEEDED')
            prospective = sum(new_objects.values())
            require(size + 2*prospective + self._profile.sqlite_headroom_bytes
                    <= self._profile.max_state_bytes, 'RAW_CAPTURE_CAPACITY_EXCEEDED')
            try:
                if payload_bytes is not None:
                    ObjectStore.put(self._store, payload_bytes, max_bytes=1048576)
                    require(ObjectStore.read(self._store, payload_sha, max_bytes=payload_count)
                            == payload_bytes, 'RAW_CAPTURE_LINK_UNAVAILABLE')
                ObjectStore.put(self._store, observation_bytes, max_bytes=16384)
                require(ObjectStore.read(self._store, key, max_bytes=16384) == observation_bytes,
                        'RAW_CAPTURE_LINK_UNAVAILABLE')
                Journal.append(self._journal, 'OBSERVING', link, expected_sequence=len(links))
                after = self._records()
                require(key in after and after[key][0] == link, 'RAW_CAPTURE_LINK_UNAVAILABLE')
                self._inventory(after)
                return self._read(*after[key])
            except Exception:
                self._failed = True
                raise StorageBlocked('RAW_CAPTURE_WRITE_OUTCOME_UNKNOWN') from None
        except StorageBlocked:
            raise
        except Exception:
            raise StorageBlocked('RAW_CAPTURE_LINK_UNAVAILABLE') from None
        finally:
            self._busy.release()
