"""Immutable local objects in an exclusively created, identity-bound owned root.

This library performs real local filesystem effects. It is not an admitted service
factory or dataset publication authority. Callers must separately admit the root,
OS access control and current staging grant before any office/runtime use.
"""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import threading
import uuid

from .contracts import StorageBlocked, _UUID, digest, require

MAX_OBJECT_BYTES = 64 * 1024 * 1024
_MARKER = "owned-root.json"
_REPARSE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 1024)


def _identity(info):
    return info.st_dev, info.st_ino


def _plain(path, *, directory):
    info = path.lstat()
    require(not stat.S_ISLNK(info.st_mode) and not (getattr(info, "st_file_attributes", 0) & _REPARSE), "PATH_ALIAS_REJECTED")
    require(stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode), "PATH_KIND_REJECTED")
    if not directory:
        require(info.st_nlink == 1, "HARDLINK_REJECTED")
    return info


def _parents(path):
    for parent in reversed((path, *path.parents)):
        _plain(parent, directory=True)


def _read(path, max_bytes):
    before = _plain(path, directory=False)
    require(before.st_size <= max_bytes, "OBJECT_SIZE_EXCEEDED")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0))
    try:
        opened = os.fstat(fd)
        require(_identity(opened) == _identity(before) and opened.st_nlink == 1, "FILE_IDENTITY_CHANGED")
        chunks, total = [], 0
        while True:
            chunk = os.read(fd, min(1024*1024, max_bytes-total+1))
            if not chunk:
                break
            total += len(chunk)
            require(total <= max_bytes, "OBJECT_SIZE_EXCEEDED")
            chunks.append(chunk)
        after = os.fstat(fd)
        current = _plain(path, directory=False)
        require((_identity(after), after.st_size, after.st_mtime_ns) ==
                (_identity(before), before.st_size, before.st_mtime_ns), "OBJECT_CHANGED_DURING_READ")
        require((_identity(current), current.st_size, current.st_mtime_ns) ==
                (_identity(after), after.st_size, after.st_mtime_ns), "OBJECT_PATH_CHANGED")
        require(total == after.st_size, "OBJECT_SHORT_READ")
        return b"".join(chunks), _identity(after)
    finally:
        os.close(fd)


