"""Non-actuating LAB-only Root → C PostgreSQL fence compatibility assessment.

All external calls must use Root-owned sealed authority objects and C-owned
PostgreSQL owner APIs. The result is diagnostic *only* and is never a service,
SQL, source, trading or native startup grant. No new Consul or writer client.
"""
import hashlib
from pathlib import Path
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



# C's tested native source digest is SHA256(path + NUL + verified bytes + NUL)
# over four exact installed SDK modules. Its schema digest is SHA256 of the
# protected Grid migrations module. These are not wheel-publisher attestations.
_CANONICAL_DIGEST_FILES = (
    "market_data/provenance.py",
    "market_data/history_api.py",
    "market_data_v2/qualified_read_contract.py",
    "market_data_v2/read_api.py",
)
_SCHEMA_DIGEST_FILE = "grid/migrations.py"


def verified_grid_source_digests(source, manifest, source_root):
    """Read source-owned, manifest-hashed LAB files; never accept supplied SHA."""
    from .lab_release import regular
    _need(callable(getattr(source, "require_current", None))
          and callable(getattr(source, "source_scope", None)),
          "LAB_SOURCE_ADMISSION_REQUIRED")
    _need(type(manifest) is dict and type(manifest.get("files")) is dict,
          "LAB_SOURCE_MANIFEST_REQUIRED")
    _need(source.require_current() is True, "LAB_SOURCE_REVOKED")
    try:
        root=Path(source_root).resolve(strict=True)
        approved=source.source_scope("market_data",root,APPROVED_GRID_COMMIT)
        _need(Path(approved).resolve(strict=True)==root,
              "LAB_SOURCE_ROOT_NOT_ADMITTED")
        def read(rel):
            name="sources/market_data/"+rel
            pin=manifest["files"].get(name)
            _need(type(pin) is dict and set(pin)=={"sha256","bytes"}
                  and type(pin["sha256"]) is str
                  and type(pin["bytes"]) is int and 0<pin["bytes"]<=8*1024*1024,
                  "LAB_SOURCE_FILE_PIN_REQUIRED")
            path=regular(root/rel)
            raw=path.read_bytes()
            _need(len(raw)==pin["bytes"]
                  and hashlib.sha256(raw).hexdigest()==pin["sha256"],
                  "LAB_SOURCE_FILE_CHANGED")
            return raw
        digest=hashlib.sha256()
        for rel in _CANONICAL_DIGEST_FILES:
            digest.update(rel.encode("ascii")+b"\0"+read(rel)+b"\0")
        schema=hashlib.sha256(read(_SCHEMA_DIGEST_FILE)).hexdigest()
        _need(source.require_current() is True, "LAB_SOURCE_REVOKED")
        return digest.hexdigest(),schema
    except ResourceFenceBlocked:
        raise
    except Exception:
        raise ResourceFenceBlocked("LAB_SOURCE_DIGEST_NOT_ATTESTED") from None


# Only a declared, source-verified, explicitly enumerated B Grid adapter may
# participate in a later combined Root/C writer acceptance. The adapter lives
# outside the Market Data wheel and is NOT imported or run here.
GRID_WRITER_PATH = "grid/canonical_lab_fenced_writer.py"
GRID_WRITER_COMMIT = "3265d441717f2bc01b82e759b5d8df06cb516fa4"
GRID_WRITER_BLOB = "8b93466a79fa234468a3cdc44106bd5e153e81c4"


def verified_grid_writer_adapter_pin(source, manifest, source_root):
    """Verify B adapter bytes and exact installed source tree cohort.

    The present `entry_for_manifest` is frozen to the older approved B read
    cohort. This function refuses implicit relabeling of the new writer: a
    future combined LAB manifest must explicitly carry its NEW B commit.
    Always diagnostic; never enough to authorize execution.
    """
    _need(type(manifest) is dict and type(manifest.get("sources")) is dict
          and type(manifest.get("files")) is dict,
          "LAB_GRID_WRITER_PIN_MISSING")
    src=manifest["sources"].get("market_data")
    _need(type(src) is dict and src.get("repository") == GRID_REPOSITORY
          and src.get("commit") == GRID_WRITER_COMMIT,
          "LAB_GRID_WRITER_COHORT_NOT_PINNED")
    path="sources/market_data/"+GRID_WRITER_PATH
    pin=manifest["files"].get(path)
    _need(type(pin) is dict and set(pin)=={"sha256","bytes"}
          and type(pin["sha256"]) is str and len(pin["sha256"])==64
          and type(pin["bytes"]) is int and 0<pin["bytes"]<=1024*1024,
          "LAB_GRID_WRITER_PIN_MISSING")
    _need(source.require_current() is True,
          "LAB_SOURCE_REVOKED")
    try:
        from .lab_release import regular
        root=Path(source_root).resolve(strict=True)
        selected=source.source_scope(
            "market_data",root,GRID_WRITER_COMMIT)
        _need(Path(selected).resolve(strict=True)==root,
              "LAB_GRID_WRITER_ROOT_REJECTED")
        import hashlib
        raw=regular(root/GRID_WRITER_PATH).read_bytes()
        _need(len(raw)==pin["bytes"]
              and hashlib.sha256(raw).hexdigest()==pin["sha256"],
              "LAB_GRID_WRITER_BYTES_CHANGED")
        _need(source.require_current() is True,
              "LAB_SOURCE_REVOKED")
        return {
            "schema":"unified.grid-canonical-lab-writer-pin.v1",
            "source_commit":GRID_WRITER_COMMIT,
            "git_blob_sha1":GRID_WRITER_BLOB,
            "relative_path":GRID_WRITER_PATH,
            "file_sha256":pin["sha256"],
            "size_bytes":pin["bytes"],
            "native_admitted":False,
            "trading_authorized":False,
        }
    except ResourceFenceBlocked:
        raise
    except Exception:
        raise ResourceFenceBlocked(
            "LAB_GRID_WRITER_BYTES_NOT_ATTESTED") from None


