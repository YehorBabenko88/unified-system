"""Source-only operator tool for exporting and preparing fresh LAB worker capsules.

Operator code/closure and lock digest must be independently pinned before launch.
Never import this tool from an unadmitted payload. No services are installed.
The run operation is inert unless explicitly selected with --execute.
Enrollment stdin is exactly {"enrollment_token":"..."}; node-only WORKER v3
never accepts or stores a fleet token or database password.
The externally pinned operator lock has exactly schema, files, and
source_manifest_sha256s (1..16 sorted unique owner-approved source manifest pins).
Files map operator-relative Python source paths (including this script) to SHA256.
Failures retain new inactive output/state for inspection; no cleanup/overwrite.
"""
import argparse
import copy
from contextlib import contextmanager
import hashlib
import importlib.abc
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import socket
import stat
import subprocess
import sys
import time
import zipfile

WORKERS={'PC1':'Easy','PC2':'Leitstelle1','PC3':'LS03e','PC4':'LS4','LS7':'LS-07'}
MODULES={'unified-system','grid','math','meta_analyse','strattester','terminan'}
ARCHIVE_LIMIT=9*1024**3


def need(ok,code='WORKER_CAPSULE_REJECTED'):
    if not ok:raise ValueError(code)


def unique(pairs):
    value={}
    for key,item in pairs:
        need(key not in value);value[key]=item
    return value


def canonical(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()


def safe(path):
    path=Path(path);raw=str(path)
    need(path.is_absolute() and not raw.startswith(('\\\\','//')))
    parts=raw.replace('\\','/').split('/')[1:]
    need(not any(p in ('.','..') or ':' in p or p.endswith((' ','.')) or re.match(r'(?i)^(CON|PRN|AUX|NUL|COM[0-9\u00b9\u00b2\u00b3]|LPT[0-9\u00b9\u00b2\u00b3]) *(?:[.]|$)',p) for p in parts))
    for ancestor in (*reversed(path.parents),path):
        try:info=ancestor.lstat()
        except FileNotFoundError:continue
        need(not stat.S_ISLNK(info.st_mode) and not getattr(info,'st_file_attributes',0)&1024)
    need(path.resolve(strict=False)==path)
    return path


def read_file(path,limit):
    path=safe(path)
    with path.open('rb') as stream:
        before=os.fstat(stream.fileno());need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_size<=limit)
        raw=stream.read(limit+1);after=os.fstat(stream.fileno());current=path.stat()
        fields=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_nlink)
        need(len(raw)==before.st_size and fields(before)==fields(after)==fields(current))
        return raw


def hash_path(path,limit=ARCHIVE_LIMIT):
    path=safe(path);h=hashlib.sha256()
    with path.open('rb') as stream:
        before=os.fstat(stream.fileno());need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_size<=limit)
        count=0
        for block in iter(lambda:stream.read(1048576),b''):count+=len(block);need(count<=limit);h.update(block)
        after=os.fstat(stream.fileno());current=path.stat()
        fields=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_nlink)
        need(count==before.st_size and fields(before)==fields(after)==fields(current))
    return h.hexdigest()


class OperatorSources(importlib.abc.MetaPathFinder,importlib.abc.Loader):
    """Compile exclusively verified operator .py bytes; no cached payload imports."""
    def __init__(self,root,files):self.root=root;self.files=files
    def find_spec(self,fullname,path=None,target=None):
        if fullname!='unified_system' and not fullname.startswith('unified_system.') and fullname!='integration' and not fullname.startswith('integration.'):return None
        if fullname=='integration':return importlib.machinery.ModuleSpec(fullname,loader=None,is_package=True)
        stem=fullname.replace('.','/');package=stem+'/__init__.py';relative=package if package in self.files else stem+'.py'
        need(relative in self.files,'OPERATOR_IMPORT_NOT_PINNED')
        spec=importlib.util.spec_from_loader(fullname,self,is_package=relative==package);spec.loader_state=relative;return spec
    def create_module(self,spec):return None
    def exec_module(self,module):
        relative=module.__spec__.loader_state;module.__file__=str(self.root/relative)
        if module.__spec__.submodule_search_locations is not None:module.__path__=[]
        exec(compile(self.files[relative],module.__file__,'exec'),module.__dict__)


