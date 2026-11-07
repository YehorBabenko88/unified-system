"""Bounded isolated object-inventory copies and actual byte restore tests.

Not a dataset backup, authority restore, rollback executor or admitted service.
Inventory provenance, independent media and schema/closure admission are external
requirements. This module never deletes or replaces an existing object.
"""
from dataclasses import dataclass
import hashlib
import json

from .contracts import digest, require
from .object_store import MAX_OBJECT_BYTES, ObjectStore

MAX_INVENTORY_OBJECTS = 256
MAX_INVENTORY_BYTES = 1024 * 1024 * 1024


@dataclass(frozen=True)
class CopyObservation:
    inventory_sha256: str
    source_store_id: str
    destination_store_id: str
    object_count: int
    byte_count: int
    restore_test_passed: bool

    @property
    def publication_confirmed(self):
        return False


def _inventory(value):
    require(type(value) is tuple and 0 < len(value) <= MAX_INVENTORY_OBJECTS, "INVENTORY_BOUND_INVALID")
    seen, total = set(), 0
    for entry in value:
        require(type(entry) is tuple and len(entry) == 2, "INVENTORY_ENTRY_INVALID")
        sha, size = entry
        digest(sha)
        require(type(size) is int and 0 <= size <= MAX_OBJECT_BYTES, "INVENTORY_SIZE_INVALID")
        require(sha not in seen, "INVENTORY_DUPLICATE")
        seen.add(sha)
        total += size
        require(total <= MAX_INVENTORY_BYTES, "INVENTORY_TOTAL_EXCEEDED")
    canonical = json.dumps([[sha, str(size)] for sha, size in sorted(value)], separators=(",", ":")).encode("ascii")
    # This digest binds this local inventory encoding, never a dataset root.
    return hashlib.sha256(b"isolated-object-inventory.v1\x00" + canonical).hexdigest(), total


def _copy(source, destination, inventory, *, restore):
    require(type(source) is ObjectStore and type(destination) is ObjectStore, "OBJECT_STORE_REQUIRED")
    inventory_sha, total = _inventory(inventory)
    source._check()
    destination._check()
    require(source.store_id != destination.store_id and
            source._identities["."] != destination._identities["."], "INDEPENDENT_ROOT_REQUIRED")
    for sha, size in inventory:
        raw = source.read(sha, max_bytes=size)
        require(len(raw) == size, "INVENTORY_LENGTH_MISMATCH")
        copied = destination.put(raw, max_bytes=size)
        require(copied.sha256 == sha and copied.byte_length == size, "COPY_MISMATCH")
    # Re-read the entire destination inventory after copying. Any failure yields
    # no success observation; partial objects remain charged/retained by caller.
    for sha, size in inventory:
        require(len(destination.read(sha, max_bytes=size)) == size, "RESTORE_LENGTH_MISMATCH")
    source._check()
    destination._check()
    return CopyObservation(inventory_sha, source.store_id, destination.store_id,
                           len(inventory), total, restore)


def copy_inventory(source, backup_destination, inventory):
    """Copy actual bytes; result explicitly does not claim a restore test."""
    return _copy(source, backup_destination, inventory, restore=False)


def verify_restore(backup_source, isolated_destination, inventory):
    """Restore and rehash exact inventory into a distinct owned local root.

    The observation qualifies these fixture bytes only. It does not prove backup
    origin, independence of media, closure completeness, crash durability, schema
    validity, authority state or service rollback.
    """
    return _copy(backup_source, isolated_destination, inventory, restore=True)
