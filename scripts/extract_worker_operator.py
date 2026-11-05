"""Independently pin this stdlib-only script before isolated raw execution.

Verify an externally pinned operator bundle and lock completely before creating
one NEW output root. Extract data only; never import or execute archive content.
Failures retain fresh output for inspection. Existing targets are never reused.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import sys
import zipfile

MAX_ARCHIVE=18*1024*1024
MAX_TOTAL=17*1024*1024
MAX_MEMBER=1024*1024


def need(ok):
    if not ok:raise ValueError('OPERATOR_BUNDLE_REJECTED')


def pin(value):need(type(value) is str and re.fullmatch('[a-f0-9]{64}',value))


def relative(name):
    need(type(name) is str and 0<len(name)<=240)
    parts=name.split('/')
    need(all(re.fullmatch('[A-Za-z0-9_.-]+',p) and p not in ('','.', '..') and not p.endswith('.')
        and p.casefold()!='__pycache__' and not re.match(r'(?i)^(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])(?:[.]|$)',p) for p in parts))
    return name


def local(path):
    path=Path(path);need(path.is_absolute() and not str(path).startswith(('\\\\','//')))
    for part in path.parts[1:]:
        need(part not in ('.','..') and not part.endswith((' ','.')) and ':' not in part
            and not re.match(r'(?i)^(CON|PRN|AUX|NUL|COM[0-9\u00b9\u00b2\u00b3]|LPT[0-9\u00b9\u00b2\u00b3]) *(?:[.]|$)',part))
    for ancestor in (*reversed(path.parents),path):
        try:info=ancestor.lstat()
        except FileNotFoundError:continue
        need(not stat.S_ISLNK(info.st_mode) and not getattr(info,'st_file_attributes',0)&1024)
    need(path.resolve(strict=False)==path)
    return path


def bytes_file(path,limit):
    path=local(path)
    with path.open('rb') as stream:
        before=os.fstat(stream.fileno());need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and 0<before.st_size<=limit)
        raw=stream.read(limit+1);after=os.fstat(stream.fileno());current=path.lstat()
        fields=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_nlink)
        need(len(raw)==before.st_size and fields(before)==fields(after)==fields(current))
        return raw


def unique(pairs):
    result={}
    for key,value in pairs:need(key not in result);result[key]=value
    return result


def extract(archive,archive_sha256,lock_sha256,target):
    pin(archive_sha256);pin(lock_sha256);target=local(target)
    need(not target.exists() and target.parent.is_dir())
    raw=bytes_file(archive,MAX_ARCHIVE);need(hashlib.sha256(raw).hexdigest()==archive_sha256)
    payloads={};folded=set();total=0
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        need(not z.comment and 2<=len(z.infolist())<=501)
        for info in z.infolist():
            name=relative(info.filename)
            need(not info.is_dir() and name.casefold() not in folded and info.create_system==3
                and info.external_attr==0o100600<<16 and not info.extra and not info.comment
                and info.compress_type==zipfile.ZIP_DEFLATED and not info.flag_bits&~(8|0x800))
            folded.add(name.casefold());need(0<info.file_size<=MAX_MEMBER);total+=info.file_size;need(total<=MAX_TOTAL)
            with z.open(info) as source:data=source.read(MAX_MEMBER+1)
            need(len(data)==info.file_size);payloads[name]=data
    need('operator-lock.json' in payloads)
    lock_raw=payloads['operator-lock.json'];need(hashlib.sha256(lock_raw).hexdigest()==lock_sha256)
    policy=json.loads(lock_raw,object_pairs_hook=unique)
    need(type(policy) is dict and set(policy)=={'schema','files','source_manifest_sha256s'} and policy['schema']=='unified.worker-operator.v1')
    files=policy['files'];allowed=policy['source_manifest_sha256s']
    need(type(files) is dict and 1<=len(files)<=500 and type(allowed) is list and 1<=len(allowed)<=16)
    for value in allowed:pin(value)
    need(allowed==sorted(set(allowed)))
    required={'scripts/prepare_worker_capsule.py','integration/source_guard.py','unified_system/__init__.py',
              'unified_system/lab_release.py','unified_system/lab_runtime.py','unified_system/lab_capsule_acl.py'}
    need(required<=set(files))
    names=set();folded=set()
    for name,digest in files.items():
        relative(name);pin(digest)
        need(re.fullmatch(r'(?:unified_system/[A-Za-z0-9_/]+[.]py|integration/source_guard[.]py|scripts/prepare_worker_capsule[.]py)',name)
            and name.casefold() not in folded)
        folded.add(name.casefold());names.add('operator/'+name)
        need('operator/'+name in payloads and hashlib.sha256(payloads['operator/'+name]).hexdigest()==digest)
    need(set(payloads)==names|{'operator-lock.json'})
    # Only verified immutable bytes enter this newly created directory.
    target.mkdir(exist_ok=False)
    for name,data in payloads.items():
        path=local(target/name);path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as output:output.write(data);output.flush();os.fsync(output.fileno())
    actual={p.relative_to(target).as_posix() for p in target.rglob('*') if p.is_file()}
    need(actual==set(payloads))
    for name,data in payloads.items():need(bytes_file(target/name,MAX_MEMBER)==data)
    return dict(result='VERIFIED_OPERATOR_DATA_EXTRACTED',files=len(payloads),archive_sha256=archive_sha256,
        operator_lock_sha256=lock_sha256,operator_script_sha256=files['scripts/prepare_worker_capsule.py'],
        operator_root=str(target/'operator'),operator_lock=str(target/'operator-lock.json'),execution='NOT_STARTED')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('archive','archive-sha256','lock-sha256','target'):parser.add_argument('--'+name,required=True)
    args=parser.parse_args(argv)
    try:
        need(sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode)
        result=extract(args.archive,args.archive_sha256,args.lock_sha256,args.target)
        print(json.dumps(result,sort_keys=True));return 0
    except Exception:print('OPERATOR_BUNDLE_REJECTED');return 1


if __name__=='__main__':raise SystemExit(main())
