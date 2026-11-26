"""F-owned offline wheel/installation byte audit, NEVER an authorization issuer.

Checks externally pinned wheel source bytes against the *current* installation.
This read-only, potentially racy check does not authenticate a release, prove the
running process's import provenance, or grant Root/Consul/SQL privileges.
"""
from __future__ import annotations

import base64
import configparser
import csv
import hashlib
import io
import pathlib
import re
import stat
import unicodedata
import zipfile
from email.parser import Parser

_MAX_ARCHIVE_ENTRIES = 10000
_MAX_ARCHIVE_BYTES = 256 * 1024 * 1024
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_WINDOWS_RESERVED = re.compile(r"(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?\Z", re.I)


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_member(name: str) -> tuple[str, ...]:
    if not isinstance(name, str) or not name or "\\" in name or ":" in name or "\x00" in name:
        raise ValueError("unsafe archive member")
    if unicodedata.normalize("NFC", name) != name:
        raise ValueError("non-canonical archive path")
    parts = pathlib.PurePosixPath(name).parts
    if name.startswith("/") or any(p in ("", ".", "..") or p[-1:] in (" ", ".")
                                or _WINDOWS_RESERVED.fullmatch(p) for p in parts):
        raise ValueError("unsafe archive member")
    if "/".join(parts) != name:
        raise ValueError("non-canonical archive path")
    return parts


def _installed_bytes(root: pathlib.Path, parts: tuple[str, ...]) -> bytes:
    path = root
    for part in parts:
        path = path / part
        if path.is_symlink():
            raise ValueError("installed symlink")
    try:
        resolved = path.resolve(strict=True)
        if not resolved.is_relative_to(root) or not resolved.is_file():
            raise ValueError("installed path escapes root or is not a file")
        return resolved.read_bytes()
    except (FileNotFoundError, NotADirectoryError) as exc:
        raise ValueError("installed member absent") from exc