def admit_operator(root,lock,pin):
    need(sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode,'ISOLATED_OPERATOR_REQUIRED')
    root=safe(root);raw=read_file(lock,1024*1024)
    need(re.fullmatch('[a-f0-9]{64}',pin) and hashlib.sha256(raw).hexdigest()==pin,'OPERATOR_LOCK_PIN')
    policy=json.loads(raw,object_pairs_hook=unique)
    need(type(policy) is dict and set(policy)=={'schema','files','source_manifest_sha256s'} and policy['schema']=='unified.worker-operator.v1' and type(policy['files']) is dict)
    allowed=policy['source_manifest_sha256s']
    need(type(allowed) is list and 1<=len(allowed)<=16 and all(type(pin) is str and re.fullmatch('[a-f0-9]{64}',pin) for pin in allowed))
    need(allowed==sorted(set(allowed)),'OPERATOR_SOURCE_POLICY_REJECTED')
    need(1<=len(policy['files'])<=500)
    required={'scripts/prepare_worker_capsule.py','unified_system/__init__.py','unified_system/lab_release.py','unified_system/lab_runtime.py','unified_system/lab_capsule_acl.py','integration/source_guard.py'}
    need(required<=set(policy['files']))
    files={};total=0;seen=set()
    for relative,digest in policy['files'].items():
        need(type(relative) is str and re.fullmatch(r'(?:unified_system/[A-Za-z0-9_/]+[.]py|integration/source_guard[.]py|scripts/prepare_worker_capsule[.]py)',relative))
        need(all(part not in ('','.', '..') for part in relative.split('/')) and relative.casefold() not in seen)
        seen.add(relative.casefold())
        need(type(digest) is str and re.fullmatch('[a-f0-9]{64}',digest))
        data=read_file(root/relative,1024*1024);total+=len(data);need(total<=16*1024*1024 and hashlib.sha256(data).hexdigest()==digest,'OPERATOR_SOURCE_PIN')
        files[relative]=data
    need(read_file(Path(__file__).resolve(),1024*1024)==files['scripts/prepare_worker_capsule.py'],'OPERATOR_SCRIPT_PIN')
    need(not any(n=='unified_system' or n.startswith('unified_system.') or n=='integration' or n.startswith('integration.') for n in sys.modules),'OPERATOR_ALREADY_IMPORTED')
    sys.meta_path.insert(0,OperatorSources(root,files))
    return frozenset(allowed)


def prove_sources(root,manifest):
    from unified_system.lab_runtime import verify_sources
    return verify_sources(root,manifest)


def archive_info(name,is_dir):
    info=zipfile.ZipInfo(name+('/' if is_dir else ''));info.create_system=3
    info.external_attr=((0o40700 if is_dir else 0o100600)<<16)|(16 if is_dir else 0)
    info.compress_type=zipfile.ZIP_DEFLATED
    return info


def export_archive(source,destination,manifest_pin):
    from unified_system import lab_release
    source=safe(source);destination=safe(destination)
    need(not destination.exists() and source not in destination.parents and destination.parent.is_dir())
    m=lab_release.verify_capsule(source,manifest_pin)['manifest'];prove_sources(source,m)
    with destination.open('xb') as output:
        with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as archive:
            for name in m['directories']:archive.writestr(archive_info(name,True),b'')
            for name,pin in [*m['files'].items(),('lab-release.json',dict(sha256=manifest_pin,bytes=(source/'lab-release.json').stat().st_size))]:
                path=lab_release.regular(source/name);h=hashlib.sha256();count=0
                with path.open('rb') as src,archive.open(archive_info(name,False),'w') as dst:
                    before=os.fstat(src.fileno())
                    for block in iter(lambda:src.read(1048576),b''):
                        count+=len(block);need(count<=pin['bytes']);h.update(block);dst.write(block)
                    after=os.fstat(src.fileno());current=path.stat()
                    fields=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_nlink)
                    need(count==pin['bytes'] and h.hexdigest()==pin['sha256'] and fields(before)==fields(after)==fields(current))
    lab_release.verify_capsule(source,manifest_pin);prove_sources(source,m)
    digest=hash_path(destination);check_archive(destination,digest,manifest_pin)
    return dict(result='ORIGINAL_CAPSULE_EXPORTED',archive_sha256=digest,source_manifest_sha256=manifest_pin,execution='NOT_STARTED')


