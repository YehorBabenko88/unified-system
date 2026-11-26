"""Offline package qualification only. Never issues Root or writer authority."""
import base64
import csv
import hashlib
import io
import pathlib
import zipfile

def qualify_wheel(wheel, installed_root, *, expected_sha256, source_files):
    """Compare a trusted externally pinned wheel and source map with installed bytes.
    source_files maps wheel-relative paths to externally pinned SHA256 values.
    Result is diagnostic only; caller inputs are not authenticated release evidence.
    """
    wheel = pathlib.Path(wheel)
    root = pathlib.Path(installed_root).resolve(strict=True)
    def digest(data):
        return hashlib.sha256(data).hexdigest()
    if digest(wheel.read_bytes()) != expected_sha256:
        raise ValueError("wheel digest mismatch")
    with zipfile.ZipFile(wheel) as z:
        names = z.namelist()
        if len(names) != len(set(names)):
            raise ValueError("duplicate archive member")
        for name in names:
            p = pathlib.PurePosixPath(name)
            if p.is_absolute() or ".." in p.parts or "\\" in name or ":" in name:
                raise ValueError("unsafe archive member")
        records = [n for n in names if n.endswith(".dist-info/RECORD")]
        if len(records) != 1:
            raise ValueError("ambiguous RECORD")
        rows = list(csv.reader(io.StringIO(z.read(records[0]).decode("utf-8"))))
        seen = set()
        for name, encoded, size in rows:
            if name in seen or name not in names:
                raise ValueError("invalid RECORD member")
            seen.add(name)
            if name == records[0]:
                continue
            data = z.read(name)
            actual = "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip("=")
            if encoded != actual or size != str(len(data)):
                raise ValueError("RECORD mismatch")
            if ".data/" in name:
                raise ValueError("unsupported relocated wheel member")
            target = root.joinpath(*pathlib.PurePosixPath(name).parts)
            if not target.resolve(strict=True).is_relative_to(root) or target.read_bytes() != data:
                raise ValueError("installed bytes mismatch")
        if seen != {n for n in names if not n.endswith("/")}:
            raise ValueError("unrecorded wheel member")
        if not source_files:
            raise ValueError("missing source pins")
        for name, sha in source_files.items():
            if name not in seen or name == records[0] or digest(z.read(name)) != sha:
                raise ValueError("source bytes mismatch")
    return {"wheel_bytes_match": True, "installed_bytes_match": True,
            "root_admitted": False, "writer_admitted": False,
            "import_origin_verified": False, "entrypoint_verified": False,
            "installed_record_verified": False, "release_authenticated": False}
