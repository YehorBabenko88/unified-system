"""Exact local checkpoint-object readback without codec or authority promotion."""
from dataclasses import dataclass

from .contracts import StorageBlocked, require
from .object_store import ObjectStore


@dataclass(frozen=True)
class CheckpointObjectObservation:
    raw_bytes: bytes
    object_sha256: str

    @property
    def publication_confirmed(self):
        return False

    @property
    def checkpoint_schema_verified(self):
        return False

    def require_recovery_cursor(self):
        raise StorageBlocked("CHECKPOINT_PROOF_ADAPTER_UNAVAILABLE")


def inspect_checkpoint_object(store, object_sha256):
    require(type(store) is ObjectStore, "OWNED_OBJECT_STORE_REQUIRED")
    raw = store.read(object_sha256, max_bytes=32768)
    return CheckpointObjectObservation(raw, object_sha256)
