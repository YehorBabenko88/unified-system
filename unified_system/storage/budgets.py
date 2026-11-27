"""Local untrusted reservation arithmetic fixture, NOT an issued-record codec.

This model deliberately cannot validate native indices, provenance or permission.
Exact native producer schemas and proof adapter are separate pending contracts.
"""
from dataclasses import dataclass
import hashlib
import json

from .contracts import _UUID, digest, require, u63


@dataclass(frozen=True)
class ReservationObservation:
    local_facts_sha256: str

    @property
    def publication_authorized(self):
        return False

    @property
    def native_proof_verified(self):
        return False


def _fields(value, fields):
    require(type(value) is dict and all(type(k) is str for k in value)
            and set(value) == set(fields), "RESERVATION_FACT_FIELDS_INVALID")


def validate_reservation_binding(facts):
    """Check only closed fixture roles/arithmetic; never grant an effect.

    Facts are proposed local observations, not the four native schema candidates.
    Their hashes cannot replace actual source/issuer/native proof verification.
    """
    _fields(facts, ("issuance", "current", "accounting", "requested_bytes"))
    issued, current, accounting = facts["issuance"], facts["current"], facts["accounting"]
    _fields(issued, ("reservation_id", "scope_sha256", "grant_sha256", "issuance_budget_revision", "policy_revision", "granted_bytes"))
    _fields(current, ("reservation_revision", "state", "remaining_bytes", "issuance_sha256", "delegation_sha256"))
    _fields(accounting, ("usage_revision", "used_bytes", "reserved_bytes", "limit_bytes"))
    require(type(issued["reservation_id"]) is str and _UUID.fullmatch(issued["reservation_id"]) is not None)
    for field in ("scope_sha256", "grant_sha256"):
        digest(issued[field])
    for field in ("issuance_sha256", "delegation_sha256"):
        digest(current[field])
    for field in ("issuance_budget_revision", "policy_revision", "granted_bytes"):
        u63(issued[field], positive=True)
    u63(current["reservation_revision"], positive=True)
    u63(accounting["usage_revision"], positive=True)
    require(type(current["state"]) is str and current["state"] in ("RESERVED", "DRAINING"), "OWN_RESERVATION_NOT_ELIGIBLE")
    remaining = u63(current["remaining_bytes"])
    requested = u63(facts["requested_bytes"], positive=True)
    require(requested <= remaining <= u63(issued["granted_bytes"]), "RESERVATION_EXHAUSTED")
    used, reserved, limit = (u63(accounting[field]) for field in ("used_bytes", "reserved_bytes", "limit_bytes"))
    require(used + reserved <= limit and remaining <= reserved, "ACCOUNTING_CAPACITY_INVALID")
    raw = json.dumps(facts, sort_keys=True, separators=(",", ":")).encode("ascii")
    return ReservationObservation(hashlib.sha256(b"untrusted-reservation-fixture.v1\x00" + raw).hexdigest())