def _check_zip(archive,manifest_pin):
    from unified_system import lab_release
    need(not archive.comment and len(archive.infolist())<=200001)
    entries={};folded=set();total=0
    for info in archive.infolist():
        name=info.filename[:-1] if info.is_dir() else info.filename;lab_release.relative(name)
        need(name.casefold() not in folded and not info.extra and not info.comment and not info.flag_bits&1)
        folded.add(name.casefold());entries[name]=info
        mode=(info.external_attr>>16)&0o170000
        need(info.create_system==3 and info.compress_type==zipfile.ZIP_DEFLATED and not info.flag_bits&~(8|0x800))
        need(mode==(0o040000 if info.is_dir() else 0o100000) and not info.external_attr&1024)
        need(0<=info.file_size<=(0 if info.is_dir() else lab_release.FILE_LIMIT))
        total+=info.file_size;need(total<=lab_release.TOTAL_LIMIT+lab_release.LIMIT)
    need('lab-release.json' in entries and entries['lab-release.json'].file_size<=lab_release.LIMIT)
    raw=archive.read(entries['lab-release.json']);m=lab_release.parse_manifest(raw,manifest_pin)
    need(set(entries)==set(m['files'])|set(m['directories'])|{'lab-release.json'})
    for name,info in entries.items():
        if name in m['directories']:need(info.is_dir());continue
        pin=m['files'].get(name,dict(sha256=manifest_pin,bytes=len(raw)))
        need(not info.is_dir() and info.file_size==pin['bytes'])
        h=hashlib.sha256();count=0
        with archive.open(info) as src:
            for block in iter(lambda:src.read(1048576),b''):
                count+=len(block);need(count<=pin['bytes']);h.update(block)
        need(count==pin['bytes'] and h.hexdigest()==pin['sha256'])
    return m


@contextmanager
def admitted_archive(path,archive_pin,manifest_pin):
    """Hold one ordinary file handle across hashing, ZIP proof and extraction."""
    need(type(archive_pin) is str and re.fullmatch('[a-f0-9]{64}',archive_pin))
    path=safe(path)
    with path.open('rb') as stream:
        before=os.fstat(stream.fileno())
        need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and 0<before.st_size<=ARCHIVE_LIMIT)
        fields=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_nlink)
        def stable_hash():
            stream.seek(0);h=hashlib.sha256();count=0
            for block in iter(lambda:stream.read(1048576),b''):
                count+=len(block);need(count<=ARCHIVE_LIMIT);h.update(block)
            need(count==before.st_size and h.hexdigest()==archive_pin)
            need(fields(before)==fields(os.fstat(stream.fileno()))==fields(path.lstat()))
        stable_hash();stream.seek(0)
        with zipfile.ZipFile(stream) as archive:
            manifest=_check_zip(archive,manifest_pin)
            yield archive,manifest
        stable_hash()


def check_archive(path,archive_pin,manifest_pin):
    with admitted_archive(path,archive_pin,manifest_pin) as (_,manifest):return manifest


def extract_verified(archive_path,target,m,manifest_pin,archive_pin):
    from unified_system import lab_release
    target=safe(target);need(target.is_dir() and not any(target.iterdir()))
    with admitted_archive(archive_path,archive_pin,manifest_pin) as (archive,checked):
        need(checked==m)
        for name in m['directories']:safe(target/name).mkdir(parents=True,exist_ok=True)
        for name,pin in [*m['files'].items(),('lab-release.json',dict(sha256=manifest_pin,bytes=archive.getinfo('lab-release.json').file_size))]:
            path=safe(target/name);h=hashlib.sha256();count=0
            with archive.open(name) as src,path.open('xb') as dst:
                for block in iter(lambda:src.read(1048576),b''):
                    count+=len(block);need(count<=pin['bytes']);h.update(block);dst.write(block)
            need(count==pin['bytes'] and h.hexdigest()==pin['sha256'])
    lab_release.verify_capsule(target,manifest_pin)