def _require_native_owner_contract(authority, lease, source, manifest,
                                   identity, generation,
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
    _need(pg is not None and callable(getattr(pg, "_verify_owned", None))
          and callable(getattr(pg, "_verify_postmaster", None))
          and hasattr(pg, "started"),
          "LAB_PG_OWNER_REQUIRED")
    # A witness object must implement an actual native assessment; a boolean
    # supplied by a caller, signed JSON or a passed-in PID list is NOT proof.
    _need(legacy_witness is not None
          and callable(getattr(legacy_witness, "require_current", None))
          and callable(getattr(legacy_witness, "confirmed_quiescent", None)),
          "LAB_QUIESCENCE_WITNESS_REQUIRED")
    _need(c_module is not None
          and callable(getattr(c_module, "fenced_lab_witness", None))
          and callable(getattr(c_module, "fence_identity", None))
          and callable(getattr(c_module, "revalidate_lab_fence", None)),
          "LAB_C_CANONICAL_FENCE_REQUIRED")


async def assess_lab_c_fence(*, authority, lease, source, manifest, identity,
                             generation, pg, c_module, legacy_witness,
                             source_root, backend_pid):
    """Read-only multi-owner assessment; even positive result cannot start.

    Caller must independently supply protected Root objects: do not accept
    strings/JSON as a lease, process witness, source grant or database owner.
    The assessment intentionally does not invoke C claim_lab_fence(), modify
    PG roles/tables, create leases, kill workers or mutate instance state.
    """
    try:
        from .consul_authority import ConsulLease, ConsulSessionAuthority
        _need(type(backend_pid) is int and 1<backend_pid<2**31,
              "LAB_WRITER_BACKEND_PID_REQUIRED")
        _need(type(authority) is ConsulSessionAuthority
              and authority.config.isolated_lab is True
              and type(lease) is ConsulLease,
              "LAB_CONSUL_AUTHORITY_REQUIRED")
        _require_native_owner_contract(authority, lease, source, manifest,
                                       identity, generation,
                                       legacy_witness, pg, c_module)
        actual_source,actual_schema=verified_grid_source_digests(
            source,manifest,source_root)
        _need(identity.source_sha256==actual_source
              and identity.schema_sha256==actual_schema,
              "LAB_WRITER_DIGEST_NOT_SOURCE_BOUND")
        _need(await authority.validate(lease) is True,
              "LAB_CONSUL_LEASE_UNVERIFIED")
        _need(source.require_current() is True, "LAB_SOURCE_REVOKED")
        _need(legacy_witness.require_current() is True
              and legacy_witness.confirmed_quiescent() is True,
              "LAB_QUIESCENCE_UNVERIFIED")
        _need(pg._verify_owned() is None, "LAB_PG_OWNER_UNVERIFIED")
        _need(pg.started is True, "LAB_PG_NOT_STARTED")
        postmaster=pg._verify_postmaster()
        _need(type(postmaster) is int and postmaster>1,
              "LAB_PG_POSTMASTER_UNVERIFIED")
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
              and witness.get("fence_writer_select") is False
              and witness.get("fence_writer_update") is False
              and witness.get("fence_reader_select") is False
              and witness.get("function_owner") == "lab_owner"
              and witness.get("function_security_definer") is True
              and witness.get("function_search_path_pinned") is True
              and witness.get("fence_owner") == "lab_owner"
              and type(witness.get("fence_state_count")) is int
              and 0 <= witness["fence_state_count"] <= 1
              and witness.get("schema") == C_FENCE_SCHEMA
              and witness.get("scope") == SCOPE
              and witness.get("direct_writer_insert") is False
              and witness.get("writer_exec") is True
              and witness.get("reader_exec") is False
              and witness.get("execution_authority") is False
              and witness.get("trading_authorized") is False,
              "LAB_C_CUSTODY_UNVERIFIED")
        # C's actual owner-side revalidation binds generation to the current
        # original DB backend + backend_start. Never trust a caller JSON token.
        receipt=c_module.revalidate_lab_fence(
            pg,identity=identity,generation=generation,backend_pid=backend_pid)
        expected={
            "schema":"lab-postgres-fence-revalidation.v1",
            "scope":SCOPE,"resource_id":_RESOURCE,
            "generation":generation,"token":identity.token,
            "backend_pid":backend_pid,"owner":identity.owner,
            "namespace":identity.namespace,
            "session_id":identity.session_id,
            "instance_id":identity.instance_id,
            "node_incarnation_id":identity.node_incarnation_id,
            "source_sha256":actual_source,
            "schema_sha256":actual_schema,
            "db_backend_observed":True,"db_fence_current_at_read":True,
            "root_consul_admitted":False,
            "host_old_process_quiescence_attested":False,
            "native_writer_admitted":False,"paper_admitted":False,
            "execution_authority":False,"trading_authorized":False,
        }
        _need(type(receipt) is dict and receipt==expected,
              "LAB_C_FENCE_REVALIDATION_REJECTED")
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


