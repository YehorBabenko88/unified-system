"""Pure in-memory byte verification. No paths, file mutation, replication or authority."""
from dataclasses import dataclass
import hashlib
import hmac

from .contracts import InstrumentIdentity, SegmentClaim, _decode, digest, require, u63


@dataclass(frozen=True)
class ByteCheck:
    sha256: str
    byte_length: int
    record_count: int

    def __post_init__(self):
        digest(self.sha256)
        require(type(self.byte_length) is int and self.byte_length > 0)
        require(type(self.record_count) is int and self.record_count > 0)

    @property
    def status(self):
        return "BYTES_MATCHED_UNTRUSTED"

    @property
    def authority_verified(self):
        return False

    @property
    def source_completeness(self):
        return "UNKNOWN"


def verify_segment_bytes(raw: bytes, claim: SegmentClaim, *, max_bytes=8388608) -> ByteCheck:
    """Check exact bytes AND Stage1 JSONL framing; bytes never prove source coverage."""
    require(type(claim) is SegmentClaim)
    require(type(max_bytes) is int and 1 <= max_bytes <= 8388608)
    require(type(raw) is bytes and 0 < len(raw) <= max_bytes, "SEGMENT_SIZE_EXCEEDED")
    require(len(raw) == u63(claim.byte_length), "SEGMENT_LENGTH_MISMATCH")
    actual = hashlib.sha256(raw).hexdigest()
    require(hmac.compare_digest(actual, claim.sha256), "SEGMENT_HASH_MISMATCH")
    require(raw.endswith(b"\n"), "INCOMPLETE_SEGMENT_FRAME")
    count = 0
    for frame in raw.split(b"\n")[:-1]:
        require(bool(frame), "EMPTY_SEGMENT_FRAME")
        row = _decode(frame, canonical=False)[0]
        require(set(row) == {"schema_version", "event_time_ms", "instrument", "payload"})
        require(row["schema_version"] == claim.schema_version)
        require(type(row["payload"]) is dict)
        require(InstrumentIdentity.from_mapping(row["instrument"]) == claim.instrument, "INSTRUMENT_MISMATCH")
        require(u63(claim.start_ms) <= u63(row["event_time_ms"]) < u63(claim.end_ms), "EVENT_RANGE_MISMATCH")
        count += 1
    require(count == u63(claim.record_count), "SEGMENT_RECORD_COUNT_MISMATCH")
    return ByteCheck(actual, len(raw), count)
