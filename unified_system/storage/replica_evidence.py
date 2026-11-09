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


class LocalInventoryReadback:
    """Point-in-time local bytes only, NOT native closure/capture/replica proof.

ROOT commissioning and the future A2 native snapshot/issuer contract are separate.
This object cannot establish source trust against arbitrary hostile Python.
"""
    __slots__ = ('_store_id', '_closure_sha256', '_objects')

    def __new__(cls, *args, **kwargs):
        raise TypeError('READBACK_CREATED_BY_FIXED_LOCAL_READER_ONLY')

    def __setattr__(self, name, value):
        raise TypeError('LOCAL_READBACK_IMMUTABLE')

    def __copy__(self):
        raise TypeError('LOCAL_READBACK_NOT_TRANSFERABLE_PROOF')

    def __deepcopy__(self, memo):
        raise TypeError('LOCAL_READBACK_NOT_TRANSFERABLE_PROOF')

    def __reduce__(self):
        raise TypeError('LOCAL_READBACK_NOT_SERIALIZABLE_PROOF')

    @property
    def store_id(self):
        return self._store_id

    @property
    def closure_sha256(self):
        return self._closure_sha256

    @property
    def objects(self):
        return self._objects

    @property
    def native_replica_eligible(self):
        return False

    @property
    def failure_domain_qualified(self):
        return False

    @property
    def semantic_closure_verified(self):
        return False

    @property
    def publication_confirmed(self):
        return False


def _issue_local_inventory_readback(store_id, closure_sha256, observations):
    # Private construction is data provenance hygiene, not an authority boundary.
    result = object.__new__(LocalInventoryReadback)
    object.__setattr__(result, '_store_id', store_id)
    object.__setattr__(result, '_closure_sha256', closure_sha256)
    object.__setattr__(result, '_objects', tuple(observations))
    return result
