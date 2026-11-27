"""F-owned Windows read-only retained-handle backend for wheel qualification.

Not an execution/installation authority.  No service, registry, root, SQL or
network side effects.  Requires native Win32 and rejects reparse points,
alternate data streams, hardlinked files, aliases and foreign/uncertain handles.
Handles are retained for the entire installation inspection to narrow the
pathname TOCTOU interval.  This cannot attest release signatures, ACL protection,
an already-running Python interpreter or subsequent runtime mutation.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import ntpath
import os
import re
import unicodedata

_MAX_FILES = 10000
_MAX_BYTES = 256 * 1024 * 1024
_FILE_READ_DATA = 0x0001
_FILE_LIST_DIRECTORY = 0x0001
_FILE_READ_ATTRIBUTES = 0x0080
_FILE_SHARE_READ = 0x00000001
_OPEN_EXISTING = 3
_FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
_FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
_FILE_ATTRIBUTE_DIRECTORY = 0x10
_FILE_ATTRIBUTE_REPARSE_POINT = 0x400
_FILE_ATTRIBUTE_DEVICE = 0x40
_FILE_ID_INFO_CLASS = 18
_FILE_ATTRIBUTE_TAG_INFO_CLASS = 9
_INVALID_HANDLE = ctypes.c_void_p(-1).value
_RESERVED = re.compile(r"(?:con|prn|aux|nul|com[1-9¹²³]|lpt[1-9¹²³])(?:\..*)?$", re.I)


class _FILE_ID_INFO(ctypes.Structure):
    _fields_ = [("VolumeSerialNumber", ctypes.c_ulonglong),
                ("FileId", ctypes.c_ubyte * 16)]


class _FILE_ATTRIBUTE_TAG_INFO(ctypes.Structure):
    _fields_ = [("FileAttributes", wintypes.DWORD),
                ("ReparseTag", wintypes.DWORD)]


class _FILETIME(ctypes.Structure):
    _fields_ = [("low", wintypes.DWORD), ("high", wintypes.DWORD)]


class _BY_HANDLE_FILE_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("dwFileAttributes", wintypes.DWORD),
        ("ftCreationTime", _FILETIME),
        ("ftLastAccessTime", _FILETIME),
        ("ftLastWriteTime", _FILETIME),
        ("dwVolumeSerialNumber", wintypes.DWORD),
        ("nFileSizeHigh", wintypes.DWORD),
        ("nFileSizeLow", wintypes.DWORD),
        ("nNumberOfLinks", wintypes.DWORD),
        ("nFileIndexHigh", wintypes.DWORD),
        ("nFileIndexLow", wintypes.DWORD),
    ]


def _api():
    if os.name != "nt":
        raise ValueError("Win32 retained-handle inspection unsupported on this OS")
    dll = ctypes.WinDLL("kernel32", use_last_error=True)
    dll.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                               ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD,
                               wintypes.HANDLE]
    dll.CreateFileW.restype = wintypes.HANDLE
    dll.GetFileInformationByHandleEx.argtypes = [wintypes.HANDLE, ctypes.c_int,
                                                  ctypes.c_void_p, wintypes.DWORD]
    dll.GetFileInformationByHandleEx.restype = wintypes.BOOL
    dll.GetFileInformationByHandle.argtypes = [
        wintypes.HANDLE, ctypes.POINTER(_BY_HANDLE_FILE_INFORMATION)]
    dll.GetFileInformationByHandle.restype = wintypes.BOOL
    dll.ReadFile.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
                             ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
    dll.ReadFile.restype = wintypes.BOOL
    dll.CloseHandle.argtypes = [wintypes.HANDLE]
    dll.CloseHandle.restype = wintypes.BOOL
    dll.GetFinalPathNameByHandleW.argtypes = [
        wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD]
    dll.GetFinalPathNameByHandleW.restype = wintypes.DWORD
    return dll


def _segments(path):
    """Local drive-absolute spelling only; never resolve through a link."""
    if not isinstance(path, (str, os.PathLike)):
        raise ValueError("Windows path required")
    raw = os.fspath(path)
    if type(raw) is not str or not re.match(r"^[A-Za-z]:\\", raw):
        raise ValueError("local drive-absolute Windows path required")
    if "/" in raw or raw.endswith((".", " ")) or "\x00" in raw:
        raise ValueError("non-canonical Windows path")
    parts = raw.split("\\")
    if len(parts) == 2 and parts[1] == "":
        return parts[0] + "\\", []
    if not parts[0].endswith(":") or len(parts) < 2:
        raise ValueError("invalid Windows drive path")
    drive = parts[0] + "\\"
    result = []
    for part in parts[1:]:
        if not part:
            raise ValueError("empty Windows path component")
        _part(part)
        result.append(part)
    return drive, result


def _part(part):
    if type(part) is not str or not part or part in (".", ".."):
        raise ValueError("invalid Windows path component")
    if (unicodedata.normalize("NFC", part) != part
            or any(ord(c) < 32 for c in part)
            or any(c in part for c in "\\/:*?\"<>|\x00")
            or part.endswith((" ", "."))
            or _RESERVED.fullmatch(part)):
        raise ValueError("unsafe Windows path component")
    return part


def _info(dll, handle, *, directory):
    tag = _FILE_ATTRIBUTE_TAG_INFO()
    if not dll.GetFileInformationByHandleEx(handle, _FILE_ATTRIBUTE_TAG_INFO_CLASS,
                                             ctypes.byref(tag), ctypes.sizeof(tag)):
        raise ValueError("Windows handle attribute identity unavailable")
    flags = tag.FileAttributes
    if flags & (_FILE_ATTRIBUTE_REPARSE_POINT | _FILE_ATTRIBUTE_DEVICE):
        raise ValueError("reparse point, junction or device refused")
    if bool(flags & _FILE_ATTRIBUTE_DIRECTORY) != bool(directory):
        raise ValueError("Windows handle type mismatch")
    fileid = _FILE_ID_INFO()
    if not dll.GetFileInformationByHandleEx(handle, _FILE_ID_INFO_CLASS,
                                             ctypes.byref(fileid), ctypes.sizeof(fileid)):
        raise ValueError("Windows file ID unavailable")
    basic = _BY_HANDLE_FILE_INFORMATION()
    if not dll.GetFileInformationByHandle(handle, ctypes.byref(basic)):
        raise ValueError("Windows handle metadata unavailable")
    if not directory and basic.nNumberOfLinks != 1:
        raise ValueError("ambiguous hardlinked installed file")
    return (int(fileid.VolumeSerialNumber), bytes(fileid.FileId),
            int(basic.nFileSizeHigh) << 32 | int(basic.nFileSizeLow),
            int(basic.ftLastWriteTime.high) << 32 | int(basic.ftLastWriteTime.low))


def _final_path_matches(dll, handle, expected):
    buf = ctypes.create_unicode_buffer(32768)
    size = dll.GetFinalPathNameByHandleW(handle, buf, len(buf), 0)
    if not size or size >= len(buf):
        raise ValueError("Windows final handle path unavailable")
    actual = buf.value
    if not actual.startswith("\\\\?\\"):
        raise ValueError("Windows non-DOS handle path refused")
    actual = actual[4:]
    if (not re.match(r"^[A-Za-z]:\\", actual)
            or ntpath.normcase(actual) != ntpath.normcase(expected)):
        raise ValueError("Windows path alias or reparse resolution refused")


def _open(dll, path, *, directory):
    access = _FILE_READ_ATTRIBUTES | (_FILE_LIST_DIRECTORY if directory else _FILE_READ_DATA)
    flags = _FILE_FLAG_OPEN_REPARSE_POINT | (_FILE_FLAG_BACKUP_SEMANTICS if directory else 0)
    handle = dll.CreateFileW(path, access, _FILE_SHARE_READ, None,
                              _OPEN_EXISTING, flags, None)
    if handle in (None, _INVALID_HANDLE):
        raise ValueError("Windows owned readonly handle unavailable")
    try:
        identity = _info(dll, handle, directory=directory)
        _final_path_matches(dll, handle, path)
    except BaseException:
        dll.CloseHandle(handle)
        raise
    return handle, identity


def _read(dll, handle, first, limit):
    if first[2] > limit:
        raise ValueError("installed member exceeds byte budget")
    blocks = []
    remaining = limit + 1
    while remaining:
        buf = ctypes.create_string_buffer(min(1024 * 1024, remaining))
        count = wintypes.DWORD()
        if not dll.ReadFile(handle, buf, len(buf), ctypes.byref(count), None):
            raise ValueError("Windows original handle read failed")
        if not count.value:
            break
        remaining -= count.value
        blocks.append(buf.raw[:count.value])
    if not remaining:
        raise ValueError("installed member exceeds byte budget")
    data = b"".join(blocks)
    if len(data) != first[2] or _info(dll, handle, directory=False) != first:
        raise ValueError("Windows original file modified during read")
    return data


class WindowsInstalledRoot:
    """Read-only retained directory/file handles, never a release authority.

    Exact anchored paths and FILE_SHARE_READ deny ordinary delete/rename/write
    while retained. Enumeration is still a forensic snapshot, not a security
    boundary against existing privileged writers or later runtime mutation.
    """

    def __init__(self, root):
        self.root = os.fspath(root)
        self.dll = None
        self._dirs = {}
        self._files = []
        self._count = 0

    def __enter__(self):
        self.dll = _api()
        try:
            drive, parts = _segments(self.root)
            self._retain_dir(drive)
            current = drive.rstrip("\\")
            for part in parts:
                current += "\\" + part
                # At each traversed directory boundary, refuse substitution
                # of a component that would otherwise be reached by name.
                retained, pinned = self._retain_dir(current)
                probe, observed = _open(self.dll, current, directory=True)
                try:
                    if observed != pinned:
                        raise ValueError("Windows root ancestor path substituted")
                finally:
                    self.dll.CloseHandle(probe)
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *_exc):
        if self.dll is not None:
            for handle in reversed(self._files):
                self.dll.CloseHandle(handle)
            for handle, _ in reversed(list(self._dirs.values())):
                self.dll.CloseHandle(handle)
        self._files.clear()
        self._dirs.clear()
        self.dll = None

    def _retain_dir(self, path):
        key = ntpath.normcase(path)
        if key not in self._dirs:
            self._dirs[key] = _open(self.dll, path, directory=True)
        else:
            handle, first = self._dirs[key]
            if _info(self.dll, handle, directory=True) != first:
                raise ValueError("Windows retained parent identity changed")
        return self._dirs[key]

    def _parent(self, parts):
        _segments(self.root)
        _part(parts[0])
        path = self.root
        self._retain_dir(path)
        for name in parts[:-1]:
            _part(name)
            path = ntpath.join(path, name)
            retained, pinned = self._retain_dir(path)
            # The Win32 directory was retained before opening any descendant.
            # A second pathname probe must resolve to the SAME kernel object;
            # a replacement via an existing writable handle cannot be
            # silently mistaken for the retained parent.
            probe, observed = _open(self.dll, path, directory=True)
            try:
                if observed != pinned:
                    raise ValueError("Windows parent directory path substituted")
            finally:
                self.dll.CloseHandle(probe)
        return path

    def read(self, parts, *, max_bytes=_MAX_BYTES):
        if not isinstance(parts, tuple) or not parts:
            raise ValueError("installed relative parts required")
        parent = self._parent(parts)
        _part(parts[-1])
        path = ntpath.join(parent, parts[-1])
        self._count += 1
        if self._count > _MAX_FILES * 4:
            raise ValueError("Windows retained handle budget exceeded")
        handle, first = _open(self.dll, path, directory=False)
        self._files.append(handle)
        data = _read(self.dll, handle, first, max_bytes)
        self._retain_dir(parent)
        # Verify the live pathname still identifies the retained original
        # file, not merely that our old handle remains readable. The held
        # handle stays open through the repeat-open check.
        probe, current = _open(self.dll, path, directory=False)
        try:
            if current != first:
                raise ValueError("Windows installed file path substituted")
        finally:
            self.dll.CloseHandle(probe)
        return data

    def readonly_identity_receipt(self, parts):
        """Observed Win32 object identities, NOT installation or delete authority.

        The caller must separately bind this observation to a versioned,
        authenticated installation receipt at initial installation time.
        Retain original directory and file handles while checking a repeat
        open; never interpret this forensic observation as ownership.
        """
        if not isinstance(parts, tuple) or not parts:
            raise ValueError("installed relative parts required")
        parent = self._parent(parts)
        _part(parts[-1])
        path = ntpath.join(parent, parts[-1])
        root_handle, root_before = self._retain_dir(self.root)
        parent_handle, parent_before = self._retain_dir(parent)
        if self._count >= _MAX_FILES * 4:
            raise ValueError("Windows retained identity handle budget exceeded")
        self._count += 1
        handle, first = _open(self.dll, path, directory=False)
        self._files.append(handle)
        probe, second = _open(self.dll, path, directory=False)
        try:
            if first != second or _info(self.dll, handle, directory=False) != first:
                raise ValueError("Windows original file identity changed")
            if (_info(self.dll, parent_handle, directory=True) != parent_before
                    or _info(self.dll, root_handle, directory=True) != root_before):
                raise ValueError("Windows root or parent file identity changed")
            if any(len(info[1]) != 16 or info[0] <= 0
                   for info in (first, parent_before, root_before)):
                raise ValueError("Windows native 128-bit identity unavailable")
            return {
                "schema": "f-win32-file-identity-observation.v1",
                "relative_path": "/".join(parts),
                "file_volume_serial": first[0],
                "file_id128": first[1].hex(),
                "parent_volume_serial": parent_before[0],
                "parent_file_id128": parent_before[1].hex(),
                "root_volume_serial": root_before[0],
                "root_file_id128": root_before[1].hex(),
                "size_bytes": first[2],
                "filetime_last_write": first[3],
                "installation_ownership_attested": False,
                "physical_delete_authorized": False,
            }
        finally:
            self.dll.CloseHandle(probe)

    def verify_readonly_identity_receipt(self, parts, expected):
        """Compare an exact earlier observation; fail closed on substitution.

        This check does not authenticate when or by whom expected was made.
        """
        if type(expected) is not dict or expected.get("schema") != "f-win32-file-identity-observation.v1":
            raise ValueError("Windows identity observation schema invalid")
        current = self.readonly_identity_receipt(parts)
        if current != expected:
            raise ValueError("Windows observed installation identity mismatch")
        return current

    def closure(self):
        discovered = set()
        visited = set()

        def walk(directory, prefix):
            handle, first = self._retain_dir(directory)
            ident = first[:2]
            if ident in visited:
                raise ValueError("Windows directory identity revisited")
            visited.add(ident)
            if len(visited) > _MAX_FILES:
                raise ValueError("Windows directory count exceeded")
            with os.scandir(directory) as entries:
                originals = list(entries)
            names = [item.name for item in originals]
            if len(names) != len(set(n.casefold() for n in names)):
                raise ValueError("Windows case-colliding installed paths")
            for entry in originals:
                name = entry.name
                _part(name)
                rel = prefix + (name,)
                path = ntpath.join(directory, name)
                # Enumerator metadata is NOT trusted for final authority:
                # the retained CreateFileW handle independently verifies
                # the exact original file ID and reparse tag.
                if entry.is_dir(follow_symlinks=False):
                    self._retain_dir(path)
                    walk(path, rel)
                elif entry.is_file(follow_symlinks=False):
                    if (name.lower().endswith((".pyc", ".pyo", ".pth", ".egg-link"))
                            or name.lower() in ("sitecustomize.py", "usercustomize.py")):
                        raise ValueError("untrusted Windows import hook or bytecode")
                    self.read(rel)
                    discovered.add("/".join(rel))
                    if len(discovered) > _MAX_FILES:
                        raise ValueError("Windows installed closure too large")
                else:
                    raise ValueError("Windows reparse or unsupported installed member")
            if _info(self.dll, handle, directory=True) != first:
                raise ValueError("Windows directory changed during inspection")
            probe, current = _open(self.dll, directory, directory=True)
            try:
                if current != first:
                    raise ValueError("Windows traversed directory path substituted")
            finally:
                self.dll.CloseHandle(probe)
            with os.scandir(directory) as entries:
                after = [e.name for e in entries]
            if sorted(x.casefold() for x in names) != sorted(x.casefold() for x in after):
                raise ValueError("Windows directory membership changed")
        walk(self.root, ())
        return discovered


def wheel_snapshot(path, limit=_MAX_BYTES + 1024 * 1024):
    """Original wheel bytes from a no-reparse retained Windows file handle."""
    raw = os.fspath(path)
    _segments(raw)
    parent, name = ntpath.split(raw)
    _part(name)
    with WindowsInstalledRoot(parent) as root:
        return root.read((name,), max_bytes=limit)