def check_worker_host(node):
    need(node in WORKERS and socket.gethostname().split('.')[0].casefold() in (node.casefold(),WORKERS[node].casefold()),'ACTUAL_WORKER_HOST_REQUIRED')


def read_private(stream):
    try:
        raw=stream.read(4097);need(type(raw) is bytes and 0<len(raw)<=4096)
        value=json.loads(raw,object_pairs_hook=unique)
        need(type(value) is dict and set(value)=={'enrollment_token'})
        need(type(value['enrollment_token']) is str and re.fullmatch('[A-Za-z0-9_-]{32,256}',value['enrollment_token']))
        return value
    except Exception:raise ValueError('PRIVATE_INPUT_REJECTED') from None


def enroll(port,node,token,timeout=5):
    need(type(port) is int and 1024<=port<=65535 and node in WORKERS and .05<=timeout<=5)
    deadline=time.monotonic()+timeout;body=json.dumps(dict(enrollment_token=token,node_id=node),separators=(',',':')).encode()
    request=(f'POST /enroll HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n').encode()+body
    try:
        with socket.create_connection(('127.0.0.1',port),timeout=min(2,timeout)) as wire:
            def budget():
                left=deadline-time.monotonic();need(left>0);wire.settimeout(left)
            budget();wire.sendall(request);data=b''
            while b'\r\n\r\n' not in data:
                budget();block=wire.recv(1024);need(block);data+=block;need(len(data)<=8192)
            header,data=data.split(b'\r\n\r\n',1);lines=header.split(b'\r\n');need(lines[0] in (b'HTTP/1.1 200 OK',b'HTTP/1.0 200 OK'))
            headers={}
            for line in lines[1:]:
                key,sep,value=line.partition(b':');key=key.lower()
                need(sep and re.fullmatch(b'[a-z0-9-]{1,64}',key) and key not in headers);headers[key]=value.strip()
            need(b'transfer-encoding' not in headers and b'content-encoding' not in headers)
            length=headers.get(b'content-length',b'');need(re.fullmatch(b'[0-9]{1,4}',length) and 1<=int(length)<=4096)
            length=int(length);need(len(data)<=length)
            while len(data)<length:
                budget();block=wire.recv(min(1024,length-len(data)));need(block);data+=block
            budget();reply=json.loads(data,object_pairs_hook=unique)
            need(type(reply) is dict and set(reply)=={'node_id','credential','install_mode'})
            need(reply['node_id']==node and reply['install_mode']=='PILOT' and type(reply['credential']) is str and re.fullmatch('[A-Za-z0-9_-]{64,128}',reply['credential']))
            return reply['credential']
    except Exception:raise ValueError('CONTROL_ENROLLMENT_REJECTED') from None


