"""Fixed installed-Git byte export; existing source hardlinks are explicit.

No process, publisher/loaded-DLL attestation, ACL change, installation or deletion.
Root independently admits the real source/parent before invoking this operation.
"""
import hashlib
import os
from pathlib import Path
import re
import stat

from . import materialize
from . import package as integrity

FIXED_SOURCE=Path("C:/Program Files/Git")
FIXED_EVIDENCE_PARENT=Path("C:/Users/LS-5/.codex/native-e2e-evidence-20261109")
PINNED_GIT_EXE_SHA256="78211c7ed73988da93a6d8a33d47ec6187f464d7ea2a9a00c182bbd7a1ecf30f"
MAX_FILES=20000
MAX_BYTES=1073741824
MAX_ENTRIES=40000


class ExportError(ValueError):
    pass


def _need(condition):
    if not condition:raise ExportError("GIT_EXPORT_REJECTED_PARTIAL_EVIDENCE_RETAINED")


def _source_regular(info):
    # This exception is local to the one fixed source, never the package guard.
    _need(not getattr(info,"st_file_attributes",0)&1024)
    _need(stat.S_ISREG(info.st_mode) and info.st_nlink>=1)


def _inventory(root):
    pending=[root];files={};directories={};aliases=set();total=0;visited=0
    while pending:
        directory=pending.pop();integrity._directory(directory)
        directories[directory.relative_to(root).as_posix()]=integrity._signature(directory.lstat())
        _need(len(directories)<=MAX_FILES)
        with os.scandir(directory) as entries:
            for entry in entries:
                visited+=1;_need(visited<=MAX_ENTRIES)
                path=directory/entry.name;relative=integrity._relative(path.relative_to(root).as_posix())
                _need(relative.casefold() not in aliases);aliases.add(relative.casefold())
                info=path.lstat();_need(not getattr(info,"st_file_attributes",0)&1024)
                if stat.S_ISDIR(info.st_mode):integrity._ordinary(info,"directory");pending.append(path)
                else:
                    _source_regular(info);integrity._integer(info.st_size,0,MAX_BYTES)
                    total+=info.st_size;_need(total<=MAX_BYTES)
                    files[relative]=(path,integrity._signature(info));_need(len(files)<=MAX_FILES)
    return files,directories


def _hash_copy(source,expected,target=None,pinned=None):
    integrity._directory(source.parent)
    initial=source.lstat();_source_regular(initial);_need(integrity._signature(initial)==expected)
    source_fd=os.open(source,os.O_RDONLY|getattr(os,"O_BINARY",0)|getattr(os,"O_NOFOLLOW",0));target_fd=None
    try:
        held=os.fstat(source_fd);_source_regular(held);held_before=integrity._signature(held)
        _need(stat.S_IFMT(held_before[2])==stat.S_IFMT(expected[2]))
        _need(all(held_before[index]==expected[index] for index in (0,1,3,4,5)))
        if target is not None:
            integrity._directory(target.parent)
            target_fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,"O_BINARY",0)|getattr(os,"O_NOFOLLOW",0),0o600)
            integrity._ordinary(os.fstat(target_fd),"file")
        count=0;digest=hashlib.sha256()
        while True:
            chunk=os.read(source_fd,min(65536,expected[4]-count+1))
            if not chunk:break
            count+=len(chunk);_need(count<=expected[4]);digest.update(chunk)
            if target_fd is not None:materialize._write_all(target_fd,chunk)
        result=dict(bytes=count,sha256=digest.hexdigest())
        _need(count==expected[4] and (pinned is None or result==pinned))
        _need(integrity._signature(os.fstat(source_fd))==held_before)
        current=source.lstat();_source_regular(current);_need(integrity._signature(current)==expected)
        if target_fd is not None:
            os.fsync(target_fd);held_target=os.fstat(target_fd);named_target=target.lstat()
            integrity._ordinary(held_target,"file");integrity._ordinary(named_target,"file")
            _need((held_target.st_dev,held_target.st_ino)==(named_target.st_dev,named_target.st_ino))
            _need(held_target.st_size==named_target.st_size==count)
        return result
    finally:
        if target_fd is not None:os.close(target_fd)
        os.close(source_fd)


def _snapshot(root):
    before,dirs=_inventory(root)
    hashes={name:_hash_copy(path,identity) for name,(path,identity) in sorted(before.items())}
    after,after_dirs=_inventory(root);_need(before==after and dirs==after_dirs)
    return before,dirs,hashes


