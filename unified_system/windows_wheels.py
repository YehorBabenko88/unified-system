"""Offline Windows CPython312 wheel candidate integrity, never installation.

No dependency resolver, package import, network, extraction or execution lives
here. The lock and this validator require independent external admission.
"""
import argparse
from contextlib import contextmanager
from email.parser import BytesParser
from email.policy import default as email_policy
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import stat
import struct
import zipfile

from .owned_python import reject_external_namespace
from .runtime_process import _safe_path

LOCK_LIMIT=4*1024*1024
WHEEL_LIMIT=1024*1024*1024
TOTAL_LIMIT=2*WHEEL_LIMIT
META_LIMIT=1024*1024


class WheelValidationError(ValueError):pass


def need(ok,code):
    if not ok:raise WheelValidationError(code)


def canonical(name):return re.sub('[-_.]+','-',name).lower()


def local(path):
    reject_external_namespace(str(path))
    need(Path(path).is_absolute(),'LOCAL_NAMESPACE_REJECTED')
    return _safe_path(path)


def identity(s):return (s.st_dev,s.st_ino,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)


@contextmanager
def opened(path,maximum):
    path=local(path);before=path.lstat()
    need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and 0<before.st_size<=maximum,'LOCAL_FILE_UNVERIFIED')
    fd=os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0))
    with os.fdopen(fd,'rb') as f:
        current=os.fstat(f.fileno());need(stat.S_ISREG(current.st_mode) and identity(current)==identity(before),'LOCAL_FILE_CHANGED')
        yield f
        need(identity(os.fstat(f.fileno()))==identity(before) and identity(local(path).lstat())==identity(before),'LOCAL_FILE_CHANGED')


def parse_compiled_lock(raw):
    """Parse only fully pinned hash records, not pip options or PEP508 syntax."""
    need(type(raw) is bytes and 0<len(raw)<=LOCK_LIMIT,'LOCK_INVALID')
    try:text=raw.decode('utf-8',errors='strict')
    except UnicodeError:raise WheelValidationError('LOCK_INVALID') from None
    need(not re.search('[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]',text),'LOCK_INVALID')
    records=[];pending=''
    for line in text.splitlines():
        need(len(line)<=16384,'LOCK_INVALID');line=line.strip()
        if not line or line.startswith('#'):continue
        continued=line.endswith('\\');line=line[:-1].rstrip() if continued else line
        pending+=((' ' if pending else '')+line)
        need(len(pending)<=1024*1024,'LOCK_INVALID')
        if not continued:records.append(pending);pending=''
    need(not pending and 1<=len(records)<=512,'LOCK_INVALID')
    result={}
    for record in records:
        m=re.fullmatch(r'([A-Za-z0-9][A-Za-z0-9._-]{0,127})==([0-9][A-Za-z0-9.!+_-]{0,127})((?:[ \t]+--hash=sha256:[a-f0-9]{64})+)',record)
        need(m is not None,'LOCK_INVALID')
        name=canonical(m[1]);hashes=re.findall('--hash=sha256:([a-f0-9]{64})',m[3])
        need(name not in result and len(hashes)<=4096 and len(hashes)==len(set(hashes)),'LOCK_INVALID')
        result[name]={'version':m[2],'hashes':set(hashes)}
    return result


def filename_identity(filename):
    need(type(filename) is str and len(filename)<=255 and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.+!-]*[.]whl',filename),'WHEEL_FILENAME_INVALID')
    parts=filename[:-4].split('-');need(len(parts) in (5,6),'WHEEL_FILENAME_INVALID')
    name,version=parts[:2]
    need(re.fullmatch('[A-Za-z0-9][A-Za-z0-9._]*',name) and re.fullmatch('[0-9][A-Za-z0-9.!+_]*',version),'WHEEL_FILENAME_INVALID')
    if len(parts)==6:need(re.fullmatch('[0-9][A-Za-z0-9_]*',parts[2]),'WHEEL_FILENAME_INVALID')
    groups=[p.split('.') for p in parts[-3:]]
    need(all(1<=len(g)<=8 and all(re.fullmatch('[a-z0-9_]{1,64}',v) for v in g) for g in groups),'WHEEL_TAG_INVALID')
    tags={'-'.join(t) for t in itertools.product(*groups)};need(len(tags)<=64,'WHEEL_TAG_INVALID')
    return canonical(name),version,tags


