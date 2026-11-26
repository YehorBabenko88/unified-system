"""Non-actuating LAB-only Root → C PostgreSQL fence compatibility assessment.

All external calls must use Root-owned sealed authority objects and C-owned
PostgreSQL owner APIs. The result is diagnostic *only* and is never a service,
SQL, source, trading or native startup grant. No new Consul or writer client.
"""
import inspect
from dataclasses import dataclass

from .grid_writer_fence_model import (
    ResourceFenceBlocked, WriterLeaseIdentity, _need,
)
from .market_data_entry_contract import (
    APPROVED_GRID_COMMIT, GRID_REPOSITORY, V2_ENTRY, entry_for_manifest,
)

SCHEMA = "unified.grid-writer-lab-bridge.v1"
SCOPE = "ISOLATED_LAB_ONLY"
C_FENCE_SCHEMA = "lab-postgres-fenced-custody.v1"
_RESOURCE = "grid-market-data-primary"


@dataclass(frozen=True)
class LabFenceAssessment:
    schema: str
    scope: str
    code: str
    source_commit: str
    resource_id: str
    native_admitted: bool = False

    def __post_init__(self):
        _need(self.schema == SCHEMA and self.scope == SCOPE)
        _need(type(self.code) is str and self.code in (
            "LAB_EVIDENCE_VALIDATED_NOT_NATIVE",
            "LAB_CUSTODY_UNVERIFIED",
            "LAB_QUIESCENCE_UNVERIFIED",
            "LAB_CONSUL_LEASE_UNVERIFIED"))
        _need(self.source_commit == APPROVED_GRID_COMMIT)
        _need(self.resource_id == _RESOURCE)
        _need(self.native_admitted is False)


def _require_native_owner_contract(authority, lease, source, manifest,
                                   identity, generation, owner,
                                   legacy_witness, pg, c_module):
    """Validate cross-owner types without trusting user-supplied JSON receipts."""
    _need(source is not None and callable(getattr(source, "require_current", None)),
          "LAB_SOURCE_ADMISSION_REQUIRED")
    _need(source.require_current() is True, "LAB_SOURCE_REVOKED")
    _need(type(manifest) is dict and entry_for_manifest(manifest) == V2_ENTRY,
          "LAB_GRID_SOURCE_REJECTED")
    market = manifest["sources"]["market_data"]
    _need(market["repository"] == GRID_REPOSITORY
          and market["commit"] == APPROVED_GRID_COMMIT,
          "LAB_GRID_SOURCE_REJECTED")
    _need(type(identity) is WriterLeaseIdentity,
          "LAB_WRITER_IDENTITY_REJECTED")
    _need(identity.owner == lease.owner
          and identity.namespace == authority.config.namespace
          and identity.session_id == lease.session_id
          and identity.token == lease.token,
          "LAB_CONSUL_IDENTITY_REJECTED")
    _need(type(generation) is int and 1 <= generation < 2**63,
          "LAB_GENERATION_REJECTED")
    _need(owner is not None and callable(getattr(owner, "_verify_owned", None))
          and callable(getattr(owner, "_verify_postmaster", None))
          and hasattr(owner, "started"),
          "LAB_PG_OWNER_REQUIRED")
    # A witness object must implement an actual native assessment; a boolean
    # supplied by a caller, signed JSON or a passed-in PID list is NOT proof.
    _need(legacy_witness is not None
          and callable(getattr(legacy_witness, "require_current", None))
          and callable(getattr(legacy_witness, "confirmed_quiescent", None)),
          "LAB_QUIESCENCE_WITNESS_REQUIRED")
    _need(pg is owner, "LAB_PG_OWNER_INSTANCE_MISMATCH")
    _need(c_module is not None
          and callable(getattr(c_module, "fenced_lab_witness", None))
          and callable(getattr(c_module, "fence_identity", None)),
          "LAB_C_CANONICAL_FENCE_REQUIRED")


async def assess_lab_c_fence(*, authority, lease, source, manifest, identity,
                             generation, pg, c_module, legacy_witness):
    """Read-only multi-owner assessment; even positive result cannot start.

    Caller must independently supply protected Root objects: do not accept
    strings/JSON as a lease, process witness, source grant or database owner.
    The assessment intentionally does not invoke C claim_lab_fence(), modify
    PG roles/tables, create leases, kill workers or mutate instance state.
    """
    try:
        from .consul_authority import ConsulLease, ConsulSessionAuthority
        _need(type(authority) is ConsulSessionAuthority
              and type(lease) is ConsulLease,
              "LAB_CONSUL_AUTHORITY_REQUIRED")
        _require_native_owner_contract(authority, lease, source, manifest,
                                       identity, generation, pg,
                                       legacy_witness, pg, c_module)
        _need(await authority.validate(lease) is True,
              "LAB_CONSUL_LEASE_UNVERIFIED")
        _need(source.require_current() is True, "LAB_SOURCE_REVOKED")
        _need(legacy_witness.require_current() is True
              and legacy_witness.confirmed_quiescent() is True,
              "LAB_QUIESCENCE_UNVERIFIED")
        _need(pg._verify_owned() is None, "LAB_PG_OWNER_UNVERIFIED")
        _need(pg.started is True, "LAB_PG_NOT_STARTED")
        _need(pg._verify_postmaster() is None, "LAB_PG_POSTMASTER_UNVERIFIED")
        fence=c_module.fence_identity()
        _need(type(fence) is dict
              and fence.get("schema") == "lab-postgres-writer-fence.v1"
              and fence.get("resource_id") == _RESOURCE
              and fence.get("scope") == SCOPE
              and fence.get("execution_authority") is False
              and fence.get("native_admission") is False,
              "LAB_C_FENCE_ABI_REJECTED")
        witness=c_module.fenced_lab_witness(pg)
        _need(type(witness) is dict
              and witness.get("schema") == C_FENCE_SCHEMA
              and witness.get("scope") == SCOPE
              and witness.get("direct_writer_insert") is False
              and witness.get("writer_exec") is True
              and witness.get("reader_exec") is False
              and witness.get("execution_authority") is False
              and witness.get("trading_authorized") is False,
              "LAB_C_CUSTODY_UNVERIFIED")
        # The window between two reads is not an atomic native grant. This is
        # for diagnosis only; real admission needs owner-controlled lifecycle
        # and a C transaction acquired under the same Root authority.
        _need(source.require_current() is True
              and legacy_witness.require_current() is True
              and await authority.validate(lease) is True,
              "LAB_LEASE_CHANGED_DURING_ASSESSMENT")
    except ResourceFenceBlocked:
        raise
    except Exception:
        raise ResourceFenceBlocked("LAB_FENCE_ASSESSMENT_REJECTED") from None
    return LabFenceAssessment(SCHEMA,SCOPE,"LAB_EVIDENCE_VALIDATED_NOT_NATIVE",
                              APPROVED_GRID_COMMIT,_RESOURCE)


def native_writer_admission(*_args, **_kwargs):
    """No callable Lab assessment may be used to grant native startup."""
    raise ResourceFenceBlocked("NATIVE_DB_FENCE_NOT_ADMITTED")