# E Round19: one exact B9e0 writer+collector+adapter+async-factory cohort.
# These are Git source blob identity pins only. The Root must independently
# authenticate source release, built wheel, installation, imports, entrypoint
# and original SQL worker; issue_operation_permit() remains DENIED meanwhile.
# Historical B3265 adapter pin above is intentionally left unchanged.
GRID_RUNTIME_LAB_SHA = "9e0d57c4c0f2d01bc381ada090b62d23566b32aa"
_GRID_RUNTIME_BLOBS = {
    "grid/canonical_lab_fenced_writer.py":
        "247d7fab2738e1892a05979e407f637f9df62784",
    "grid/canonical_lab_continuous_collector.py":
        "873e83839bee9ceb1cca710a5291ba2cf5f7f038",
    "grid/c_lab_journal_adapter.py":
        "ab93c6d421c3d3f0232060f6ded7ac01bf8eeda0",
    "grid/c_async_fenced_writer.py":
        "35bf202bb1674238d53b74f962af966d2a699fa2",
}


def verified_grid_runtime_cohort_pin(source, manifest, source_root):
    """Verify four exact B continuous LAB source files, no code import.

    This contract pins the complete four-file LAB writer cohort only.
    Protected release/wheel, package selection and entrypoint are independent
    mandatory gates; absence of any of those is NOT a full bundle acceptance.
    The protected Root capsule must separately verify all source/wheel files.
    Git object hashes here are repository evidence, not publisher signatures.
    This does not create SQL, lease, child, trading or native admission.
    """
    _need(type(manifest) is dict
          and type(manifest.get("sources")) is dict
          and type(manifest.get("files")) is dict,
          "LAB_GRID_RUNTIME_MANIFEST_REQUIRED")
    m=manifest["sources"].get("market_data")
    _need(type(m) is dict and m.get("repository") == GRID_REPOSITORY
          and m.get("commit") == GRID_RUNTIME_LAB_SHA
          and m.get("root") == "sources/market_data",
          "LAB_GRID_RUNTIME_COHORT_REJECTED")
    _need(callable(getattr(source, "require_current", None))
          and callable(getattr(source, "source_scope", None))
          and source.require_current() is True,
          "LAB_GRID_RUNTIME_SOURCE_REVOKED")
    try:
        from .lab_release import regular
        root=Path(source_root).resolve(strict=True)
        approved=source.source_scope("market_data",root,GRID_RUNTIME_LAB_SHA)
        _need(Path(approved).resolve(strict=True)==root,
              "LAB_GRID_RUNTIME_ROOT_REJECTED")
        pins={}
        for relative,expected_blob in _GRID_RUNTIME_BLOBS.items():
            file_key="sources/market_data/"+relative
            pin=manifest["files"].get(file_key)
            _need(type(pin) is dict and set(pin)=={"sha256","bytes"}
                  and type(pin["sha256"]) is str
                  and len(pin["sha256"])==64
                  and type(pin["bytes"]) is int
                  and 0<pin["bytes"]<=8*1024*1024,
                  "LAB_GRID_RUNTIME_FILE_PIN_REQUIRED")
            raw=regular(root/relative).read_bytes()
            _need(len(raw)==pin["bytes"]
                  and hashlib.sha256(raw).hexdigest()==pin["sha256"],
                  "LAB_GRID_RUNTIME_SOURCE_CHANGED")
            actual_blob=hashlib.sha1(
                b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()
            _need(actual_blob==expected_blob,
                  "LAB_GRID_RUNTIME_BLOB_MISMATCH")
            pins[relative]={"git_blob_sha1":actual_blob,
                            "sha256":pin["sha256"],"bytes":pin["bytes"]}
        _need(source.require_current() is True,
              "LAB_GRID_RUNTIME_SOURCE_REVOKED")
        return {"schema":"unified.grid-lab-runtime-cohort.v1",
                "scope":SCOPE,
                "source_commit":GRID_RUNTIME_LAB_SHA,
                "verified_files":pins,
                "native_admitted":False,
                "trading_authorized":False}
    except ResourceFenceBlocked:
        raise
    except Exception:
        raise ResourceFenceBlocked("LAB_GRID_RUNTIME_NOT_ATTESTED") from None