def compatible(tags):
    """Conservative Windows312 subset; not a general packaging.tags engine."""
    accepted=False
    for tag in tags:
        m=re.fullmatch(r'([a-z0-9]+)-(none|abi3|cp312)-(any|win_amd64)',tag)
        if not m:return False
        python,abi,platform=m.groups()
        if python=='py2':
            if tag!='py2-none-any' or 'py3-none-any' not in tags:return False
        elif python in ('py3','py312') and abi=='none':accepted=True
        elif python=='cp312' and abi in ('cp312','none') and platform=='win_amd64':accepted=True
        elif re.fullmatch(r'cp3[0-9]{1,2}',python) and abi=='abi3' and platform=='win_amd64' and 2<=int(python[3:])<=12:accepted=True
        else:return False
    return accepted


def central_directory(f,size):
    # Bound ZipFile's central-directory allocation before constructing it.
    f.seek(max(0,size-65557));tail=f.read(65557);position=tail.rfind(b'PK\x05\x06')
    need(position>=0 and len(tail)-position>=22,'ZIP_DIRECTORY_INVALID')
    values=struct.unpack('<4s4H2LH',tail[position:position+22])
    _,disk,start_disk,count_disk,count,cd_size,cd_offset,comment=values
    eocd=size-len(tail)+position
    need(disk==start_disk==0 and count==count_disk and 1<=count<=20000 and cd_size<=16*1024*1024
         and cd_offset+cd_size==eocd and position+22+comment==len(tail),'ZIP_DIRECTORY_INVALID')
    f.seek(0);need(f.read(4)==b'PK\x03\x04','ZIP_DIRECTORY_INVALID');f.seek(0)
    return count


def zip_path(info):
    name=info.orig_filename
    need(type(name) is str and 0<len(name)<=512 and all(32<=ord(c)<127 for c in name)
         and not name.startswith('/') and not any(c in name for c in '\\:'),'ZIP_PATH_INVALID')
    path=name[:-1] if name.endswith('/') else name;parts=path.split('/')
    devices={'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))}
    need(all(p and p not in ('.','..') and not p.endswith((' ','.')) and p.split('.')[0].upper() not in devices for p in parts),'ZIP_PATH_INVALID')
    mode=stat.S_IFMT(info.external_attr>>16)
    need(mode in (0,stat.S_IFREG,stat.S_IFDIR) and (mode!=stat.S_IFDIR or info.is_dir())
         and (mode!=stat.S_IFREG or not info.is_dir()) and not info.flag_bits&1 and not info.external_attr&0x400
         and info.compress_type in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED),'ZIP_ENTRY_INVALID')
    need(info.file_size<=512*1024*1024 and info.compress_size>=0 and (not info.is_dir() or info.file_size==0),'ZIP_ENTRY_INVALID')
    return path,parts


def header(data):
    need(0<len(data)<=META_LIMIT and max(map(len,data.splitlines()),default=0)<=16384,'WHEEL_METADATA_INVALID')
    try:data.decode('utf-8',errors='strict');message=BytesParser(policy=email_policy).parsebytes(data)
    except (UnicodeError,ValueError):raise WheelValidationError('WHEEL_METADATA_INVALID') from None
    need(not message.defects,'WHEEL_METADATA_INVALID');return message


def single(message,key):
    values=[value for name,value in message.raw_items() if name.lower()==key.lower()]
    need(len(values)==1,'WHEEL_METADATA_INVALID')
    value=values[0];need(value and not re.search('[\x00-\x1f\x7f]',value),'WHEEL_METADATA_INVALID');return value


