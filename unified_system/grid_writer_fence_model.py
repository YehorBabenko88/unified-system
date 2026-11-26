"""Root-owned *model* of the resource-side Grid writer fence, not an actuator.

C must implement atomic fencing inside PostgreSQL's writer transaction. An
in-process lock, Consul lease, caller-supplied receipt or this pure state model
cannot constrain a stale external writer. No network, SQL, service or Bybit IO.
"""
from dataclasses import dataclass
import re
import uuid

SCHEMA = "unified.grid-writer-fence-model.v1"
_SCOPE = "ISOLATED_LAB_ONLY"
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_OWNER = re.compile(r"[A-Za-z0-9_.:-]{1,128}\Z")
_MAX = (1 << 63) - 1


class ResourceFenceBlocked(ValueError):
    """Bounded refusal only; never include SQL, credentials or peer data."""


def _need(value, code="FENCE_MODEL_REJECTED"):
    if not value:
        raise ResourceFenceBlocked(code)


def _uuid4(value):
    if type(value) is not str:
        return False
    try:
        item = uuid.UUID(value)
        return item.version == 4 and str(item) == value
    except (ValueError, TypeError, AttributeError):
        return False


def _digest(value):
    return type(value) is str and _HEX.fullmatch(value) is not None


@dataclass(frozen=True)
class WriterLeaseIdentity:
    """Versioned identity carried to C, not proof the lease is current."""
    owner: str
    session_id: str
    token: int
    instance_id: str
    source_sha256: str
    schema_sha256: str

    def __post_init__(self):
        _need(type(self.owner) is str and _OWNER.fullmatch(self.owner) is not None)
        _need(_uuid4(self.session_id) and _uuid4(self.instance_id))
        _need(type(self.token) is int and 0 < self.token <= _MAX)
        _need(_digest(self.source_sha256) and _digest(self.schema_sha256))


@dataclass(frozen=True)
class ModelFenceState:
    """Durable high-water state that a DB transaction would have to maintain."""
    schema: str
    scope: str
    generation: int
    identity: WriterLeaseIdentity
    active: bool

    def __post_init__(self):
        _need(self.schema == SCHEMA and self.scope == _SCOPE)
        _need(type(self.generation) is int and 1 <= self.generation <= _MAX)
        _need(type(self.identity) is WriterLeaseIdentity and type(self.active) is bool)


def claim_model(previous, incoming, *, legacy_quiescent):
    """Pure CAS transition. Caller must separately prove host/DB quiescence.

    C's future DB adapter must lock the persistent fence row and enforce this
    transition in the SAME transaction as the authoritative writer claim.
    Returning a state here never grants execution or write permissions.
    """
    _need(type(incoming) is WriterLeaseIdentity)
    _need(legacy_quiescent is True, "FENCE_LEGACY_WRITER_UNVERIFIED")
    if previous is None:
        return ModelFenceState(SCHEMA, _SCOPE, 1, incoming, True)
    _need(type(previous) is ModelFenceState)
    _need(previous.generation < _MAX, "FENCE_GENERATION_EXHAUSTED")
    _need(incoming.token > previous.identity.token, "FENCE_STALE_TOKEN")
    _need(not previous.active, "FENCE_PREVIOUS_WRITER_ACTIVE")
    return ModelFenceState(SCHEMA, _SCOPE, previous.generation + 1, incoming, True)


def stop_model(current, identity):
    """Quiescence transition preserves the durable token high-water mark."""
    _need(type(current) is ModelFenceState and type(identity) is WriterLeaseIdentity)
    _need(current.active and current.identity == identity, "FENCE_STALE_WRITER")
    return ModelFenceState(SCHEMA, _SCOPE, current.generation, current.identity, False)


def write_matches_model(current, identity, generation):
    """Model-only predicate. C must enforce a stronger DB-side native fence.

    Never feed this value to a runtime admission, trading or SQL write path.
    """
    return (type(current) is ModelFenceState
            and type(identity) is WriterLeaseIdentity
            and type(generation) is int
            and current.active and current.generation == generation
            and current.identity == identity)


def native_writer_admission(*_args, **_kwargs):
    """Explicitly unavailable until a C-owned DB and Root native gate exist."""
    raise ResourceFenceBlocked("NATIVE_DB_FENCE_NOT_ADMITTED")
