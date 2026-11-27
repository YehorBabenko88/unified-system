"""Strict untrusted Stage1 contracts, independent of authority and checkpoint codecs."""
from dataclasses import dataclass
import json
import re
from typing import NoReturn

U63_MAX = 9223372036854775807
MAX_CLAIM_BYTES = 32768  # Local parser ceiling, not a production capacity policy.
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z")
_SHA = re.compile(r"[0-9a-f]{64}\Z")


class StorageBlocked(ValueError):
    """Closed, nonsecret failure; never a partial successful effect."""


def require(condition, code="INVALID_STORAGE_CLAIM"):
    if not condition:
        raise StorageBlocked(code)


def identifier(value):
    require(type(value) is str and _ID.fullmatch(value) is not None)
    return value


def u63(value, *, positive=False):
    require(type(value) is str and re.fullmatch(r"0|[1-9][0-9]{0,18}", value) is not None)
    number = int(value)
    require((1 if positive else 0) <= number <= U63_MAX)
    return number


def digest(value):
    require(type(value) is str and _SHA.fullmatch(value) is not None)
    return value


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "DUPLICATE_FIELD")
        result[key] = value
    return result


def _no_number(_value):
    raise StorageBlocked("JSON_NUMBER_NOT_ALLOWED")


def _shape(value, depth=1):
    require(depth <= 12, "CLAIM_DEPTH_EXCEEDED")
    if type(value) is dict:
        require(len(value) <= 48, "CLAIM_MEMBERS_EXCEEDED")
        for key, child in value.items():
            _shape(key, depth + 1)
            _shape(child, depth + 1)
    elif type(value) is list:
        require(len(value) <= 32, "CLAIM_ARRAY_EXCEEDED")
        for child in value:
            _shape(child, depth + 1)
    elif type(value) is str:
        require(all(32 <= ord(char) <= 126 for char in value), "NON_ASCII_CLAIM")
    else:
        require(value is None or type(value) is bool)


def _decode(raw, *, canonical):
    require(type(raw) is bytes and 0 < len(raw) <= MAX_CLAIM_BYTES, "CLAIM_SIZE_EXCEEDED")
    # Bound nesting before the recursive JSON decoder; brackets inside strings do not count.
    depth, quoted, escaped = 0, False, False
    for byte in raw:
        if quoted:
            if escaped:
                escaped = False
            elif byte == 92:
                escaped = True
            elif byte == 34:
                quoted = False
        elif byte == 34:
            quoted = True
        elif byte in (91, 123):
            depth += 1
            require(depth <= 12, "CLAIM_DEPTH_EXCEEDED")
        elif byte in (93, 125):
            depth -= 1
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                           parse_int=_no_number, parse_float=_no_number, parse_constant=_no_number)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise StorageBlocked("INVALID_JSON_CLAIM") from exc
    require(type(value) is dict)
    _shape(value)
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    require(not canonical or encoded == raw, "NONCANONICAL_CLAIM")
    return value, encoded


@dataclass(frozen=True)
class UntrustedClaim:
    canonical_bytes: bytes

    @property
    def value(self):
        return _decode(self.canonical_bytes, canonical=True)[0]

    @property
    def authority_verified(self):
        return False


def decode_untrusted_claim(raw: bytes) -> UntrustedClaim:
    """Generic bounded canonical claim parser; NOT a V3 checkpoint schema validator."""
    return UntrustedClaim(_decode(raw, canonical=True)[1])


def require_publication_authority(_claim) -> NoReturn:
    """No verifier/callback/boolean can enable effects in this independent slice."""
    raise StorageBlocked("PROOF_ADAPTER_UNAVAILABLE")


@dataclass(frozen=True)
class InstrumentIdentity:
    exchange: str
    category: str
    symbol: str
    instrument_version: str

    def __post_init__(self):
        identifier(self.exchange)
        require(type(self.category) is str and self.category in ("linear", "inverse", "spot", "option"))
        require(type(self.symbol) is str and re.fullmatch(r"[A-Z0-9][A-Z0-9_-]{0,63}", self.symbol) is not None)
        u63(self.instrument_version, positive=True)

    @classmethod
    def from_mapping(cls, value):
        require(type(value) is dict and set(value) == {"exchange", "category", "symbol", "instrument_version"})
        return cls(**value)


@dataclass(frozen=True)
class SegmentClaim:
    schema: str
    dataset_id: str
    instrument: InstrumentIdentity
    source_id: str
    partition_id: str
    data_kind: str
    schema_version: str
    encoding: str
    start_ms: str
    end_ms: str
    sha256: str
    byte_length: str
    record_count: str

    def __post_init__(self):
        require(type(self.schema) is str and self.schema == "unified.storage.segment-claim.stage1")
        require(type(self.dataset_id) is str and _UUID.fullmatch(self.dataset_id) is not None)
        require(type(self.instrument) is InstrumentIdentity)
        identifier(self.source_id)
        identifier(self.partition_id)
        require(type(self.data_kind) is str and self.data_kind in ("raw", "normalized", "derived", "checkpoints", "paper_events"))
        require(type(self.schema_version) is str and self.schema_version == "1")
        require(type(self.encoding) is str and self.encoding == "jsonl.stage1")
        require(u63(self.start_ms) < u63(self.end_ms))
        digest(self.sha256)
        u63(self.byte_length, positive=True)
        u63(self.record_count, positive=True)

    @classmethod
    def from_mapping(cls, value):
        require(type(value) is dict and set(value) == set(cls.__dataclass_fields__))
        copied = dict(value)
        copied["instrument"] = InstrumentIdentity.from_mapping(copied["instrument"])
        return cls(**copied)
