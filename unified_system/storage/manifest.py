"""Strict local instrument-manifest candidate codec; no authority admission.

Registry, segment/page/schema/coverage/dependency proofs and current native head
CAS are deliberately NOT inferred from canonical bytes or a matching local hash.
"""
from dataclasses import dataclass
import hashlib
import json
import re

from .contracts import StorageBlocked, _UUID, _decode, digest, identifier, require, u63
from .object_store import ObjectStore

MAX_MANIFEST_BYTES = 16384
_KINDS = ("raw", "normalized", "derived", "checkpoints", "paper_events")


def _fields(value, names):
    require(type(value) is dict and all(type(k) is str for k in value)
            and set(value) == set(names), "MANIFEST_FIELDS_INVALID")


def _uuid(value):
    require(type(value) is str and _UUID.fullmatch(value) is not None, "MANIFEST_UUID_INVALID")


def _value(raw):
    require(type(raw) is bytes and 0 < len(raw) <= MAX_MANIFEST_BYTES, "MANIFEST_BYTES_INVALID")
    value, _ = _decode(raw, canonical=True)
    _fields(value, ("schema", "lineage", "manifest_revision", "previous_manifest_sha256",
                    "segments_root_sha256", "coverage_root_sha256", "dependencies_root_sha256", "data_schema_sha256"))
    require(value["schema"] == "unified.storage.instrument-manifest.v1-review1", "MANIFEST_PROFILE_UNAVAILABLE")
    lineage = value["lineage"]
    _fields(lineage, ("schema", "cluster_id", "dataset_id", "source_id", "partition_id", "instrument_id", "data_kind"))
    require(lineage["schema"] == "unified.storage.manifest-lineage.v1-review1", "MANIFEST_LINEAGE_PROFILE_UNAVAILABLE")
    for key in ("cluster_id", "dataset_id"):
        _uuid(lineage[key])
    for key in ("source_id", "partition_id"):
        identifier(lineage[key])
    require(type(lineage["data_kind"]) is str and lineage["data_kind"] in _KINDS, "MANIFEST_KIND_UNAVAILABLE")
    instrument = lineage["instrument_id"]
    _fields(instrument, ("exchange", "category", "symbol", "instrument_version"))
    require(instrument["exchange"] == "bybit", "MANIFEST_INSTRUMENT_PROFILE_UNAVAILABLE")
    require(type(instrument["category"]) is str and instrument["category"] in ("linear", "spot", "inverse", "option"))
    require(type(instrument["symbol"]) is str and re.fullmatch(r"[A-Z0-9][A-Z0-9_-]{0,63}", instrument["symbol"]) is not None)
    u63(instrument["instrument_version"], positive=True)
    revision = u63(value["manifest_revision"], positive=True)
    previous = value["previous_manifest_sha256"]
    if revision == 1:
        require(previous is None, "MANIFEST_GENESIS_PREDECESSOR_INVALID")
    else:
        digest(previous)
    for key in ("segments_root_sha256", "coverage_root_sha256", "dependencies_root_sha256", "data_schema_sha256"):
        digest(value[key])
    return value


@dataclass(frozen=True)
class ManifestClaim:
    raw_bytes: bytes

    def __post_init__(self):
        _value(self.raw_bytes)

    def as_dict(self):
        return json.loads(self.raw_bytes)

    @property
    def sha256(self):
        return hashlib.sha256(self.raw_bytes).hexdigest()

    @property
    def lineage_sha256(self):
        raw = json.dumps(self.as_dict()["lineage"], sort_keys=True, separators=(",", ":")).encode("ascii")
        return hashlib.sha256(raw).hexdigest()

    @property
    def publication_confirmed(self):
        return False

    @property
    def closure_verified(self):
        return False

    def require_publication_authority(self):
        raise StorageBlocked("MANIFEST_AUTHORITY_ADAPTER_UNAVAILABLE")


def decode_manifest(raw):
    return ManifestClaim(raw)


def validate_manifest_successor(candidate, previous):
    """Untrusted predecessor relation only; no current authoritative head CAS."""
    require(type(candidate) is ManifestClaim, "MANIFEST_CLAIM_REQUIRED")
    value = candidate.as_dict()
    if previous is None:
        require(value["manifest_revision"] == "1" and value["previous_manifest_sha256"] is None,
                "MANIFEST_GENESIS_REQUIRED")
        return
    require(type(previous) is ManifestClaim, "MANIFEST_PREDECESSOR_REQUIRED")
    prior = previous.as_dict()
    require(value["lineage"] == prior["lineage"], "MANIFEST_LINEAGE_CHANGED")
    require(u63(value["manifest_revision"]) == u63(prior["manifest_revision"]) + 1,
            "MANIFEST_REVISION_NOT_SUCCESSOR")
    require(value["previous_manifest_sha256"] == previous.sha256, "MANIFEST_PREDECESSOR_MISMATCH")


def read_manifest_object(store, object_sha256):
    require(type(store) is ObjectStore, "OWNED_OBJECT_STORE_REQUIRED")
    return decode_manifest(store.read(object_sha256, max_bytes=MAX_MANIFEST_BYTES))