def worker_config(config,*,node_id,old_root,new_root,new_state,ports,coordinator_port,auth_path,auth_sha256):
    if node_id not in WORKERS or set(ports)!=MODULES:raise ValueError('WORKER_TARGET_REQUIRED')
    if any(type(p) is not int or not 1024<=p<=65535 for p in [*ports.values(),coordinator_port]) or len(set(ports.values()))!=6 or coordinator_port in ports.values():
        raise ValueError('BOUND_LOOPBACK_PORTS_REQUIRED')
    old_root=Path(old_root);new_root=Path(new_root);old_state=Path(config['state_root']);new_state=Path(new_state)
    if not all(p.is_absolute() for p in (old_root,new_root,old_state,new_state,Path(auth_path))):raise ValueError('ABSOLUTE_PATH_REQUIRED')
    if new_root==new_state or new_root in new_state.parents or new_state in new_root.parents:raise ValueError('DISJOINT_STATE_REQUIRED')
    if new_state not in Path(auth_path).parents or not isinstance(auth_sha256,str) or not re.fullmatch('[a-f0-9]{64}',auth_sha256):raise ValueError('PRIVATE_AUTH_BINDING_REQUIRED')
    def text(value):
        if type(value) is not str:return value
        for old,new in ((old_root,new_root),(old_state,new_state)):
            if value==str(old):return str(new)
            if value.startswith(str(old)+'\\') or value.startswith(str(old)+'/'):return str(new)+value[len(str(old)):]
        return value
    def rebase(value):
        if isinstance(value,dict):return {text(k):rebase(v) for k,v in value.items()}
        if isinstance(value,list):return [rebase(v) for v in value]
        return text(value)
    c=rebase(copy.deepcopy(config));c['node_id']=node_id;c['http_port']=ports['unified-system']
    for name,program in c['programs'].items():
        previous=program['health_url'].rsplit(':',1)[1].split('/',1)[0]
        program['health_url']=f'http://127.0.0.1:{ports[name]}/internal/v2/module/health'
        if name!='math':
            args=program['argv'];port_index=args.index('--port')
            if args[port_index+1]!=previous:raise ValueError('SOURCE_PORT_BINDING')
            args[port_index+1]=str(ports[name])
        else:program['env']['MATH_ENGINE_PORT']=str(ports[name])
    for name,program in c['programs'].items():
        need(not any(k.upper() in ('PGPASSWORD','NODE_CREDENTIAL','GRID_SHARED_TOKEN') for k in program['env']))
        if name!='grid':need(not any(k.upper()=='POSTGRES_DSN' for k in program['env']))
    grid=c['programs']['grid'];env=grid['env']
    for key in list(env):
        if key.upper()=='POSTGRES_DSN':del env[key]
    for key in ('PGPASSWORD','NODE_CREDENTIAL','GRID_SHARED_TOKEN'):
        if key in env:raise ValueError('PRIVATE_ENV_NOT_IN_PUBLIC_CONFIG')
    env.update(ROLE='worker',NODE_ID=node_id,NODE_ROLE='WORKER',COORDINATOR_URL=f'http://127.0.0.1:{coordinator_port}',
               GRID_LAB_AUTH_PATH=str(auth_path),GRID_LAB_AUTH_SHA256=auth_sha256)
    args=grid['argv'];source=str(new_root/'sources/grid');deps=str(new_root/'dependencies/site-packages')
    args[args.index('--source-root')+1]=source
    dependency_indices=[i+1 for i,a in enumerate(args) if a=='--dependency-root']
    if len(dependency_indices)!=1:raise ValueError('REVIEWED_GRID_DEPENDENCIES_REQUIRED')
    args[dependency_indices[0]]=deps
    index=args.index('--module')
    grid['argv']=args[:index]+['--module','grid.owned_worker_service','--','--execute','--port',str(ports['grid'])]
    return c