def export_git(destination):
    """Export fixed dependency bytes, preserving all failed partial evidence.

    Only existing regular SOURCE hardlinks are allowed. Outputs must be new
    independent single-link files. The returned receipt belongs outside the tree.
    """
    try:
        destination=Path(destination);integrity._text(str(destination),4096)
        parent=integrity._directory(FIXED_EVIDENCE_PARENT);source=integrity._directory(FIXED_SOURCE)
        _need(destination.is_absolute() and str(destination.parent)==str(parent) and str(destination)==str(parent/destination.name))
        _need(re.fullmatch(r"ls5-git-export-[A-Za-z0-9][A-Za-z0-9_.-]{0,95}",destination.name) is not None)
        integrity._relative(destination.name)
        _need(source!=destination and source not in destination.parents and destination not in source.parents)
        try:destination.lstat()
        except FileNotFoundError:pass
        else:raise ExportError("GIT_EXPORT_DESTINATION_ALREADY_EXISTS")
        inventory,directories=_inventory(source)
        _need("cmd/git.exe" in inventory)
        integrity._sha(PINNED_GIT_EXE_SHA256,64)
        main=_hash_copy(*inventory["cmd/git.exe"]);_need(main["sha256"]==PINNED_GIT_EXE_SHA256)
        before,before_dirs,hashes=_snapshot(source)
        _need(inventory==before and directories==before_dirs)
        # The complete snapshot must still contain the pinned executable, not
        # merely metadata matching the earlier quick pin observation.
        _need(hashes["cmd/git.exe"]==main and hashes["cmd/git.exe"]["sha256"]==PINNED_GIT_EXE_SHA256)
        parent_identity=materialize._directory_identity(parent)
        os.mkdir(destination,0o700);owned={destination:materialize._directory_identity(destination)}
        # Preserve the complete directory closure, including empty source dirs.
        for relative in sorted(before_dirs,key=lambda name:(len(Path(name).parts),name)):
            if relative==".":continue
            directory=destination/relative
            _need(materialize._directory_identity(parent)==parent_identity)
            _need(materialize._directory_identity(directory.parent)==owned[directory.parent])
            os.mkdir(directory,0o700);owned[directory]=materialize._directory_identity(directory)
        for relative,(path,identity) in sorted(before.items()):
            _need(materialize._directory_identity(parent)==parent_identity)
            directory=destination
            for part in Path(relative).parts[:-1]:
                _need(materialize._directory_identity(directory)==owned[directory]);directory=directory/part
                if directory not in owned:os.mkdir(directory,0o700);owned[directory]=materialize._directory_identity(directory)
                else:_need(materialize._directory_identity(directory)==owned[directory])
            _hash_copy(path,identity,destination/relative,hashes[relative])
        after,after_dirs,after_hashes=_snapshot(source)
        _need(before==after and before_dirs==after_dirs and hashes==after_hashes)
        _need(materialize._directory_identity(parent)==parent_identity)
        _need(all(materialize._directory_identity(path)==identity for path,identity in owned.items()))
        _,target_dirs=_inventory(destination);_need(set(target_dirs)==set(before_dirs))
        _need(integrity.snapshot_files(destination)==hashes)
        identities={name:list(identity) for name,(_,identity) in before.items()}
        receipt=dict(schema="unified.installed-git-export.v1",status="EXPORTED_DEPENDENCY_BYTES_ONLY",source=str(source),destination=str(destination),
                     pinned_git_exe_sha256=PINNED_GIT_EXE_SHA256,files=hashes,directories=sorted(before_dirs),source_identity=identities,
                     source_identity_sha256=hashlib.sha256(integrity._canonical(identities)).hexdigest(),
                     source_hardlink_file_count=sum(identity[3]>1 for _,identity in before.values()),file_count=len(hashes),total_bytes=sum(item["bytes"] for item in hashes.values()),
                     publisher_attestation="NOT_ESTABLISHED",loaded_dll_attestation="NOT_ESTABLISHED",destination_parent_acl="EXTERNAL_ROOT_VERIFICATION_REQUIRED",
                     public_submit="DENY",runtime_admission=False,physical_execution_authorization=False)
        _need(len(integrity._canonical(receipt))<=64*1024*1024)
        return receipt
    except (integrity.PackageError,materialize.MaterializeError,OSError,TypeError,ValueError,RuntimeError,OverflowError) as exc:
        if isinstance(exc,ExportError):raise
        raise ExportError("GIT_EXPORT_REJECTED_PARTIAL_EVIDENCE_RETAINED") from exc
