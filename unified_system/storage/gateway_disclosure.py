"""Synthetic Gateway manifest boundary with an exact disposable owner binding.

Pure request validation never grants disclosure. ROOT must load/commission the
exact admitted A2 module, actual mTLS authority and same store before invocation.
No provider callback, registry or public capability minting is exposed here.
"""
from dataclasses import dataclass
import hashlib
import importlib.machinery
import json
from pathlib import Path
import stat
import sys
import types

from .contracts import StorageBlocked, _UUID, _decode, digest, require, u63
from .manifest import decode_manifest
from .object_store import ObjectStore

MAX_REQUEST_BYTES = 16384
MANIFEST_SCHEMA_SHA256 = "a599b399cb8809ad72a2ecdb778a4e7e419f88a6cadcf2da20489cf93d12fd10"
TOOL_NAME = "unified.get_dataset_manifest"
IDENTITY_MODULE = "unified_system.gateway_identity"
IDENTITY_SOURCE_SHA256 = "84093865e8477ef6562100d41137922785446c9cb4e024c9ba7105593a2b36c1"
MAX_OUTPUT_BYTES = 32768


class DisclosureUnavailable(RuntimeError):
    """Closed failure, no reflected arguments or private store information."""


class DisclosureInvalid(ValueError):
    """Pure request syntax failure; not a disclosure or authentication result."""


def _request(raw):
    try:
        require(type(raw) is bytes and 0 < len(raw) <= MAX_REQUEST_BYTES)
        value, _ = _decode(raw, canonical=True)
        require(set(value) == {"schema", "request_id", "dataset_id", "dataset_revision", "manifest_revision",
                               "manifest_sha256", "manifest_schema_sha256", "consumer_id", "view_id"})
        require(value["schema"] == "unified.storage.gateway-manifest-request.v1-review2")
        for name in ("request_id", "dataset_id", "consumer_id", "view_id"):
            require(type(value[name]) is str and _UUID.fullmatch(value[name]) is not None)
        for name in ("dataset_revision", "manifest_revision"):
            u63(value[name], positive=True)
        digest(value["manifest_sha256"])
        digest(value["manifest_schema_sha256"])
        require(value["manifest_schema_sha256"] == MANIFEST_SCHEMA_SHA256)
        return value
    except StorageBlocked:
        raise DisclosureInvalid("INVALID_GATEWAY_MANIFEST_REQUEST") from None


@dataclass(frozen=True)
class ManifestReadRequest:
    raw_bytes: bytes

    def __post_init__(self):
        _request(self.raw_bytes)

    def as_dict(self):
        return json.loads(self.raw_bytes)

    @property
    def request_sha256(self):
        return hashlib.sha256(self.raw_bytes).hexdigest()

    @property
    def binding(self):
        value = self.as_dict()
        return dict(schema="unified.gateway.read-binding.v1-review2", dataset_id=value["dataset_id"],
                    dataset_revision=value["dataset_revision"], manifest_sha256=value["manifest_sha256"],
                    schema_sha256=value["manifest_schema_sha256"], consumer_id=value["consumer_id"], view_id=value["view_id"])

    @property
    def disclosure_authorized(self):
        return False


def prepare_manifest_request(request_bytes):
    return ManifestReadRequest(request_bytes)


def _owner_api():
    """Check ROOT's already-loaded canonical source; never import caller code.

    ROOT must additionally qualify the complete source/dependency capsule before
    imports. This is not a sandbox against hostile Python in the owner process.
    """
    try:
        module = sys.modules.get(IDENTITY_MODULE)
        require(type(module) is types.ModuleType)
        namespace = vars(module)
        filename, spec, loader = (namespace.get(key) for key in ("__file__", "__spec__", "__loader__"))
        require(type(filename) is str and type(spec) is importlib.machinery.ModuleSpec)
        require(type(loader) is importlib.machinery.SourceFileLoader and spec.loader is loader
                and spec.name == IDENTITY_MODULE and spec.origin == filename)
        path = Path(filename)
        require(path.is_absolute() and path.suffix == ".py")
        before = path.lstat()
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                and not (getattr(before, "st_file_attributes", 0) & 1024))
        require(before.st_size == 15283)
        source = path.read_bytes()
        after = path.lstat()
        require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns))
        require(hashlib.sha256(source).hexdigest() == IDENTITY_SOURCE_SHA256)
        authority, capability = (namespace.get(key) for key in ("DisposableIdentityAuthority", "GatewayReadCapability"))
        require(type(authority) is type and type(capability) is type
                and authority.__module__ == IDENTITY_MODULE and capability.__module__ == IDENTITY_MODULE)
        method = vars(authority).get("require_issued_read")
        require(type(method) is types.FunctionType and method.__module__ == IDENTITY_MODULE
                and Path(method.__code__.co_filename).resolve() == path.resolve())
        return authority, capability, method
    except Exception:
        raise DisclosureUnavailable("GATEWAY_READ_CAPABILITY_SOURCE_UNAVAILABLE") from None


