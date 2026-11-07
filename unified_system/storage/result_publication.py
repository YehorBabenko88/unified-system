"""Bounded immutable copies of a caller-declared byte graph, not publication.

All graph claims remain untrusted. Payloads are never decoded/reencoded. These
local byte checks do not verify semantic dependencies, replica eligibility,
independent failure domains, reservations or native commit authority.
"""
from dataclasses import dataclass
import hashlib
import json

from .contracts import _decode, digest, require, u63, StorageBlocked
from .object_store import ObjectStore
from .replica_evidence import LocalReplicaObservation

MAX_OBJECTS = 16
MAX_TOTAL_BYTES = 1024*1024
ROLES = frozenset(('artifact', 'descriptor', 'request', 'query_request', 'query_result',
                  'computation_receipt', 'corrected_replay', 'input_manifest', 'input_rows',
                  'input_coverage', 'input_schema', 'input_index', 'input_profile',
                  'input_dependencies', 'input_lineage', 'producer_metadata'))


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')


def _validate(raw):
    value, _ = _decode(raw, canonical=True)
    require(set(value) == {'schema', 'objects'})
    require(value['schema'] == 'unified.storage.local-declared-byte-closure.v1')
    entries = value['objects']
    require(type(entries) is list and 3 <= len(entries) <= MAX_OBJECTS)
    roles, seen, total = set(), {}, 0
    for entry in entries:
        require(type(entry) is dict and set(entry) == {'role', 'sha256', 'bytes', 'dependencies'})
        role = entry['role']
        require(type(role) is str and role in ROLES and role not in roles)
        roles.add(role)
        sha = digest(entry['sha256'])
        require(sha not in seen)
        size = u63(entry['bytes'], positive=True)
        total += size
        require(total <= MAX_TOTAL_BYTES)
        deps = entry['dependencies']
        require(type(deps) is list and len(deps) <= MAX_OBJECTS)
        for dependency in deps:
            digest(dependency)
        require(deps == sorted(set(deps)) and sha not in deps)
        seen[sha] = entry
    require({'artifact', 'descriptor', 'request'} <= roles)
    require([e['role'] for e in entries] == sorted(roles))
    visiting, complete = set(), set()

    def visit(sha):
        require(sha in seen and sha not in visiting, 'DECLARED_GRAPH_NOT_CLOSED_ACYCLIC')
        if sha in complete:
            return
        visiting.add(sha)
        for dependency in seen[sha]['dependencies']:
            visit(dependency)
        visiting.remove(sha)
        complete.add(sha)
    for sha in seen:
        visit(sha)
    return value


@dataclass(frozen=True)
class LocalByteClosure:
    canonical_bytes: bytes

    def __post_init__(self):
        _validate(self.canonical_bytes)

    @property
    def value(self):
        return _validate(self.canonical_bytes)

    @property
    def sha256(self):
        return hashlib.sha256(self.canonical_bytes).hexdigest()

    @property
    def publication_confirmed(self):
        return False

    @property
    def semantic_closure_verified(self):
        return False


def build_local_closure(entries):
    require(type(entries) is tuple and 3 <= len(entries) <= MAX_OBJECTS)
    objects, total = [], 0
    for item in entries:
        require(type(item) is tuple and len(item) == 3)
        role, raw, dependencies = item
        require(type(raw) is bytes and 0 < len(raw) <= MAX_TOTAL_BYTES)
        total += len(raw)
        require(total <= MAX_TOTAL_BYTES)
        require(type(dependencies) is tuple and len(dependencies) <= MAX_OBJECTS)
        for sha in dependencies:
            digest(sha)
        require(len(set(dependencies)) == len(dependencies))
        require(type(role) is str and role in ROLES)
        objects.append(dict(role=role, sha256=hashlib.sha256(raw).hexdigest(),
                            bytes=str(len(raw)), dependencies=sorted(dependencies)))
    return LocalByteClosure(_canonical(dict(schema='unified.storage.local-declared-byte-closure.v1',
                                           objects=sorted(objects, key=lambda e: e['role']))))


def _inventory(claim):
    require(type(claim) is LocalByteClosure)
    return [(entry['sha256'], int(entry['bytes'])) for entry in claim.value['objects']] + [
        (claim.sha256, len(claim.canonical_bytes))]


def stage_local_closure(store, claim, entries):
    require(type(store) is ObjectStore)
    inventory = _inventory(claim)
    rebuilt = build_local_closure(entries)
    require(rebuilt.canonical_bytes == claim.canonical_bytes, 'DECLARED_BYTES_MISMATCH')
    for _, raw, _ in entries:
        ObjectStore.put(store, raw, max_bytes=MAX_TOTAL_BYTES)
    ObjectStore.put(store, claim.canonical_bytes, max_bytes=32768)
    for sha, size in inventory:
        require(len(ObjectStore.read(store, sha, max_bytes=size)) == size)
    return claim


def copy_local_closure(source, destination, claim):
    require(type(source) is ObjectStore and type(destination) is ObjectStore)
    inventory = _inventory(claim)
    ObjectStore._check(source)
    ObjectStore._check(destination)
    require(source.store_id != destination.store_id and
            source._identities['.'] != destination._identities['.'], 'DISTINCT_LOCAL_ROOT_REQUIRED')
    # Validate the complete bounded source before the first destination mutation.
    raw_objects = []
    for sha, size in inventory:
        raw = ObjectStore.read(source, sha, max_bytes=size)
        require(len(raw) == size)
        raw_objects.append(raw)
    for raw in raw_objects:
        ObjectStore.put(destination, raw, max_bytes=MAX_TOTAL_BYTES)
    for sha, size in inventory:
        require(len(ObjectStore.read(destination, sha, max_bytes=size)) == size)
    ObjectStore._check(source)
    ObjectStore._check(destination)
    return LocalReplicaObservation(_canonical(dict(schema='unified.storage.local-copy-observation.v1',
        closure_sha256=claim.sha256, source_store_id=source.store_id,
        destination_store_id=destination.store_id, object_count=str(len(inventory)),
        byte_count=str(sum(size for _, size in inventory)))))


def commit_result(original_intent_bytes):
    raise StorageBlocked('NATIVE_RESULT_PUBLICATION_UNAVAILABLE')


def reconcile_result(original_intent_bytes):
    raise StorageBlocked('NATIVE_RESULT_RECONCILIATION_UNAVAILABLE')
