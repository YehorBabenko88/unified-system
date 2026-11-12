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
COLLECTOR_SCHEMA='unified.lab-release.collector.v1'
COLLECTOR_SOURCES=frozenset(('unified-system','grid'))
COLLECTOR_PERMISSIONS=frozenset(('provider_rest','provider_websocket','trading','training','math',
                               'public_submit','authority_mutation','service_creation','acl_changes'))


def need(ok):
    if not ok:raise ValueError('LAB_CAPSULE_REJECTED')


def canonical(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()


def exact(value,keys):need(type(value) is dict and set(value)==set(keys))
def digest(value,n=64):need(type(value) is str and re.fullmatch('[a-f0-9]{'+str(n)+'}',value))


def relative(value):
    need(type(value) is str and 0<len(value)<=240 and not value.startswith('/'))
    for p in value.split('/'):
        need(re.fullmatch('[A-Za-z0-9_.@+() -]+',p) and p not in ('.','..')
             and not p.startswith(' ') and not p.endswith((' ','.'))
             and not re.match(r'(?i)^(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9]) *(?:\.|$)',p))
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


def _parse_v1_manifest(raw,expected_sha256):
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


def _canonical_document(raw):
    def unique(pairs):
        out={}
        for key,value in pairs:need(key not in out);out[key]=value
        return out
    value=json.loads(raw.decode('utf8'),object_pairs_hook=unique,parse_constant=lambda _:need(False))
    need(canonical(value)==raw)
    return value


def _collector_pin_map(pins):
    need(type(pins) is dict and 1<=len(pins)<=100000)
    seen=set()
    for name,pin in pins.items():
        relative(name);need(name.casefold() not in seen);seen.add(name.casefold())
        exact(pin,('sha256','bytes','blob_oid'));digest(pin['sha256']);digest(pin['blob_oid'],40)
        need(type(pin['bytes']) is int and 0<=pin['bytes']<=FILE_LIMIT)


def _collector_source_files(m):
    """Final explicit source map; supplied commit/tree metadata is not attested."""
    need(type(m['sources']) is dict and set(m['sources'])==COLLECTOR_SOURCES)
    final={};entries=0
    for name,source in m['sources'].items():
        exact(source,('repository','root','commit','tree','version','dependencies','file_pins'))
        need(source['repository']==REPOSITORIES[name] and source['root']=='sources/'+name)
        digest(source['commit'],40);digest(source['tree'],40)
        need(type(source['version']) is str and re.fullmatch(r'\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]{1,40})?',source['version']))
        need(type(source['dependencies']) is dict and set(source['dependencies'])<=COLLECTOR_SOURCES-{name})
        for dep,version in source['dependencies'].items():need(version==m['sources'][dep]['version'])
        _collector_pin_map(source['file_pins']);entries+=len(source['file_pins'])
        final[name]=dict(source['file_pins'])
    active=set();visited=set()
    def visit(name):
        need(name not in active)
        if name in visited:return
        active.add(name)
        for dep in m['sources'][name]['dependencies']:visit(dep)
        active.remove(name);visited.add(name)
    for name in COLLECTOR_SOURCES:visit(name)
    need(type(m['overlays']) is list and len(m['overlays'])<=16)
    for overlay in m['overlays']:
        exact(overlay,('source','commit','tree','files'))
        need(type(overlay['source']) is str and overlay['source'] in COLLECTOR_SOURCES)
        digest(overlay['commit'],40);digest(overlay['tree'],40)
        _collector_pin_map(overlay['files']);entries+=len(overlay['files']);need(entries<=100000)
        final[overlay['source']].update(overlay['files'])
    need(entries<=100000)
    result={m['sources'][name]['root']+'/'+path:pin for name,pins in final.items() for path,pin in pins.items()}
    need(set(result)=={path for path in m['files'] if path.startswith('sources/')})
    for path,pin in result.items():need(m['files'][path]=={'sha256':pin['sha256'],'bytes':pin['bytes']})
    return result


def _parse_collector_manifest(m):
    exact(m,('schema','mode','release_id','sequence','permissions','sources','files','directories',
             'dependencies','collector_profile','source_manifest','git','runtime','overlays'))
    need(m['schema']==COLLECTOR_SCHEMA and m['mode']=='SYNTHETIC_OFFLINE')
    exact(m['permissions'],COLLECTOR_PERMISSIONS);need(all(value is False for value in m['permissions'].values()))
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
        if name.startswith('sources/'):
            need(any(name=='sources/'+source or name.startswith('sources/'+source+'/') for source in COLLECTOR_SOURCES))
    for name in list(m['files'])+dirs:
        need(all(p.as_posix() in dirs for p in Path(name).parents if str(p)!='.'))
    for key in ('collector_profile','source_manifest','git'):
        relative(m[key]);need(m[key] in m['files'])
    need(m['collector_profile']!=m['source_manifest'])
    need(m['files'][m['collector_profile']]['bytes']<=32768)
    _collector_source_files(m)
    exact(m['runtime'],('python','lock'))
    python=m['runtime']['python'];lock=m['runtime']['lock']
    exact(python,('path','version','sha256'));exact(lock,('path','sha256'))
    need(python['version']=='3.12.10')
    for item in (python,lock):
        relative(item['path']);digest(item['sha256'])
        need(item['path'] in m['files'] and item['sha256']==m['files'][item['path']]['sha256'])
    deps=m['dependencies'];need(type(deps) is list and 1<=len(deps)<=256)
    seen=set();python_dep=False
    for dep in deps:
        exact(dep,('name','version','lock_path','lock_sha256'));relative(dep['name']);relative(dep['lock_path']);digest(dep['lock_sha256'])
        need(dep['name'].casefold() not in seen);seen.add(dep['name'].casefold())
        need(type(dep['version']) is str and re.fullmatch(r'[0-9][A-Za-z0-9_.+-]{0,79}',dep['version']))
        need(dep['lock_path'] in m['files'] and dep['lock_sha256']==m['files'][dep['lock_path']]['sha256'])
        if dep['name']=='python':
            need(dep['version']==python['version'] and dep['lock_path']==lock['path'] and dep['lock_sha256']==lock['sha256'])
            python_dep=True
    need(python_dep)
    return m


def parse_manifest(raw,expected_sha256):
    digest(expected_sha256);need(type(raw) is bytes and 0<len(raw)<=LIMIT)
    need(hashlib.sha256(raw).hexdigest()==expected_sha256)
    m=_canonical_document(raw)
    if type(m) is dict and m.get('schema')==COLLECTOR_SCHEMA:return _parse_collector_manifest(m)
    # The original parser body and accepted V1 result remain unchanged.
    return _parse_v1_manifest(raw,expected_sha256)


def _verify_collector_source(path,pin):
    path=regular(path);sha=hashlib.sha256()
    blob=hashlib.sha1(b'blob '+str(pin['bytes']).encode('ascii')+b'\0');count=0
    with path.open('rb') as stream:
        before=os.fstat(stream.fileno());need(before.st_size==pin['bytes'])
        while count<pin['bytes']+1:
            block=stream.read(min(1024*1024,pin['bytes']+1-count))
            if not block:break
            count+=len(block);sha.update(block);blob.update(block)
        after=os.fstat(stream.fileno());current=regular(path).lstat()
        fields=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_nlink)
        need(fields(before)==fields(after)==fields(current) and before.st_ctime_ns==after.st_ctime_ns)
    need(count==pin['bytes'] and sha.hexdigest()==pin['sha256'] and blob.hexdigest()==pin['blob_oid'])


