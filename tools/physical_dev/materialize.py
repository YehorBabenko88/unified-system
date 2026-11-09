"""Fixed-parent bounded byte copying; no runtime/physical execution authority.

Only Root may invoke this for an actual package after independent parent ACL and
isolation admission. Failures retain partial evidence; nothing is deleted.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat

from . import assembly
from . import package as integrity

FIXED_EVIDENCE_PARENT=Path("C:/Users/LS-5/.codex/native-e2e-evidence-20261109")
PLAN_FIELDS=("schema","mode","destination","components","files","component_counts","selected_file_count",
             "selected_bytes","skipped","skipped_entry_count","skipped_subtree_count","visited_entry_count",
             "limits","source_provenance","destination_parent_acl","requires_exclusive_destination_creation",
             "public_submit","runtime_admission","physical_execution_authorization")


class MaterializeError(ValueError):
    pass


def _need(condition):
    if not condition:raise MaterializeError("MATERIALIZE_REJECTED_PARTIAL_EVIDENCE_RETAINED")


def _approved_destination(value):
    path=Path(value)
    integrity._text(str(path),4096)
    _need(path.is_absolute() and re.fullmatch(r"ls5-package-[A-Za-z0-9][A-Za-z0-9_.-]{0,95}",path.name) is not None)
    parent=integrity._directory(FIXED_EVIDENCE_PARENT)
    _need(str(path.parent)==str(parent) and str(path)==str(parent/path.name))
    integrity._relative(path.name)
    return path


def _directory_identity(path):
    integrity._directory(path)
    info=path.lstat()
    return (info.st_dev,info.st_ino,stat.S_IFMT(info.st_mode))


def _write_all(descriptor,chunk):
    view=memoryview(chunk)
    while view:
        written=os.write(descriptor,view)
        _need(type(written) is int and 0<written<=len(view))
        view=view[written:]


def _copy_file(source,target,record):
    integrity._directory(source.parent)
    observed=source.lstat();integrity._ordinary(observed,"file");before=integrity._signature(observed)
    _need(before[4]==record["bytes"])
    source_fd=os.open(source,os.O_RDONLY|getattr(os,"O_BINARY",0)|getattr(os,"O_NOFOLLOW",0))
    target_fd=None
    try:
        held=os.fstat(source_fd);integrity._ordinary(held,"file");held_before=integrity._signature(held)
        _need(stat.S_IFMT(held_before[2])==stat.S_IFMT(before[2]))
        _need(all(held_before[index]==before[index] for index in (0,1,3,4,5)))
        integrity._directory(target.parent)
        target_fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,"O_BINARY",0)|getattr(os,"O_NOFOLLOW",0),0o600)
        target_info=os.fstat(target_fd);integrity._ordinary(target_info,"file")
        target_identity=(target_info.st_dev,target_info.st_ino)
        digest=hashlib.sha256();count=0
        while True:
            chunk=os.read(source_fd,min(65536,record["bytes"]-count+1))
            if not chunk:break
            count+=len(chunk);_need(count<=record["bytes"])
            digest.update(chunk);_write_all(target_fd,chunk)
        _need(count==record["bytes"] and digest.hexdigest()==record["sha256"])
        _need(integrity._signature(os.fstat(source_fd))==held_before)
        current=source.lstat();integrity._ordinary(current,"file");_need(integrity._signature(current)==before)
        os.fsync(target_fd)
        held_target=os.fstat(target_fd);current_target=target.lstat()
        integrity._ordinary(held_target,"file");integrity._ordinary(current_target,"file")
        _need((held_target.st_dev,held_target.st_ino)==target_identity==(current_target.st_dev,current_target.st_ino))
        _need(held_target.st_size==current_target.st_size==count)
    finally:
        if target_fd is not None:os.close(target_fd)
        os.close(source_fd)


def materialize(plan_raw,external_plan_sha):
    """Copy an externally pinned canonical plan into the one fixed LS5 parent.

    No destination is created before complete plan/source recomputation. SHA
    proves bytes, not consent. Existing objects are never adopted or overwritten.
    """
    try:
        _need(type(plan_raw) is bytes and len(plan_raw)<=assembly.MAX_PLAN_BYTES)
        integrity._sha(external_plan_sha,64)
        _need(hashlib.sha256(plan_raw).hexdigest()==external_plan_sha)
        plan=json.loads(plan_raw.decode("ascii"),object_pairs_hook=integrity._pairs,
                        parse_constant=lambda _:(_ for _ in ()).throw(MaterializeError("MATERIALIZE_INVALID_JSON")))
        integrity._closed(plan,PLAN_FIELDS)
        _need(integrity._canonical(plan)==plan_raw)
        integrity._closed(plan["limits"],("max_files","max_bytes","max_visited_entries"))
        destination=_approved_destination(plan["destination"])
        recomputed=assembly.plan_assembly(plan["components"],destination,max_files=plan["limits"]["max_files"],max_bytes=plan["limits"]["max_bytes"])
        _need(integrity._canonical(recomputed)==plan_raw)
        parent_identity=_directory_identity(destination.parent)
        os.mkdir(destination,0o700)  # Exclusive creation; even an empty old root refuses.
        directories={destination:_directory_identity(destination)}
        for relative,record in sorted(plan["files"].items()):
            _need(_directory_identity(destination.parent)==parent_identity)
            directory=destination
            for part in Path(relative).parts[:-1]:
                _need(_directory_identity(directory)==directories[directory])
                directory=directory/part
                if directory not in directories:
                    os.mkdir(directory,0o700)
                    directories[directory]=_directory_identity(directory)
                else:_need(_directory_identity(directory)==directories[directory])
            _copy_file(Path(record["source_path"]),destination/relative,record)
        _need(_directory_identity(destination.parent)==parent_identity)
        _need(all(_directory_identity(path)==identity for path,identity in directories.items()))
        expected={name:{key:value[key] for key in ("bytes","sha256")} for name,value in plan["files"].items()}
        _need(integrity.snapshot_files(destination)==expected)
        return dict(status="COPIED_BYTES_ONLY",destination=str(destination),plan_sha256=external_plan_sha,
                    selected_file_count=len(expected),selected_bytes=plan["selected_bytes"],destination_parent_acl="EXTERNAL_ROOT_VERIFICATION_REQUIRED",
                    public_submit="DENY",runtime_admission=False,physical_execution_authorization=False)
    except (integrity.PackageError,assembly.AssemblyError,OSError,TypeError,ValueError,RuntimeError,OverflowError) as exc:
        if isinstance(exc,MaterializeError):raise
        raise MaterializeError("MATERIALIZE_REJECTED_PARTIAL_EVIDENCE_RETAINED") from exc
