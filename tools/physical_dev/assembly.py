"""Bounded read-only copy-plan DATA. No copying or execution is implemented.

Root must verify primary sources, admit a private destination parent, exclusively
create the destination and revalidate sources before any separately reviewed copy.
This helper supplies neither provenance nor an ACL/physical/native grant.
"""
import os
from pathlib import Path
import re
import stat

from . import package as integrity

MAX_COMPONENTS=32
MAX_ENTRIES=40000
MAX_PLAN_BYTES=32*1024*1024
PROFILES=("closed-tree","python-stdlib")


class AssemblyError(ValueError):
    pass


def _need(condition):
    if not condition:raise AssemblyError("ASSEMBLY_PLAN_REJECTED")


def _destination(raw):
    path=Path(raw)
    integrity._text(str(path),4096)
    _need(path.is_absolute())
    parent=integrity._directory(path.parent)
    integrity._relative(path.name)
    _need(str(path)==str(parent/path.name))
    try:path.lstat()
    except FileNotFoundError:return path
    raise AssemblyError("ASSEMBLY_DESTINATION_ALREADY_EXISTS")


def _skip(relative,is_directory,profile):
    if profile!="python-stdlib":return None
    parts=tuple(part.casefold() for part in relative.split("/"))
    if is_directory and parts==("lib","site-packages"):return "PYTHON_LIB_SITE_PACKAGES_SUBTREE"
    if is_directory and parts[-1]=="__pycache__":return "PYTHON_CACHE_SUBTREE"
    if not is_directory and Path(relative).suffix.casefold() in (".pyc",".pyo"):return "PYTHON_BYTECODE_FILE"
    return None


def _scan(root,profile,max_files,max_bytes,max_entries):
    pending=[root];files={};namespace={};aliases=set();skipped=[];visited=0;total=0
    while pending:
        directory=pending.pop();integrity._directory(directory)
        relative=directory.relative_to(root).as_posix()
        namespace[relative]=integrity._signature(directory.lstat())
        with os.scandir(directory) as entries:
            for entry in entries:
                visited+=1;_need(visited<=max_entries)
                path=directory/entry.name;relative=integrity._relative(path.relative_to(root).as_posix())
                _need(relative.casefold() not in aliases);aliases.add(relative.casefold())
                info=path.lstat();is_directory=stat.S_ISDIR(info.st_mode)
                integrity._ordinary(info,"directory" if is_directory else "file")
                identity=integrity._signature(info);namespace[relative]=identity
                reason=_skip(relative,is_directory,profile)
                if reason is not None:
                    skipped.append(dict(relative_path=relative,reason=reason,subtree=is_directory))
                elif is_directory:pending.append(path)
                else:
                    integrity._integer(info.st_size,0,max_bytes)
                    total+=info.st_size;_need(total<=max_bytes)
                    files[relative]=(path,identity);_need(len(files)<=max_files)
    return files,namespace,sorted(skipped,key=lambda item:item["relative_path"]),visited


def plan_assembly(components,destination,*,max_files=20000,max_bytes=1073741824):
    """Return a bounded plan without creating, copying or reserving anything.

    Components are closed {name,source_root,destination_prefix,profile} records.
    closed-tree includes all files (including hidden/.git). python-stdlib uses a
    full installation root and explicitly prunes Lib/site-packages, __pycache__
    directories and .pyc/.pyo files. All other files, including DLLs, are retained.
    Skipped subtree contents are not enumerated: counts are pruned-entry counts.
    """
    try:
        integrity._integer(max_files,1,integrity.MAX_FILES)
        integrity._integer(max_bytes,0,integrity.MAX_BYTES)
        _need(type(components) is list and 1<=len(components)<=MAX_COMPONENTS)
        destination=_destination(destination)
        checked=[];names=set()
        for component in components:
            integrity._closed(component,("name","source_root","destination_prefix","profile"))
            name=component["name"]
            _need(type(name) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}",name) is not None)
            _need(name.casefold() not in names);names.add(name.casefold())
            _need(type(component["profile"]) is str and component["profile"] in PROFILES)
            source=integrity._directory(component["source_root"])
            prefix=integrity._relative(component["destination_prefix"])
            _need(destination!=source and source not in destination.parents and destination not in source.parents)
            for prior in checked:
                other=Path(prior["source_root"])
                _need(source!=other and source not in other.parents and other not in source.parents)
            checked.append(dict(name=name,source_root=str(source),destination_prefix=prefix,profile=component["profile"]))
        checked.sort(key=lambda item:item["name"])
        files={};skipped=[];visited=0;total=0;counts=[];snapshots=[]
        for component in checked:
            root=Path(component["source_root"]);remaining_files=max_files-len(files);remaining_bytes=max_bytes-total
            before,namespace,omissions,entries=_scan(root,component["profile"],remaining_files,remaining_bytes,MAX_ENTRIES-visited)
            visited+=entries;selected_bytes=0
            for relative,(path,identity) in sorted(before.items()):
                record=integrity._hash_file(path,identity);selected_bytes+=record["bytes"]
                name=component["destination_prefix"]+"/"+relative
                integrity._relative(name)
                # Prefix directories may be shared, but no source may shadow
                # a prior final file, even when both files have identical bytes.
                _need(name not in files)
                files[name]=dict(source_path=str(path),**record)
            snapshots.append((root,component["profile"],remaining_files,remaining_bytes,MAX_ENTRIES-visited+entries,before,namespace,omissions))
            total+=selected_bytes
            component_skips=[dict(component=component["name"],**entry) for entry in omissions]
            skipped.extend(component_skips)
            counts.append(dict(name=component["name"],selected_file_count=len(before),selected_bytes=selected_bytes,
                               skipped_entry_count=len(omissions),skipped_subtree_count=sum(item["subtree"] for item in omissions)))
        # Recheck all components after all hashing, so a later component cannot
        # mask ordinary mutation of an earlier already-hashed source tree.
        for root,profile,file_limit,byte_limit,entry_limit,before,namespace,omissions in snapshots:
            after,after_namespace,after_omissions,_=_scan(root,profile,file_limit,byte_limit,entry_limit)
            _need(before==after and namespace==after_namespace and omissions==after_omissions)
        # Reuse the existing file-table namespace/type/size contract. No Git
        # provenance or approval is inferred from these descriptive hashes.
        integrity._files({name:{key:value[key] for key in ("bytes","sha256")} for name,value in files.items()})
        _need(_destination(destination)==destination)
        plan=dict(schema="unified.physical-dev-assembly-plan.v1",mode="COPY_PLAN_DATA_ONLY",destination=str(destination),
                  components=checked,files=files,component_counts=counts,selected_file_count=len(files),selected_bytes=total,
                  skipped=skipped,skipped_entry_count=len(skipped),skipped_subtree_count=sum(item["subtree"] for item in skipped),
                  visited_entry_count=visited,limits=dict(max_files=max_files,max_bytes=max_bytes,max_visited_entries=MAX_ENTRIES),
                  source_provenance="ROOT_PRIMARY_VERIFIER_REQUIRED",destination_parent_acl="UNKNOWN",
                  requires_exclusive_destination_creation=True,public_submit="DENY",runtime_admission=False,physical_execution_authorization=False)
        _need(len(integrity._canonical(plan))<=MAX_PLAN_BYTES)
        return plan
    except (integrity.PackageError,OSError,TypeError,RuntimeError,OverflowError) as exc:
        raise AssemblyError("ASSEMBLY_PLAN_REJECTED") from exc
