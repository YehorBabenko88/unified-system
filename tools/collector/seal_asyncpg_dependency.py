"""Closed asyncpg0.32 DATA materializer, never a resolver/runtime grant.

Real artifact use/materialization requires external PhaseA allocation; import and
client execution require separate Root units. Inert fixtures exercise private
archive/data logic only and cannot pass the hard-coded real-wheel gate.
"""
import base64
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

NAME = 'asyncpg-0.32.0-cp312-cp312-win_amd64.whl'
WHEEL_SHA256 = 'cd7157a86817730c3239bc687abf8186a471525d695e225c187b9a523a808a98'
WHEEL_BYTES = 626763
MAX_ARCHIVE = 8*1024*1024
MAX_EXPANDED = 32*1024*1024
MARKER = 'collector-asyncpg-dependency.v1.json'
NATIVE = ('asyncpg/pgproto/pgproto.cp312-win_amd64.pyd',
          'asyncpg/protocol/protocol.cp312-win_amd64.pyd',
          'asyncpg/protocol/record.cp312-win_amd64.pyd')


def _need(ok, code='ASYNCPG_DEPENDENCY_REJECTED'):
    if not ok: raise ValueError(code)


def _sha(value):
    _need(type(value) is str and re.fullmatch('[0-9a-f]{64}',value) is not None)


def _local(path):
    _need(type(path) in (str,type(Path())))
    text=str(path)
    _need(not text.startswith(('\\','//')))
    path=Path(path)
    _need(path.is_absolute() and '..' not in path.parts)
    return path


def _canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')


def _archive_inventory(raw):
    """Closed package CPU parser; arbitrary fixtures are NOT admitted wheels."""
    _need(type(raw) is bytes and 0<len(raw)<=MAX_ARCHIVE)
    from unified_system.windows_wheels import central_directory,zip_path,inspect_wheel
    stream=io.BytesIO(raw)
    count=central_directory(stream,len(raw)); _need(count<=512)
    with zipfile.ZipFile(stream) as archive:
        infos=archive.infolist()
        _need(len(infos)==count and sum(i.file_size for i in infos)<=MAX_EXPANDED)
        inspect_wheel(stream,len(raw),'asyncpg','0.32.0',{'cp312-cp312-win_amd64'})
        paths={}
        for info in infos:
            name,parts=zip_path(info)
            _need(parts[0] in ('asyncpg','asyncpg-0.32.0.dist-info'))
            _need(not name.lower().endswith(('.pth','.pyc','.pyo')))
            if not info.is_dir(): paths[name]=info
        native={name for name in paths if name.lower().endswith(('.pyd','.dll','.exe','.so','.dylib'))}
        _need(native==set(NATIVE))
        record='asyncpg-0.32.0.dist-info/RECORD'
        _need(record in paths and paths[record].file_size<=1048576)
        rows=list(csv.reader(io.StringIO(archive.read(record).decode('utf-8'),newline='')))
        _need(1<=len(rows)<=512)
        seen=set(); payloads=[]
        for row in rows:
            _need(len(row)==3)
            name,expected,size=row
            _need(name in paths and name not in seen); seen.add(name)
            data=archive.read(paths[name]); _need(len(data)==paths[name].file_size)
            digest=hashlib.sha256(data).digest()
            if name==record: _need(expected==size=='')
            else:
                _need(size==str(len(data)))
                _need(expected=='sha256='+base64.urlsafe_b64encode(digest).decode('ascii').rstrip('='))
            payloads.append((name,data,digest.hex()))
        _need(seen==set(paths))
    return tuple(sorted(payloads))


def inspect_asyncpg_wheel(raw):
    _need(type(raw) is bytes and len(raw)==WHEEL_BYTES)
    _need(hashlib.sha256(raw).hexdigest()==WHEEL_SHA256)
    return _archive_inventory(raw)


