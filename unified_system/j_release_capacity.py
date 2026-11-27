"""Read-only native Windows V2 receipt budget projection.

This is a preflight, not installation, manifest authentication, Win32 identity
proof, or authority to grant service registration and/or physical deletion.
Inputs MUST be independently authenticated by lab_release.parse_manifest.
"""
from pathlib import PureWindowsPath
from . import lab_release

MAX_HANDLES = 512
MAX_ESTIMATED_BYTES = 56000
MAX_RECEIPT_BYTES = 60000
MAX_KEY_LEN = 300


def _path_parts(relative):
    lab_release.relative(relative)
    return PureWindowsPath(*relative.split("/")).parts


def project_native_roster(manifest, *, install_ancestor_count):
    """Return exact deterministic key roster count and conservative byte budget.

    No OS access; installation root/ancestor count is supplied from the intended
    Windows target. Refuse invalid or unverifiable manifests before installation.
    """
    lab_release.need(type(manifest) is dict)
    files = manifest.get("files")
    dirs = manifest.get("directories")
    lab_release.need(type(files) is dict and type(dirs) is list)
    lab_release.need(type(install_ancestor_count) is int and 0 <= install_ancestor_count <= 64)
    lab_release.need("lab-release.json" not in files)
    lab_release.need(len(files) == len(set(files)) and len(dirs) == len(set(dirs)))
    lab_release.need(all(type(x) is str for x in files) and all(type(x) is str for x in dirs))
    keys = {"root", "code", "ownership", "state", "ownership:service.sqlite", "file:lab-release.json"}
    keys.update("ancestor:" + str(i) for i in range(install_ancestor_count))
    for name in files:
        parts = _path_parts(name)
        keys.add("file:" + name)
        for i in range(1, len(parts)):
            keys.add("parent:" + "/".join(parts[:i]))
    for name in dirs:
        parts = _path_parts(name)
        keys.add("directory:" + name)
        for i in range(1, len(parts)):
            keys.add("parent:" + "/".join(parts[:i]))
    lab_release.need(len(keys) == len(set(keys)))
    lab_release.need(all(0 < len(k) <= MAX_KEY_LEN for k in keys))
    estimate = sum(112 + len(key.encode("utf-8")) for key in keys)
    return {"identity_count": len(keys), "estimated_receipt_bytes": estimate,
            "max_identities": MAX_HANDLES, "max_estimated_bytes": MAX_ESTIMATED_BYTES,
            "max_canonical_receipt_bytes": MAX_RECEIPT_BYTES,
            "admissible_by_conservative_preflight":
                len(keys) <= MAX_HANDLES and estimate <= MAX_ESTIMATED_BYTES}


def evaluate_manifest(raw, expected_sha256, *, install_ancestor_count):
    """Only a verified, canonical source manifest may reach the budget model."""
    manifest = lab_release.parse_manifest(raw, expected_sha256)
    result = project_native_roster(manifest, install_ancestor_count=install_ancestor_count)
    result["manifest_sha256"] = expected_sha256
    result["schema"] = manifest["schema"]
    result["actual_canonical_receipt_bytes"] = None
    result["physical_acceptance"] = "NOT_RUN"
    result["installer_authorization"] = False
    return result