def prepare_worker(archive,archive_pin,source_pin,target,state,node,ports,coordinator_port,private_stream):
    from unified_system import lab_release,lab_runtime
    from unified_system.lab_capsule_acl import FreshCodeRoot
    import tempfile
    check_worker_host(node)
    target=safe(target);state=safe(state)
    need(target.parent==state.parent and target!=state and target.parent.is_dir() and not target.exists() and not state.exists())
    need(set(ports)==MODULES and all(type(p) is int and 1024<=p<=65535 for p in [*ports.values(),coordinator_port]))
    need(len(set(ports.values()))==6 and coordinator_port not in ports.values())
    m=check_archive(archive,archive_pin,source_pin)
    # Complete ZIP admission precedes all new output/state creation.
    owned=FreshCodeRoot.create(target)
    private_state=FreshCodeRoot.create(state)
    # FreshCodeRoot has just verified the exact private FullControl ACL.
    secrets=read_private(private_stream)
    extract_verified(archive,target,m,source_pin,archive_pin)
    temporary=state/'operator-temp';temporary.mkdir()
    previous=tempfile.tempdir
    try:
        tempfile.tempdir=str(temporary)
        lab_release.verify_capsule(target,source_pin);prove_sources(target,m)
        config=json.loads(read_file(target/m['runtime_config'],lab_release.FILE_LIMIT),object_pairs_hook=unique)
        old_root=Path(config['programs']['grid']['env']['UNIFIED_SOURCE_ROOT']).parents[1]
        auth_path=state/'private/grid-auth.json'
        # Validate the complete rebased public profile before consuming a token.
        candidate=worker_config(config,node_id=node,old_root=old_root,new_root=target,new_state=state,ports=ports,
            coordinator_port=coordinator_port,auth_path=auth_path,auth_sha256='0'*64)
        lab_runtime.validate_config(candidate,m,target)
        credential=enroll(coordinator_port,node,secrets['enrollment_token'])
        auth=dict(schema='unified.lab.grid-auth.v3',node_id=node,role='WORKER',release_id=m['release_id'],
            source_commit=m['sources']['grid']['commit'],grid_shared_token=None,
            node_credential=credential,postgres_password=None)
        auth_raw=canonical(auth);auth_path.parent.mkdir()
        with auth_path.open('xb') as out:out.write(auth_raw);out.flush();os.fsync(out.fileno())
        auth_pin=hashlib.sha256(auth_raw).hexdigest()
        # This existing reader independently checks role, scope and no database password.
        lab_runtime.read_grid_auth(auth_path,auth_pin,node_id=node,release_id=m['release_id'],source_commit=m['sources']['grid']['commit'])
        candidate=worker_config(config,node_id=node,old_root=old_root,new_root=target,new_state=state,ports=ports,
            coordinator_port=coordinator_port,auth_path=auth_path,auth_sha256=auth_pin)
        config_raw=canonical(candidate)
        need(hash_path(target/m['runtime_config'])==m['files'][m['runtime_config']]['sha256'])
        with (target/m['runtime_config']).open('wb') as out:out.write(config_raw);out.flush();os.fsync(out.fileno())
        final=copy.deepcopy(m);final['files'][m['runtime_config']]=dict(sha256=hashlib.sha256(config_raw).hexdigest(),bytes=len(config_raw))
        final_raw=canonical(final);final_pin=hashlib.sha256(final_raw).hexdigest()
        need(hash_path(target/'lab-release.json')==source_pin)
        with (target/'lab-release.json').open('wb') as out:out.write(final_raw);out.flush();os.fsync(out.fileno())
        lab_release.verify_capsule(target,final_pin);lab_runtime.validate_config(candidate,final,target);prove_sources(target,final)
        owned.seal(final_pin)
    finally:tempfile.tempdir=previous
    return dict(result='PREPARED_ENROLLED_PILOT_WORKER',node_id=node,source_manifest_sha256=source_pin,
        manifest_sha256=final_pin,capsule=str(target),state_root=str(state),services='NOT_STARTED',
        runtime_readiness='NOT_TESTED',physical_acceptance='NOT_RUN')