def _verify_collector_profile(root,m):
    path=regular(root/m['collector_profile']);need(path.stat().st_size<=32768)
    with path.open('rb') as stream:
        before=os.fstat(stream.fileno());raw=stream.read(32769);after=os.fstat(stream.fileno())
    current=regular(path).lstat();fields=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_nlink)
    need(fields(before)==fields(after)==fields(current) and before.st_ctime_ns==after.st_ctime_ns and len(raw)==before.st_size)
    need(_pin_from_bytes(raw)==m['files'][m['collector_profile']])
    profile=_canonical_document(raw);need(type(profile) is dict)
    need(profile.get('schema')=='unified.data-only-collector.profile.v1' and profile.get('mode')=='SYNTHETIC_OFFLINE')
    need(profile.get('grid_launch_profile')=='grid.data-only-collector.v1' and profile.get('instrument_identity')=='synthetic-btcusdt-v1')
    need(profile.get('source_manifest_sha256')==m['files'][m['source_manifest']]['sha256'])
    exact(profile.get('network'),('rest','websocket'));need(all(value is False for value in profile['network'].values()))
    exact(profile.get('features'),('trading','training','math','public_submit','authority_mutation'))
    need(all(value is False for value in profile['features'].values()))


def _pin_from_bytes(raw):
    return {'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}


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
    if m['schema']==COLLECTOR_SCHEMA:
        for name,pin in _collector_source_files(m).items():_verify_collector_source(root/name,pin)
        _verify_collector_profile(root,m)
    need(manifest.read_bytes()==raw)
    if m['schema']==COLLECTOR_SCHEMA:
        return dict(mode='SYNTHETIC_OFFLINE',manifest_sha256=expected_sha256,release_id=m['release_id'],
                    publisher_trust='NOT_REQUIRED_FOR_LAB',files_verified=len(found),
                    source_provenance='PINNED_METADATA_ONLY_VERIFY_PRIMARY_GIT_MEMBERSHIP_BEFORE_EXECUTION',
                    trading_authorized=False,execution='DATA_ONLY',execution_authority=False,
                    service_admission=False,profile_policy='RUNTIME_VALIDATION_REQUIRED',physical_acceptance='NOT_RUN',manifest=m)
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
