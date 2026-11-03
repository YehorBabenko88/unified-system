"""Unsigned owner-admitted LAB capsules, separate from trusted-publisher releases.

The external manifest digest and bootstrap/runtime admission are caller policy.
Integrity here is not public trust, execution permission or host attestation.
No candidate code is imported, no archive is executed, no security policy changes.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat

from .module_catalog import MODULE_IDS
from .runtime_process import _safe_path

LIMIT=32*1024*1024
FILE_LIMIT=512*1024*1024
TOTAL_LIMIT=8*1024*1024*1024
REPOSITORIES={n:'YehorBabenko88/'+{'grid':'bybit-cluster-grid','terminan':'Terminan'}.get(n,n) for n in MODULE_IDS}


def need(ok):
    if not ok:raise ValueError('LAB_CAPSULE_REJECTED')


def canonical(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()


def exact(value,keys):need(type(value) is dict and set(value)==set(keys))
def digest(value,n=64):need(type(value) is str and re.fullmatch('[a-f0-9]{'+str(n)+'}',value))


def relative(value):
    need(type(value) is str and 0<len(value)<=240 and not value.startswith('/'))
    for p in value.split('/'):
        need(re.fullmatch('[A-Za-z0-9_.@+-]+',p) and p not in ('.','..') and not p.endswith('.')
             and not re.match(r'(?i)^(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])(?:\.|$)',p))
    return value


def regular(path):
    p=_safe_path(path);s=p.lstat()
    need(stat.S_ISREG(s.st_mode) and s.st_nlink==1 and 0<=s.st_size<=FILE_LIMIT)
    return p


def hash_file(path,*,copy_to=None):
    path=regular(path);h=hashlib.sha256();count=0
    with path.open('rb') as src:
        before=os.fstat(src.fileno())
        out=None
        try:
            if copy_to is not None:out=copy_to.open('xb')
            for block in iter(lambda:src.read(1024*1024),b''):
                count+=len(block);need(count<=FILE_LIMIT);h.update(block)
                if out is not None:out.write(block)
            if out is not None:out.flush();os.fsync(out.fileno())
        finally:
            if out is not None:out.close()
        after=os.fstat(src.fileno());current=path.lstat()
        fields=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_nlink)
        # Windows fstat/path stat can round creation-time differently. Retain
        # the handle's change-time check, compare path identity/mtime/size.
        need(fields(before)==fields(after)==fields(current) and before.st_ctime_ns==after.st_ctime_ns and count==before.st_size)
    return {'sha256':h.hexdigest(),'bytes':count}


def parse_manifest(raw,expected_sha256):
    digest(expected_sha256);need(type(raw) is bytes and 0<len(raw)<=LIMIT)
    need(hashlib.sha256(raw).hexdigest()==expected_sha256)
    def unique(pairs):
        out={}
        for k,v in pairs:need(k not in out);out[k]=v
        return out
    m=json.loads(raw.decode('utf8'),object_pairs_hook=unique,parse_constant=lambda _:need(False))
    need(canonical(m)==raw)
    exact(m,('schema','mode','release_id','sequence','market_access','execution','credentials',
             'trading_authorized','sources','files','directories','dependencies','runtime_config','git','instruments'))
    need(m['schema']=='unified.lab-release.v1' and m['mode']=='LAB_SIMULATION')
    need(m['market_access']=='PUBLIC_READ_ONLY' and m['execution']=='PAPER_ONLY'
         and m['credentials']=='FORBIDDEN' and m['trading_authorized'] is False)
    need(type(m['instruments']) is list and len(m['instruments'])==10
         and all(type(s) is str and re.fullmatch('[A-Z0-9]{2,24}USDT',s) for s in m['instruments'])
         and len(set(m['instruments']))==10)
    need(type(m['release_id']) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,79}',m['release_id']))
    need(type(m['sequence']) is int and 1<=m['sequence']<=2**53-1)
    need(type(m['files']) is dict and 1<=len(m['files'])<=100000)
    seen=set();total=0
    for name,pin in m['files'].items():
        relative(name);need(name.casefold()!='lab-release.json' and name.casefold() not in seen);seen.add(name.casefold())
        need(Path(name).name.casefold() not in ('.env','.env.local','.env.production'))
        exact(pin,('sha256','bytes'));digest(pin['sha256'])
        need(type(pin['bytes']) is int and 0<=pin['bytes']<=FILE_LIMIT);total+=pin['bytes']
    need(total<=TOTAL_LIMIT)
    dirs=m['directories'];need(type(dirs) is list and len(dirs)<=100000 and dirs==sorted(set(dirs)))
    seen_dirs=set()
    for name in dirs:
        relative(name);need(name.casefold() not in seen and name.casefold() not in seen_dirs);seen_dirs.add(name.casefold())
    for name in list(m['files'])+dirs:
        need(all(p.as_posix() in dirs for p in Path(name).parents if str(p)!='.'))
    for key in ('runtime_config','git'):relative(m[key]);need(m[key] in m['files'])
    need(type(m['sources']) is dict and set(m['sources'])==MODULE_IDS)
    for name,s in m['sources'].items():
        exact(s,('repository','root','commit','tree','version','dependencies'))
        need(s['repository']==REPOSITORIES[name] and s['root']=='sources/'+name)
        digest(s['commit'],40);digest(s['tree'],40)
        need(type(s['version']) is str and re.fullmatch(r'\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]{1,40})?',s['version']))
        need(any(p.startswith(s['root']+'/') for p in m['files']))
        need(type(s['dependencies']) is dict and set(s['dependencies'])<=MODULE_IDS-{name})
        for dep,version in s['dependencies'].items():need(version==m['sources'][dep]['version'])
    visited=set();active=set()
    def visit(name):
        need(name not in active)
        if name in visited:return
        active.add(name)
        for dep in m['sources'][name]['dependencies']:visit(dep)
        active.remove(name);visited.add(name)
    for name in MODULE_IDS:visit(name)
    deps=m['dependencies'];need(type(deps) is list and 1<=len(deps)<=256)
    seen=set()
    for dep in deps:
        exact(dep,('name','version','lock_path'));relative(dep['name']);relative(dep['lock_path'])
        need(dep['name'].casefold() not in seen);seen.add(dep['name'].casefold())
        need(type(dep['version']) is str and re.fullmatch(r'[0-9][A-Za-z0-9_.+-]{0,79}',dep['version']))
        need(dep['lock_path'] in m['files'])
    return m


def verify_capsule(root,expected_sha256):
    need(Path(root).is_absolute())
    root=_safe_path(root).resolve();need(root.is_absolute() and root.is_dir())
    manifest=regular(root/'lab-release.json');need(manifest.stat().st_size<=LIMIT)
    raw=manifest.read_bytes();m=parse_manifest(raw,expected_sha256)
    found=set();directories=set();count=0
    for directory,dirs,files in os.walk(root,followlinks=False):
        _safe_path(directory)
        for name in dirs:
            p=_safe_path(Path(directory)/name);need(p.is_dir());directories.add(p.relative_to(root).as_posix())
        for name in files:
            p=regular(Path(directory)/name);rel=p.relative_to(root).as_posix();count+=1;need(count<=100001)
            if rel=='lab-release.json':continue
            need(rel in m['files'] and hash_file(p)==m['files'][rel]);found.add(rel)
    need(found==set(m['files']))
    # Git has intentional empty metadata directories; admit their exact names
    # explicitly rather than ignoring arbitrary unlisted empty namespaces.
    need(directories==set(m['directories']))
    need(manifest.read_bytes()==raw)
    return dict(mode='LAB_SIMULATION',manifest_sha256=expected_sha256,release_id=m['release_id'],
                publisher_trust='NOT_REQUIRED_FOR_LAB',files_verified=len(found),
                source_provenance='PINNED_METADATA_ONLY_VERIFY_SOURCES_BEFORE_EXECUTION',
                trading_authorized=False,execution='PAPER_ONLY',physical_acceptance='NOT_RUN',manifest=m)


def stage_capsule(source,target,expected_sha256):
    need(Path(source).is_absolute() and Path(target).is_absolute())
    source=_safe_path(source);target=_safe_path(target)
    need(source.is_absolute() and target.is_absolute() and not target.exists())
    need(source!=target and source not in target.parents and target not in source.parents)
    m=verify_capsule(source,expected_sha256)['manifest']
    target.mkdir(parents=False,exist_ok=False)
    for name in m['directories']:
        dest=target/name;_safe_path(dest);dest.mkdir(parents=True,exist_ok=True)
    for name,pin in m['files'].items():
        dest=target/name;dest.parent.mkdir(parents=True,exist_ok=True);_safe_path(dest)
        need(hash_file(source/name,copy_to=dest)==pin)
    raw=regular(source/'lab-release.json').read_bytes();parse_manifest(raw,expected_sha256)
    with (target/'lab-release.json').open('xb') as stream:stream.write(raw)
    # Failures leave a new, inactive directory for inspection; never delete or
    # replace an existing release or alter an active service.
    return verify_capsule(target,expected_sha256)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=('LAB_SIMULATION','TRUSTED_RELEASE'),required=True)
    p.add_argument('--root',required=True);p.add_argument('--manifest-sha256',required=True)
    p.add_argument('--stage-to');a=p.parse_args(argv)
    try:
        if a.mode=='TRUSTED_RELEASE':
            print('BLOCKED_NO_TRUSTED_PUBLISHER; lab verifier cannot admit trusted releases');return 1
        r=stage_capsule(a.root,a.stage_to,a.manifest_sha256) if a.stage_to else verify_capsule(a.root,a.manifest_sha256)
        r.pop('manifest');print(json.dumps(r,sort_keys=True));return 0
    except Exception:
        print('BLOCKED: LAB_CAPSULE_REJECTED');return 1


if __name__=='__main__':raise SystemExit(main())
