"""Bounded, pure security planning. Input claims never grant host admission."""
import hashlib
import json
import re
from .module_catalog import MODULE_IDS

SCHEMA = "unified.windows-package-lock.v1"
SCHEMA_V2 = "unified.windows-package-lock.v2"
REQUIRED = {"python", "postgresql", "openssh", "tailscale", "service-wrapper"}
HEX = re.compile(r"[0-9a-f]{64}\Z")
SID = re.compile(r"S-1-5-(?:[0-9]+-)*[0-9]+\Z")


def _reject(message):
    raise ValueError(message)


def _path(value):
    if not isinstance(value, str) or len(value) > 240:
        _reject("invalid path")
    parts = value.split("/")
    if not parts or any(not re.fullmatch(r"[A-Za-z0-9_-][A-Za-z0-9_.-]*", p)
                        or p.endswith(".") or re.match(r"(?i)^(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])(?:\.|$)", p)
                        for p in parts):
        _reject("unsafe Windows path")
    return value


def validate_package_lock(lock, package_bytes):
    """Validate synthetic/offline supplied bytes; no signature or source authority claim."""
    if not isinstance(lock, dict) or type(lock.get("schema")) is not str or lock.get("schema") not in (SCHEMA, SCHEMA_V2):
        _reject("lock schema")
    if not isinstance(lock.get("identity_sid"), str) or not SID.fullmatch(lock["identity_sid"]):
        _reject("signed identity required")
    sources = lock.get("sources")
    expected_sources = set(MODULE_IDS) if lock["schema"] == SCHEMA_V2 else {"grid", "strattester", "unified", "terminan", "math"}
    if not isinstance(sources, dict) or set(sources) != expected_sources:
        _reject("exact source inventory")
    for source in sources.values():
        if not isinstance(source, dict) or set(source) != {"commit", "tree"} or any(not isinstance(v, str) or not re.fullmatch(r"[0-9a-f]{40}", v) for v in source.values()):
            _reject("exact commit/tree pins")
    requirements = lock.get("requirements")
    if (not isinstance(requirements, dict)
            or requirements != {"powershell": "5.1,7", "postgresql_major": 18}
            or type(requirements.get("postgresql_major")) is not int):
        _reject("PS5.1/7 and PostgreSQL18 required")
    artifacts = lock.get("artifacts")
    if not isinstance(artifacts, list) or not 1 <= len(artifacts) <= 32:
        _reject("bounded dependency inventory required")
    seen, names, total = set(), set(), 0
    for item in artifacts:
        if not isinstance(item, dict): _reject("artifact object required")
        path = _path(item.get("path"))
        name = item.get("dependency")
        if path.casefold() in seen or not isinstance(name, str) or name in names:
            _reject("duplicate path or dependency")
        seen.add(path.casefold()); names.add(name)
        digest, size = item.get("sha256"), item.get("bytes")
        if not isinstance(digest, str) or not HEX.fullmatch(digest): _reject("digest")
        if type(size) is not int or not 1 <= size <= 536870912: _reject("size")
        total += size
        if total > 1073741824: _reject("aggregate bytes")
        version, publisher = item.get("version"), item.get("publisher_sha256")
        if not isinstance(version, str) or not version or len(version) > 80: _reject("version")
        if name == "postgresql" and version.split(".")[0] != "18": _reject("PG18 package required")
        if not isinstance(publisher, str) or not HEX.fullmatch(publisher): _reject("package publisher pin")
        data = package_bytes.get(path)
        if not isinstance(data, bytes) or len(data) != size or hashlib.sha256(data).hexdigest() != digest:
            _reject("package bytes mismatch")
    if REQUIRED != names: _reject("dependency closure missing")
    if set(package_bytes) != {a["path"] for a in artifacts}: _reject("unexpected package bytes")
    return hashlib.sha256(json.dumps(lock, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def build_security_plan(lock, package_bytes, nodes):
    """PLAN_ONLY deltas from bounded untrusted observations, never executable commands.

    SignedCms verification is separate in SecurityPackage.psm1. Even verified
    signatures bind bytes to a supplied publisher pin, not independent owner trust.
    """
    digest = validate_package_lock(lock, package_bytes)
    if not isinstance(nodes, list) or len(nodes) > 64: _reject("fleet limit 64")
    ids, identities, plans = set(), set(), []
    for node in nodes:
        if not isinstance(node, dict): _reject("node object")
        node_id, identity = node.get("id"), node.get("identity_sid")
        if not isinstance(node_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", node_id): _reject("node id")
        if node_id.casefold() in ids or not isinstance(identity, str) or not SID.fullmatch(identity) or identity in identities:
            _reject("duplicate or invalid identity")
        ids.add(node_id.casefold()); identities.add(identity)
        installed = node.get("installed")
        if not isinstance(installed, dict) or not set(installed) <= REQUIRED: _reject("installed inventory")
        if any(not isinstance(v, str) or not HEX.fullmatch(v) for v in installed.values()): _reject("installed digest")
        blockers = [name for name in ("identity_verified", "publisher_pin_verified", "path_verified", "no_reparse", "acl_protected", "operator_approved") if node.get(name) is not True]
        desired = {a["dependency"]: a["sha256"] for a in lock["artifacts"]}
        changes = [{"dependency": k, "before_sha256": installed.get(k), "after_sha256": v,
                    "rollback": "RESTORE_PINNED_PREVIOUS_OR_REMOVE_NEW_AFTER_OPERATOR_APPROVAL"}
                   for k, v in sorted(desired.items()) if installed.get(k) != v]
        plans.append({"id": node_id, "identity_sid": identity, "status": "BLOCKED" if blockers else "PLAN_READY",
                      "blockers": blockers, "deltas": changes,
                      "enrollment": "PER_NODE_SINGLE_USE_SHORT_LIVED_OPERATOR_APPROVED_IDENTITY",
                      "service_account": "DEDICATED_NON_ADMIN_NO_INTERACTIVE_LOGON_LEAST_PRIVILEGE",
                      "tailscale": "OWNER_MANAGED_TAGS_WITH_EXPLICIT_POLICY_APPROVAL",
                      "rollback_requires": "PINNED_PREVIOUS_PACKAGE_AND_BACKUP_RESTORE_ACCEPTANCE"})
    return {"mode": "PLAN_ONLY", "lock_sha256": digest, "nodes": plans, "mutations_performed": False,
            "software": "MODEL_ONLY", "source_provenance": "NOT_EVALUATED", "physical": "NOT_RUN",
            "production": "NO_GO", "admission": "NOT_GRANTED", "secrets_collected": False}
