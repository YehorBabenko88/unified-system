"""Bounded file-integrity data, never execution or source-provenance authority.

No package copying, manifest writes, process/network operations or ACL changes.
The caller must separately establish source/tool trust and protected parents.
Stat comparisons detect ordinary mutation, not a hostile administrator who can
replace namespaces and restore metadata between observations.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import unicodedata

MAX_FILES = 20000
MAX_BYTES = 1073741824
MAX_MANIFEST_BYTES = 8*1024*1024
MAX_METADATA_BYTES = 65536
SCHEMA = "unified.physical-dev-package.v1"
FIXED = dict(schema=SCHEMA,source_provenance="DESCRIPTIVE_NOT_VERIFIED",public_submit="DENY",
             runtime_admission=False,physical_execution_authorization=False)


class PackageError(ValueError):
    """Closed integrity refusal; it is never a recovery or execution grant."""


def _need(condition):
    if not condition: raise PackageError("PACKAGE_INTEGRITY_REJECTED")


def _integer(value, minimum, maximum):
    _need(type(value) is int and minimum<=value<=maximum)


def _closed(value, fields):
    _need(type(value) is dict and set(value)==set(fields))


def _canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode("ascii")


def _text(value,limit):
    _need(type(value) is str and 1<=len(value)<=limit and value==value.strip())
    _need(not any(unicodedata.category(char) in ("Cc","Cs") for char in value))


def _sha(value,length):
    _need(type(value) is str and re.fullmatch("[0-9a-f]{"+str(length)+"}",value) is not None)


def _relative(value):
    _text(value,1024)
    _need(unicodedata.normalize("NFC",value)==value)
    _need(not any(char in value for char in '\\:< >|?*"'.replace(" ","")))
    parts=value.split("/")
    for part in parts:
        _need(1<=len(part)<=255 and part not in (".","..") and not part.endswith((" ",".")))
        device=part.split(".",1)[0].rstrip(" ").upper()
        _need(device not in ("CON","PRN","AUX","NUL","CONIN$","CONOUT$") and re.fullmatch(r"(?:COM|LPT)[1-9¹²³]",device) is None)
    return value


def _ordinary(info,kind):
    _need(not getattr(info,"st_file_attributes",0)&1024)
    _need(stat.S_ISDIR(info.st_mode) if kind=="directory" else stat.S_ISREG(info.st_mode) and info.st_nlink==1)


def _signature(info):
    return (info.st_dev,info.st_ino,info.st_mode,info.st_nlink,info.st_size,info.st_mtime_ns,info.st_ctime_ns)


def _directory(raw):
    path=Path(raw)
    _need(path.is_absolute() and not str(path).startswith(("\\\\","//")))
    _need(str(path)==str(path.resolve(strict=True)))
    for item in (*reversed(path.parents),path): _ordinary(item.lstat(),"directory")
    return path


def _inventory(root,max_files,max_bytes):
    files={};directories={};names={};pending=[root];total=0
    while pending:
        directory=pending.pop();_directory(directory)
        relative=directory.relative_to(root).as_posix()
        directories[relative]=_signature(directory.lstat())
        _need(len(directories)<=MAX_FILES)
        with os.scandir(directory) as entries:
            for entry in entries:
                path=directory/entry.name;relative=_relative(path.relative_to(root).as_posix())
                alias=relative.casefold()
                _need(alias not in names);names[alias]=relative
                # Windows DirEntry.stat may return zero link/inode fields;
                # lstat supplies the actual identity needed for hardlink checks.
                info=path.lstat()
                if stat.S_ISDIR(info.st_mode):
                    _ordinary(info,"directory");pending.append(path)
                    _need(len(pending)+len(directories)<=MAX_FILES)
                else:
                    _ordinary(info,"file");_integer(info.st_size,0,max_bytes)
                    total+=info.st_size;_need(total<=max_bytes)
                    files[relative]=(path,_signature(info))
                    _need(len(files)<=max_files)
    return files,directories


def _hash_file(path,expected):
    # Recheck named parents immediately before opening an ordinary single-link
    # file. Descriptor identity must agree with the inventory before any read.
    _directory(path.parent)
    _ordinary(path.lstat(),"file");_need(_signature(path.lstat())==expected)
    descriptor=os.open(path,os.O_RDONLY|getattr(os,"O_BINARY",0)|getattr(os,"O_NOFOLLOW",0))
    try:
        held=os.fstat(descriptor);_ordinary(held,"file");held_before=_signature(held)
        # Windows pathname/descriptor ctime can use different timestamp
        # semantics. Compare identity/size/mtime across APIs, and retain full
        # before/after comparisons within each API (including its own ctime).
        _need(held_before[:6]==expected[:6])
        size=expected[4];count=0;digest=hashlib.sha256()
        while True:
            chunk=os.read(descriptor,min(65536,size-count+1))
            if not chunk:break
            count+=len(chunk);_need(count<=size);digest.update(chunk)
        _need(count==size and _signature(os.fstat(descriptor))==held_before)
        current=path.lstat();_ordinary(current,"file");_need(_signature(current)==expected)
        return dict(bytes=count,sha256=digest.hexdigest())
    finally:os.close(descriptor)


def snapshot_files(root, *, max_files=MAX_FILES, max_bytes=MAX_BYTES):
    """Return all file bytes/count digests; hidden files are ordinary members.

    Empty directories are namespace-checked but not represented in this file-only
    manifest. Caller-supplied limits can only reduce the hard ceilings.
    """
    _integer(max_files,1,MAX_FILES);_integer(max_bytes,0,MAX_BYTES)
    try:
        root=_directory(root)
        before,dirs=_inventory(root,max_files,max_bytes)
        result={name:_hash_file(path,identity) for name,(path,identity) in sorted(before.items())}
        after,after_dirs=_inventory(root,max_files,max_bytes)
        _need(before==after and dirs==after_dirs)
        return result
    except (OSError,RuntimeError,TypeError) as exc:
        raise PackageError("PACKAGE_FILES_UNAVAILABLE") from exc


def _files(files):
    _need(type(files) is dict and len(files)<=MAX_FILES)
    aliases=set();namespace={};total=0
    for name,value in files.items():
        _relative(name);_need(name.casefold() not in aliases);aliases.add(name.casefold())
        parts=name.split("/")
        for index in range(1,len(parts)+1):
            prefix="/".join(parts[:index]);folded=prefix.casefold()
            _need(namespace.get(folded,prefix)==prefix);namespace[folded]=prefix
        _closed(value,("bytes","sha256"));_integer(value["bytes"],0,MAX_BYTES);_sha(value["sha256"],64)
        total+=value["bytes"];_need(total<=MAX_BYTES)
    # A file cannot also be an ancestor directory, including through a case alias.
    for name in files:
        for parent in Path(name).parents:
            if str(parent)!=".":_need(parent.as_posix().casefold() not in aliases)
    return total


def _metadata(value):
    _closed(value,("description","sources","dependencies"));_text(value["description"],2048)
    for field,limit in (("sources",32),("dependencies",128)):
        _need(type(value[field]) is list and len(value[field])<=limit)
        names=set()
        for entry in value[field]:
            _closed(entry,("name","repository","commit","tree") if field=="sources" else ("name","version"))
            _text(entry["name"],128);_need(entry["name"].casefold() not in names);names.add(entry["name"].casefold())
            if field=="sources":
                _need(type(entry["repository"]) is str and re.fullmatch(r"[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}",entry["repository"]) is not None)
                _sha(entry["commit"],40);_sha(entry["tree"],40)
            else:_text(entry["version"],128)
    _need(len(_canonical(value))<=MAX_METADATA_BYTES)


def manifest_bytes(files, source_metadata):
    """Create canonical in-memory data; syntax-valid source pins remain claims."""
    total=_files(files);_metadata(source_metadata)
    value=dict(FIXED,files=copy.deepcopy(files),file_count=len(files),total_bytes=total,source_metadata=copy.deepcopy(source_metadata))
    result=_canonical(value);_need(len(result)<=MAX_MANIFEST_BYTES)
    return result


def _pairs(pairs):
    result={}
    for key,value in pairs:
        _need(key not in result);result[key]=value
    return result


def verify_package(root, manifest_raw, expected_manifest_sha256):
    """Verify an externally pinned manifest against current file bytes only.

    A successful result is descriptive integrity DATA. It grants no execution,
    install, source-provenance, runtime or physical authorization.
    """
    _need(type(manifest_raw) is bytes and len(manifest_raw)<=MAX_MANIFEST_BYTES)
    _sha(expected_manifest_sha256,64)
    _need(hashlib.sha256(manifest_raw).hexdigest()==expected_manifest_sha256)
    try:
        value=json.loads(manifest_raw.decode("ascii"),object_pairs_hook=_pairs,
                         parse_constant=lambda _:(_ for _ in ()).throw(PackageError("PACKAGE_JSON_REJECTED")))
        _closed(value,(*FIXED,"files","file_count","total_bytes","source_metadata"))
        _need(_canonical(value)==manifest_raw)
        for key,expected in FIXED.items():_need(type(value[key]) is type(expected) and value[key]==expected)
        total=_files(value["files"]);_metadata(value["source_metadata"])
        _integer(value["file_count"],0,MAX_FILES);_integer(value["total_bytes"],0,MAX_BYTES)
        _need(value["file_count"]==len(value["files"]) and value["total_bytes"]==total)
    except (UnicodeError,ValueError,TypeError,RecursionError,OverflowError) as exc:
        if isinstance(exc,PackageError):raise
        raise PackageError("PACKAGE_MANIFEST_REJECTED") from exc
    _need(snapshot_files(root)==value["files"])
    return dict(status="VERIFIED_FILE_BYTES_ONLY",manifest_sha256=expected_manifest_sha256,
                file_count=value["file_count"],total_bytes=total,source_metadata=copy.deepcopy(value["source_metadata"]),
                source_provenance=FIXED["source_provenance"],public_submit="DENY",runtime_admission=False,physical_execution_authorization=False)
