"""Local-only copy observations; native closure inventory is not admitted.

This is deliberately not the proposed native replica/CAS wire contract.
Neither source hashes nor a parsed observation confer replica eligibility.
"""
from dataclasses import dataclass
from .contracts import _decode, _UUID, digest, require, u63, StorageBlocked


@dataclass(frozen=True)
class LocalReplicaObservation:
    canonical_bytes: bytes

    def __post_init__(self):
        value, _ = _decode(self.canonical_bytes, canonical=True)
        require(set(value) == {'schema', 'closure_sha256', 'source_store_id',
                              'destination_store_id', 'object_count', 'byte_count'})
        require(value['schema'] == 'unified.storage.local-copy-observation.v1')
        digest(value['closure_sha256'])
        for name in ('source_store_id', 'destination_store_id'):
            require(type(value[name]) is str and _UUID.fullmatch(value[name]) is not None)
        require(value['source_store_id'] != value['destination_store_id'])
        require(4 <= u63(value['object_count'], positive=True) <= 17)
        require(u63(value['byte_count'], positive=True) <= 1024*1024+32768)

    @property
    def replica_valid(self):
        return False

    @property
    def failure_domain_verified(self):
        return False

    @property
    def publication_confirmed(self):
        return False


class ReplicaClosureInventory:
    """Deny-only placeholder, never an injectable native provider."""

    def capture_result_closure(self, original_intent_bytes, *, expected_authority):
        raise StorageBlocked('NATIVE_CLOSURE_CAPTURE_UNAVAILABLE')