def inspect_wheel(f,size,name,version,filename_tags):
    count=central_directory(f,size)
    with zipfile.ZipFile(f,'r') as archive:
        entries=archive.infolist();need(len(entries)==count,'ZIP_DIRECTORY_INVALID')
        paths={};roots=set();expanded=0
        for info in entries:
            path,parts=zip_path(info);key=path.casefold();need(key not in paths,'ZIP_PATH_INVALID')
            paths[key]=info;expanded+=info.file_size;need(expanded<=TOTAL_LIMIT,'ZIP_ENTRY_INVALID')
            # Only a top-level dist-info tree defines this wheel's identity.
            # Vendored package metadata remains ordinary bounded archive data.
            if parts[0].lower().endswith('.dist-info'):roots.add(parts[0])
            # A .data purelib/platlib remap must not mint a second top-level
            # identity at install time. Deeper vendor metadata is still data.
            if len(parts)>=3 and parts[0].lower().endswith('.data') and parts[1].lower() in ('purelib','platlib'):
                need(not parts[2].lower().endswith('.dist-info'),'WHEEL_METADATA_INVALID')
        for path in paths:
            parts=path.split('/')
            for i in range(1,len(parts)):
                parent=paths.get('/'.join(parts[:i]));need(parent is None or parent.is_dir(),'ZIP_PATH_INVALID')
        need(len(roots)==1,'WHEEL_METADATA_INVALID');root=next(iter(roots));dist=root[:-10].rsplit('-',1)
        need(len(dist)==2 and canonical(dist[0])==name and dist[1]==version,'WHEEL_METADATA_INVALID')
        parsed=[]
        for leaf in ('METADATA','WHEEL'):
            target=root+'/'+leaf;info=paths.get(target.casefold())
            need(info is not None and info.filename==target and not info.is_dir() and 0<info.file_size<=META_LIMIT,'WHEEL_METADATA_INVALID')
            with archive.open(info) as member:data=member.read(META_LIMIT+1)
            need(len(data)==info.file_size,'WHEEL_METADATA_INVALID');parsed.append(header(data))
        metadata,wheel=parsed
        need(canonical(single(metadata,'Name'))==name and single(metadata,'Version')==version,'WHEEL_METADATA_INVALID')
        need(re.fullmatch(r'2[.][0-9]+',single(metadata,'Metadata-Version')),'WHEEL_METADATA_INVALID')
        need(single(wheel,'Wheel-Version')=='1.0' and single(wheel,'Root-Is-Purelib') in ('true','false'),'WHEEL_METADATA_INVALID')
        tags=[str(v) for v in wheel.get_all('Tag',[])]
        need(1<=len(tags)<=64 and len(tags)==len(set(tags)) and set(tags)==filename_tags and compatible(set(tags)),'WHEEL_TAG_INVALID')


def validate_windows_wheels(lock_path,wheel_dir):
    report=dict(schema='unified.windows.wheel-candidate.v1',result='BLOCKED',scope='OFFLINE_CANDIDATE_BYTE_INTEGRITY_ONLY',
        dependency_closure_verified=False,installation_closure=False,publisher_authenticated=False,execution_authority=False,
        native_execution='NOT_RUN',physical='NOT_RUN',wheels=[])
    try:
        root=local(wheel_dir);need(root.is_dir(),'LOCAL_NAMESPACE_REJECTED')
        with opened(lock_path,LOCK_LIMIT) as f:raw=f.read(LOCK_LIMIT+1)
        pinned=parse_compiled_lock(raw);report['lock_sha256']=hashlib.sha256(raw).hexdigest();report['pinned_distributions']=len(pinned)
        entries=[]
        with os.scandir(root) as directory:
            for entry in directory:
                entries.append(entry.name);need(len(entries)<=512,'WHEEL_INVENTORY_INVALID')
        wheels={}
        for filename in sorted(entries):
            name,version,tags=filename_identity(filename)
            need(name in pinned and name not in wheels and pinned[name]['version']==version,'WHEEL_INVENTORY_INVALID')
            wheels[name]=(filename,version,tags)
        need(set(wheels)==set(pinned),'WHEEL_INVENTORY_INVALID');total=0
        for name,(filename,version,tags) in sorted(wheels.items()):
            with opened(root/filename,WHEEL_LIMIT) as f:
                size=os.fstat(f.fileno()).st_size;total+=size;need(total<=TOTAL_LIMIT,'WHEEL_SIZE_BOUND')
                h=hashlib.sha256();read=0
                while True:
                    chunk=f.read(min(1048576,WHEEL_LIMIT-read+1))
                    if not chunk:break
                    read+=len(chunk);need(read<=WHEEL_LIMIT,'WHEEL_SIZE_BOUND');h.update(chunk)
                need(read==size,'LOCAL_FILE_CHANGED');digest=h.hexdigest();need(digest in pinned[name]['hashes'],'WHEEL_HASH_MISMATCH')
                inspect_wheel(f,size,name,version,tags)
            report['wheels'].append(dict(name=name,version=version,filename=filename,sha256=digest,bytes=size))
        report.update(result='CANDIDATE_BYTES_MATCH',candidate_bytes=total)
    except WheelValidationError as exc:report['reason']=str(exc)
    except (OSError,ValueError,KeyError,zipfile.BadZipFile,RuntimeError,NotImplementedError):report['reason']='LOCAL_INPUT_UNVERIFIED'
    return report


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--lock',required=True);p.add_argument('--wheel-dir',required=True);args=p.parse_args(argv)
    report=validate_windows_wheels(args.lock,args.wheel_dir);print(json.dumps(report,sort_keys=True))
    return 0 if report['result']=='CANDIDATE_BYTES_MATCH' else 1


if __name__=='__main__':raise SystemExit(main())
