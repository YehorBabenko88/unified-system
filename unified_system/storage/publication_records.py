"""Exact local original-intent custody, not a native wire or proof ABI.

Native publication/receipt/access schemas still require A2/A4/A5/A7 co-ACK.
These records intentionally cannot represent COMMITTED or grant any permission.
"""
from dataclasses import dataclass
import hashlib

from .contracts import _UUID, require

MAX_ORIGINAL_BYTES = 16384


def publication_identifier(value):
    require(type(value) is str and _UUID.fullmatch(value) is not None,
            'INVALID_PUBLICATION_IDENTIFIER')
    return value


@dataclass(frozen=True)
class RetainedPublicationIntent:
    """Opaque candidate bytes, not an approved native intent/schema/authority."""
    publication_id: str
    raw_bytes: bytes

    def __post_init__(self):
        publication_identifier(self.publication_id)
        require(type(self.raw_bytes) is bytes and 0 < len(self.raw_bytes) <= MAX_ORIGINAL_BYTES,
                'INVALID_ORIGINAL_PUBLICATION_BYTES')

    @property
    def sha256(self):
        return hashlib.sha256(self.raw_bytes).hexdigest()

    @property
    def authority_verified(self):
        return False


@dataclass(frozen=True)
class PendingPublicationObservation:
    """Local journal observation; never an A2 result/receipt/projection handle."""
    publication_id: str
    original_sha256: str
    local_phase: str

    @property
    def native_outcome(self):
        return 'UNKNOWN'

    @property
    def publication_confirmed(self):
        return False

    @property
    def retry_authorized(self):
        return False

    @property
    def hold_release_authorized(self):
        return False