def _layout(inventory):
    from unified_system.windows_wheels import zip_path
    _need(type(inventory) is tuple and 1<=len(inventory)<=512)
    files={}; directories=set(); total=0
    for row in inventory:
        _need(type(row) is tuple and len(row)==3)
        name,data,sha=row
        _need(type(name) is str and type(data) is bytes); _sha(sha)
        path,parts=zip_path(zipfile.ZipInfo(name))
        _need(path==name and parts[0] in ('asyncpg','asyncpg-0.32.0.dist-info'))
        _need(name not in files and hashlib.sha256(data).hexdigest()==sha)
        files[name]=(data,sha);total+=len(data);_need(total<=MAX_EXPANDED)
        directories.update('/'.join(parts[:i]) for i in range(1,len(parts)))
    _need(len(files)+len(directories)<=1024 and not set(files)&directories)
    return files,directories


def _marker(root,inventory,wheel_sha):
    from unified_system.storage.object_store import _plain
    info=_plain(root,directory=True)
    return _canonical(dict(schema='unified.collector.asyncpg-dependency.v1',
        scope='DATA_ONLY_NOT_RUNTIME_ADMITTED',wheel_sha256=wheel_sha,root=str(root),
        root_identity=[info.st_dev,info.st_ino],members=[[name,len(data),sha] for name,data,sha in inventory],
        native_imported=False,runtime_admitted=False,publisher_authenticated=False))


def _materialize(destination,inventory,wheel_sha):
    """Private inert/data writer; not a proof that its input is the real wheel."""
    _sha(wheel_sha);files,directories=_layout(inventory);root=_local(destination)
    from unified_system.storage.object_store import _parents,_write_new
    _parents(root.parent);root.mkdir(exist_ok=False)
    for name in sorted(directories,key=lambda value:(value.count('/'),value)):
        (root/name).mkdir(exist_ok=False)
    for name,(data,_) in files.items(): _write_new(root/name,data)
    _write_new(root/MARKER,_marker(root,inventory,wheel_sha))
    return _verify_inventory(root,inventory,wheel_sha)


def _verify_inventory(root,inventory,wheel_sha):
    _sha(wheel_sha);files,directories=_layout(inventory);root=_local(root)
    from unified_system.storage.object_store import _parents,_plain,_read
    _parents(root)
    expected=set(files)|{MARKER};found=set();dirs=set();stack=[root];identities=[]
    while stack:
        folder=stack.pop();info=_plain(folder,directory=True)
        identities.append((folder,info.st_dev,info.st_ino,info.st_mtime_ns))
        for path in folder.iterdir():
            name=path.relative_to(root).as_posix()
            _need(len(found)+len(dirs)<1025)
            if name in directories:
                _plain(path,directory=True);dirs.add(name);stack.append(path)
            else:
                _need(name in expected);_plain(path,directory=False);found.add(name)
    _need(found==expected and dirs==directories)
    _need(_read(root/MARKER,1048576)[0]==_marker(root,inventory,wheel_sha))
    for name,(data,sha) in files.items():
        actual,_=_read(root/name,len(data))
        _need(len(actual)==len(data) and hashlib.sha256(actual).hexdigest()==sha)
    for folder,dev,ino,mtime in identities:
        info=_plain(folder,directory=True)
        _need((info.st_dev,info.st_ino,info.st_mtime_ns)==(dev,ino,mtime))
    return dict(scope='DATA_ONLY_NOT_RUNTIME_ADMITTED',wheel_sha256=wheel_sha,
        member_count=len(files),expanded_bytes=sum(len(data) for data,_ in files.values()),
        native_imported=False,runtime_admitted=False,publisher_authenticated=False)


def _real_inventory(wheel_path):
    from unified_system.storage.object_store import _parents,_read
    path=_local(wheel_path);_parents(path.parent)
    raw,_=_read(path,MAX_ARCHIVE)
    return inspect_asyncpg_wheel(raw)


def seal_asyncpg_dependency(wheel_path,destination):
    """Future PhaseA only. Never install to site/global paths or invoke setup."""
    inventory=_real_inventory(wheel_path)  # Hard real-wheel gate BEFORE any write.
    return _materialize(destination,inventory,WHEEL_SHA256)


def verify_sealed_dependency(wheel_path,root):
    """Rebind to actual pinned wheel, not a caller-created inventory/True flag."""
    inventory=_real_inventory(wheel_path)
    return _verify_inventory(root,inventory,WHEEL_SHA256)