def run_worker(root,manifest_pin,*,execute=False):
    """Launch an owner-pinned derived worker through its admitted raw bootstrap.

    The external operator lock must authorize this individual worker manifest
    digest, obtained from its verified preparation receipt, before this call.
    The common CONTROL manifest pin does not authorize an arbitrary derived pin.
    """
    from unified_system.lab_runtime import prepare,child_environment,read_grid_auth
    root=safe(root)
    config,report=prepare(root,manifest_pin)
    check_worker_host(config['node_id'])
    need(config['programs']['grid']['env'].get('ROLE')=='worker')
    manifest=report['manifest'];source=root/'sources/unified-system'
    env=config['programs']['grid']['env']
    auth=read_grid_auth(env['GRID_LAB_AUTH_PATH'],env['GRID_LAB_AUTH_SHA256'],
        node_id=config['node_id'],release_id=config['release_id'],source_commit=manifest['sources']['grid']['commit'])
    auth.clear()  # Never pass this reader's credential values to the bootstrap environment.
    def pin(relative):
        raw=read_file(root/relative,32*1024*1024)
        expected=manifest['files'][relative]
        digest=hashlib.sha256(raw).hexdigest()
        need(len(raw)==expected['bytes'] and digest==expected['sha256'])
        return digest
    pin('sources/unified-system/unified_system/package_preflight.py')
    guard=pin('sources/unified-system/integration/source_guard.py')
    git=pin(manifest['git'])
    result=dict(result='WORKER_RUNTIME_ADMITTED_NOT_STARTED',node_id=config['node_id'],
        release_id=config['release_id'],manifest_sha256=manifest_pin,services='NOT_INSTALLED',
        physical_acceptance='NOT_RUN',trading_authorized=False)
    if not execute:return result
    cache=safe(Path(config['state_root'])/'bootstrap-cache');cache.mkdir(exist_ok=True);safe(cache)
    args=[sys.executable,'-I','-S','-B',str(source/'unified_system/package_preflight.py'),
        '--source-root',str(source),'--source-head',manifest['sources']['unified-system']['commit'],
        '--source-tree',manifest['sources']['unified-system']['tree'],
        '--source-guard-sha256',guard,'--git-executable',str(root/manifest['git']),
        '--git-sha256',git,'--cache-root',str(cache),'--operation','lab','--lab-root',str(root),
        '--lab-manifest-sha256',manifest_pin,'--execute-lab']
    child=subprocess.Popen(args,env=child_environment())
    while True:
        try:code=child.wait();break
        except KeyboardInterrupt:continue  # Shared foreground Ctrl-C reaches owned cleanup.
    result.update(result='WORKER_RUNTIME_EXITED',exit_code=code)
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--operator-root',required=True)
    parser.add_argument('--operator-lock',required=True)
    parser.add_argument('--operator-lock-sha256',required=True)
    sub=parser.add_subparsers(dest='operation',required=True)
    export=sub.add_parser('export');export.add_argument('--source',required=True);export.add_argument('--archive',required=True)
    export.add_argument('--source-manifest-sha256',required=True)
    prepare=sub.add_parser('prepare');prepare.add_argument('--archive',required=True);prepare.add_argument('--archive-sha256',required=True)
    prepare.add_argument('--source-manifest-sha256',required=True);prepare.add_argument('--target',required=True);prepare.add_argument('--state',required=True)
    prepare.add_argument('--node',required=True,choices=sorted(WORKERS));prepare.add_argument('--ports-json',required=True)
    prepare.add_argument('--coordinator-port',type=int,required=True);prepare.add_argument('--enroll',action='store_true')
    run=sub.add_parser('run');run.add_argument('--root',required=True)
    run.add_argument('--source-manifest-sha256',required=True,help='Owner-pinned individual worker manifest, not the common archive pin')
    run.add_argument('--execute',action='store_true')
    args=parser.parse_args(argv)
    try:
        allowed=admit_operator(args.operator_root,args.operator_lock,args.operator_lock_sha256)
        need(args.source_manifest_sha256 in allowed,'SOURCE_MANIFEST_NOT_ADMITTED')
        if args.operation=='export':result=export_archive(Path(args.source),Path(args.archive),args.source_manifest_sha256)
        elif args.operation=='run':result=run_worker(Path(args.root),args.source_manifest_sha256,execute=args.execute)
        elif not args.enroll:
            check_worker_host(args.node);check_archive(Path(args.archive),args.archive_sha256,args.source_manifest_sha256)
            result=dict(result='ARCHIVE_BYTES_VERIFIED_ONLY',enrollment='NOT_PERFORMED',outputs='NOT_CREATED',runtime_readiness='NOT_TESTED')
        else:
            ports=json.loads(args.ports_json,object_pairs_hook=unique)
            result=prepare_worker(Path(args.archive),args.archive_sha256,args.source_manifest_sha256,
                Path(args.target),Path(args.state),args.node,ports,args.coordinator_port,sys.stdin.buffer)
        print(json.dumps(result,sort_keys=True));return 0 if result.get('exit_code',0)==0 else 1
    except Exception:
        print('WORKER_CAPSULE_REJECTED');return 1


if __name__=='__main__':raise SystemExit(main())