def _current(api, authority, capability, request, store):
    try:
        result = api[2](authority, capability, tool_name=TOOL_NAME, request_bytes=request.raw_bytes,
                        binding=request.binding, owned_store=store)
        if result is not None:
            raise DisclosureUnavailable("GATEWAY_READ_CAPABILITY_RESULT_UNAVAILABLE")
    except Exception:
        # Do not reflect private authority/profile/certificate/store details.
        # Never run, close or schedule an unsupported returned awaitable.
        raise DisclosureUnavailable("GATEWAY_MANIFEST_DISCLOSURE_DENIED") from None


def get_dataset_manifest(request_bytes, *, owner_read_capability, expected_identity_authority, pinned_owned_store):
    api = _owner_api()
    if (type(expected_identity_authority) is not api[0] or type(owner_read_capability) is not api[1]
            or type(pinned_owned_store) is not ObjectStore):
        raise DisclosureUnavailable("GATEWAY_MANIFEST_DISCLOSURE_DENIED")
    try:
        request = prepare_manifest_request(request_bytes)
    except DisclosureInvalid:
        raise DisclosureUnavailable("GATEWAY_MANIFEST_DISCLOSURE_DENIED") from None
    _current(api, expected_identity_authority, owner_read_capability, request, pinned_owned_store)
    try:
        target = request.as_dict()
        raw = ObjectStore.read(pinned_owned_store, target["manifest_sha256"], max_bytes=16384)
        manifest = decode_manifest(raw)
        value = manifest.as_dict()
        require(manifest.sha256 == target["manifest_sha256"] and value["lineage"]["dataset_id"] == target["dataset_id"]
                and value["manifest_revision"] == target["manifest_revision"], "MANIFEST_BINDING_MISMATCH")
        response = dict(schema="unified.storage.gateway-manifest-disclosure.v1-review1",
            status="SYNTHETIC_MANIFEST_DISCLOSED", request_id=target["request_id"], request_sha256=request.request_sha256,
            authentication="SYNTHETIC_SESSION_AUTHENTICATED_ONLY", native_authenticated=False,
            access_scope=dict(tool_name=TOOL_NAME, consumer_id=target["consumer_id"], view_id=target["view_id"],
                              mode="SYNTHETIC_DISPOSABLE_STORE_ONLY"),
            dataset_id=target["dataset_id"], dataset_revision=target["dataset_revision"],
            dataset_revision_scope="LOCAL_SYNTHETIC_RESOURCE_REVISION", manifest_revision=value["manifest_revision"],
            manifest_revision_scope="LOCAL_UNCOMMITTED_MANIFEST_REVISION", manifest_sha256=manifest.sha256,
            manifest_schema_sha256=MANIFEST_SCHEMA_SHA256, manifest=value, coverage="UNKNOWN", gaps="UNKNOWN",
            publication="UNPROVEN", committed_dataset_revision=None, registry="UNPROVEN",
            source="SYNTHETIC_DISPOSABLE_RESOURCE_NOT_SOURCE_ATTESTATION",
            integrity="LOCAL_HASH_MATCHED_NOT_REPLICA_VERIFIED", closure_verified=False)
        output = json.dumps(response, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")
        require(len(output) <= MAX_OUTPUT_BYTES, "DISCLOSURE_OUTPUT_BOUND")
    except Exception:
        raise DisclosureUnavailable("GATEWAY_MANIFEST_CONTENT_UNAVAILABLE") from None
    _current(api, expected_identity_authority, owner_read_capability, request, pinned_owned_store)
    return output