def qualify_wheel(
    wheel, installed_root, *, expected_sha256: str, source_files: dict[str, str],
    expected_distribution: str = "market-data", expected_version: str | None = None,
    expected_entrypoints: dict[str, str] | None = None,
):
    """Diagnose exact bytes; never use result as a Root operation permit.

    expected_sha256 and source_files MUST be supplied from a separate
    authenticated release process. This function cannot establish their trust.
    installed_root is a disposable, independently owned installation root.
    Expected entrypoint mappings are metadata-only; scripts/imports are NOT run.
    """
    if not isinstance(expected_sha256, str) or _SHA256.fullmatch(expected_sha256) is None:
        raise ValueError("unverified wheel pin format")
    if not isinstance(source_files, dict) or not source_files:
        raise ValueError("missing source pins")
    if not isinstance(expected_distribution, str) or not expected_distribution:
        raise ValueError("missing distribution identity")
    for name, digest in source_files.items():
        _safe_member(name)
        if not isinstance(digest, str) or _SHA256.fullmatch(digest) is None:
            raise ValueError("invalid source pin")
    if expected_entrypoints is not None and (not isinstance(expected_entrypoints, dict)
                                              or not expected_entrypoints):
        raise ValueError("invalid entrypoint pin")
    root = pathlib.Path(installed_root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("installed root is not a directory")
    wheel_path = pathlib.Path(wheel)
    if _digest(wheel_path.read_bytes()) != expected_sha256:
        raise ValueError("wheel digest mismatch")

    with zipfile.ZipFile(wheel_path, "r") as archive:
        entries = archive.infolist()
        if not entries or len(entries) > _MAX_ARCHIVE_ENTRIES:
            raise ValueError("wheel member count invalid")
        payload: dict[str, bytes] = {}
        folded: set[str] = set()
        total = 0
        for info in entries:
            parts = _safe_member(info.filename)
            if info.is_dir():
                raise ValueError("explicit directory entries prohibited")
            normalized = info.filename.casefold()
            if normalized in folded:
                raise ValueError("duplicate or case-colliding archive member")
            folded.add(normalized)
            if info.create_system == 3 and stat.S_IFMT(info.external_attr >> 16) == stat.S_IFLNK:
                raise ValueError("symlink wheel member")
            if parts[0].endswith(".data") or ".data/" in info.filename:
                raise ValueError("unsupported relocated wheel member")
            total += info.file_size
            if info.file_size > _MAX_ARCHIVE_BYTES or total > _MAX_ARCHIVE_BYTES:
                raise ValueError("oversized wheel")
            payload[info.filename] = archive.read(info)
        records = [n for n in payload if n.endswith(".dist-info/RECORD")]
        if len(records) != 1:
            raise ValueError("ambiguous RECORD")
        record_name = records[0]
        dist_dir = record_name.removesuffix("/RECORD")
        if len(pathlib.PurePosixPath(dist_dir).parts) != 1 or not dist_dir.endswith(".dist-info"):
            raise ValueError("invalid distribution metadata directory")
        wheel_meta = dist_dir + "/WHEEL"
        pkg_meta = dist_dir + "/METADATA"
        if wheel_meta not in payload or pkg_meta not in payload:
            raise ValueError("missing WHEEL or METADATA")
        meta = Parser().parsestr(payload[pkg_meta].decode("utf-8"))
        distribution = meta.get("Name")
        version = meta.get("Version")
        norm = lambda x: re.sub(r"[-_.]+", "-", x).lower()
        if not distribution or not version or norm(distribution) != norm(expected_distribution):
            raise ValueError("distribution name mismatch")
        if expected_version is not None and version != expected_version:
            raise ValueError("distribution version mismatch")
        if dist_dir != norm(distribution).replace("-", "_") + "-" + version + ".dist-info":
            raise ValueError("dist-info identity mismatch")
        if not wheel_path.name.startswith(norm(distribution).replace("-", "_") + "-" + version + "-"):
            raise ValueError("wheel filename identity mismatch")

        rows = list(csv.reader(io.StringIO(payload[record_name].decode("utf-8"), newline="")))
        recorded: set[str] = set()
        for row in rows:
            if len(row) != 3:
                raise ValueError("invalid RECORD row")
            name, encoded, size = row
            _safe_member(name)
            if name in recorded or name not in payload:
                raise ValueError("duplicate or unrecognized RECORD member")
            recorded.add(name)
            data = payload[name]
            if name == record_name:
                if encoded or size:
                    raise ValueError("self-hashed RECORD not supported")
            else:
                actual = "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip("=")
                if encoded != actual or size != str(len(data)):
                    raise ValueError("RECORD integrity mismatch")
        if recorded != payload.keys():
            raise ValueError("wheel contains unrecorded member")
        # pip rewrites the INSTALLED RECORD: it adds INSTALLER, scripts,
        # direct_url.json, and often un-hashed __pycache__ entries. The wheel
        # RECORD and installed RECORD are different sources of evidence.
        installed_record_bytes = _installed_bytes(root, _safe_member(record_name))
        installed_rows = list(csv.reader(io.StringIO(installed_record_bytes.decode("utf-8"), newline="")))
        installed_seen: set[str] = set()
        auxiliary_unhashed = 0
        for row in installed_rows:
            if len(row) != 3:
                raise ValueError("installed RECORD row invalid")
            name, encoded, size = row
            if name in installed_seen:
                raise ValueError("duplicate installed RECORD member")
            installed_seen.add(name)
            if name == record_name:
                if encoded or size:
                    raise ValueError("installed RECORD self-hash invalid")
                continue
            if name.startswith("../../bin/"):
                # Strict pip --target script path only; other venv schemes
                # must be admitted through a separately reviewed runner.
                script = name.removeprefix("../../bin/")
                if (not expected_entrypoints or script not in expected_entrypoints
                        or not script or "/" in script or chr(92) in script):
                    raise ValueError("unexpected installed script path")
                parts = ("bin", script)
            else:
                parts = _safe_member(name)
            data = _installed_bytes(root, parts)
            if name in payload and data != payload[name]:
                raise ValueError("wheel member changed during install")
            if not encoded and not size:
                if (not name.endswith(".pyc") or "__pycache__" not in parts
                        or name in payload):
                    raise ValueError("unhashed installed runtime member")
                auxiliary_unhashed += 1
                continue
            actual = "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip("=")
            if encoded != actual or size != str(len(data)):
                raise ValueError("installed RECORD integrity mismatch")
        if installed_seen.intersection(payload.keys()) != payload.keys():
            raise ValueError("installed RECORD omits wheel member")
        for name, expected in source_files.items():
            if name not in payload or _digest(payload[name]) != expected or name.endswith("/RECORD"):
                raise ValueError("source bytes mismatch or missing runtime module")
        if expected_entrypoints is not None:
            ep = dist_dir + "/entry_points.txt"
            if ep not in payload:
                raise ValueError("entrypoint metadata absent")
            parser = configparser.ConfigParser(interpolation=None)
            parser.optionxform = str
            parser.read_string(payload[ep].decode("utf-8"))
            if not parser.has_section("console_scripts"):
                raise ValueError("console entrypoints absent")
            for name, target in expected_entrypoints.items():
                if not parser.has_option("console_scripts", name) or parser.get("console_scripts", name) != target:
                    raise ValueError("entrypoint metadata mismatch")
    return {
        "wheel_bytes_match": True,
        "installed_bytes_match": True,
        "installed_record_verified": True,
        "unhashed_install_auxiliary_count": auxiliary_unhashed,
        "all_installed_bytes_authenticated": False,  # no authenticated install closure or import proof
        "source_bytes_match": True,
        "entrypoint_metadata_match": expected_entrypoints is not None,
        "import_origin_verified": False,
        "runtime_entrypoint_verified": False,
        "release_authenticated": False,
        "root_admitted": False,
        "writer_admitted": False,
    }