def _write_new(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        view = memoryview(raw)
        while view:
            written = os.write(fd, view)
            require(type(written) is int and 0 < written <= len(view), "OBJECT_SHORT_WRITE")
            view = view[written:]
        os.fsync(fd)
        info = os.fstat(fd)
        require(info.st_size == len(raw) and info.st_nlink == 1, "OBJECT_WRITE_IDENTITY_CHANGED")
        return _identity(info)
    finally:
        os.close(fd)


def _sync_directory(path):
    # Python has no portable Windows directory-handle durability primitive.
    # Do not silently label file fsync as qualified namespace/crash durability.
    if sys.platform == "win32":
        return False
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return True


@dataclass(frozen=True)
class LocalObject:
    store_id: str
    sha256: str
    byte_length: int
    file_identity: tuple[int, int]
    durability: str

    @property
    def publication_confirmed(self):
        return False

    def content_ref(self):
        return {"object_sha256": self.sha256, "bytes": str(self.byte_length)}


class ObjectStore:
    """No arbitrary object path, overwrite, adoption or delete method."""

    def __init__(self, root, store_id, marker, identities):
        self._root = root
        self.store_id = store_id
        self._marker = marker
        self._identities = identities
        self._lock = threading.RLock()

    @staticmethod
    def _inputs(root, store_id):
        require(type(store_id) is str and _UUID.fullmatch(store_id) is not None, "STORE_ID_INVALID")
        path = Path(root)
        require(path.is_absolute() and ".." not in path.parts, "ROOT_PATH_REJECTED")
        marker = json.dumps({"schema": "unified.storage.owned-root.v1", "store_id": store_id}, sort_keys=True, separators=(",", ":")).encode("ascii")
        return path, marker

    @classmethod
    def create(cls, root, *, store_id):
        path, marker = cls._inputs(root, store_id)
        try:
            _parents(path.parent)
            path.mkdir(exist_ok=False)
            _write_new(path/_MARKER, marker)
            (path/"objects").mkdir(exist_ok=False)
            (path/"staging").mkdir(exist_ok=False)
            _sync_directory(path)
            _sync_directory(path.parent)
            return cls.open(path, store_id=store_id)
        except OSError as exc:
            raise StorageBlocked("OWNED_ROOT_CREATE_FAILED") from exc

    @classmethod
    def open(cls, root, *, store_id):
        path, marker = cls._inputs(root, store_id)
        try:
            _parents(path)
            actual, _ = _read(path/_MARKER, 2048)
            require(actual == marker, "STORE_IDENTITY_MISMATCH")
            identities = {name: _identity(_plain(path/name, directory=True)) for name in (".", "objects", "staging")}
            return cls(path, store_id, marker, identities)
        except OSError as exc:
            raise StorageBlocked("OWNED_ROOT_UNAVAILABLE") from exc

    def _check(self):
        _parents(self._root)
        for name, expected in self._identities.items():
            require(_identity(_plain(self._root/name, directory=True)) == expected, "OWNED_ROOT_CHANGED")
        require(_read(self._root/_MARKER, 2048)[0] == self._marker, "STORE_MARKER_CHANGED")

    @staticmethod
    def _limit(max_bytes):
        require(type(max_bytes) is int and 0 <= max_bytes <= MAX_OBJECT_BYTES, "OBJECT_LIMIT_INVALID")

    def _read_verified(self, object_sha256, *, max_bytes=MAX_OBJECT_BYTES):
        digest(object_sha256)
        self._limit(max_bytes)
        with self._lock:
            try:
                self._check()
                raw, identity = _read(self._root/"objects"/object_sha256, max_bytes)
                require(hashlib.sha256(raw).hexdigest() == object_sha256, "OBJECT_CORRUPT")
                self._check()
                return raw, identity
            except OSError as exc:
                raise StorageBlocked("OBJECT_UNAVAILABLE") from exc

    def read(self, object_sha256, *, max_bytes=MAX_OBJECT_BYTES):
        return self._read_verified(object_sha256, max_bytes=max_bytes)[0]

    def verify(self, object_sha256, *, max_bytes=MAX_OBJECT_BYTES):
        with self._lock:
            raw, identity = self._read_verified(object_sha256, max_bytes=max_bytes)
            return LocalObject(self.store_id, object_sha256, len(raw), identity, "READ_VERIFIED_DURABILITY_UNKNOWN")

    def put(self, raw, *, max_bytes=MAX_OBJECT_BYTES):
        self._limit(max_bytes)
        require(type(raw) is bytes and len(raw) <= max_bytes, "OBJECT_SIZE_EXCEEDED")
        object_sha256 = hashlib.sha256(raw).hexdigest()
        with self._lock:
            try:
                self._check()
                destination = self._root/"objects"/object_sha256
                if destination.exists() or destination.is_symlink():
                    return self.verify(object_sha256, max_bytes=max_bytes)
                staging = self._root/"staging"/str(uuid.uuid4())
                written_identity = _write_new(staging, raw)
                self._check()
                try:
                    os.link(staging, destination, follow_symlinks=False)
                except FileExistsError:
                    result = self.verify(object_sha256, max_bytes=max_bytes)
                    # A known-good separate destination exists; remove only our own temp.
                    require(_identity(_plain(staging, directory=False)) == written_identity, "STAGING_IDENTITY_CHANGED")
                    staging.unlink()
                    return result
                require(_identity(destination.lstat()) == written_identity and _identity(staging.lstat()) == written_identity, "LINK_IDENTITY_CHANGED")
                staging.unlink()  # Remove temp alias only after immutable destination exists.
                objects_synced = _sync_directory(self._root/"objects")
                staging_synced = _sync_directory(self._root/"staging")
                verified = self.verify(object_sha256, max_bytes=max_bytes)
                durability = "FILE_AND_DIRECTORY_SYNCED" if objects_synced and staging_synced else "FILE_SYNCED_NAMESPACE_UNQUALIFIED"
                return LocalObject(self.store_id, object_sha256, verified.byte_length, verified.file_identity, durability)
            except OSError as exc:
                # Retain uncertain staging bytes; do not infer an authoritative outcome.
                raise StorageBlocked("OBJECT_WRITE_UNCONFIRMED") from exc
