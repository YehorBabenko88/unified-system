"""Explicit owner-admitted lab entrypoint; never a trusted-release fallback.

Launch only reviewed/pinned own components. This is not an arbitrary-code sandbox.
Canonical source identities and external signing/admission gates are retained.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import threading
import re
from urllib.parse import urlsplit

from . import lab_release
from .module_catalog import MODULE_IDS
from .market_data_entry_contract import MarketDataEntryRejected,V2_ENTRY,entry_for_manifest
from .runtime_cli import validate_config as base_config,read_config,make_runtime,run_runtime
from .runtime_process import _safe_path

ENVIRONMENT_KEYS={
    'PATH','UNIFIED_GIT_EXECUTABLE','UNIFIED_GIT_SHA256','UNIFIED_SOURCE_ROOT',
    'UNIFIED_ROOT_SOURCE_COMMIT','UNIFIED_SOURCE_COMMIT','GIT_CONFIG_NOSYSTEM',
    'GIT_CONFIG_GLOBAL','GIT_CONFIG_SYSTEM','GIT_NO_REPLACE_OBJECTS','GIT_NO_LAZY_FETCH',
    'NO_PROXY','MATH_ENGINE_PORT','TERMINAN_RUNTIME_V2_SNAPSHOT',
    'PROGRAMDATA','PROGRAMFILES','ML_ARTIFACT_ROOT','ARCHIVE_ROOT','STRATEGY_CACHE_DIR',
    'BYBIT_REST_URL','BYBIT_WS_URL','BYBIT_ARCHIVE_BASE_URL','LOG_LEVEL','RETENTION_ENABLED',
    'MARKET_DATA_PORT','MARKET_DATA_DSN','MARKET_DATA_PINNED_HISTORY_CATALOG',
    'TEMP','TMP','USERPROFILE','HOME','APPDATA','LOCALAPPDATA','TERMINAN_LAB_SNAPSHOT',
}
PUBLIC_ENDPOINTS={'BYBIT_REST_URL':'https://api.bybit.com',
                  'BYBIT_WS_URL':'wss://stream.bybit.com/v5/public/linear',
                  'BYBIT_ARCHIVE_BASE_URL':'https://public.bybit.com/trading'}
LAB_NODES=frozenset(('LS5','PC1','PC2','PC3','PC4','LS7'))
LAB_HOSTNAMES={'LS5':'LS5','PC1':'Easy','PC2':'Leitstelle1','PC3':'LS03e','PC4':'LS4','LS7':'LS-07'}


def need(ok):
    if not ok:raise ValueError('LAB_RUNTIME_REJECTED')


def require_v2_terminan_dependency(manifest, specs):
    """No managed chart child may survive a source loss outside supervisor DAG."""
    try:
        entry=entry_for_manifest(manifest)
    except MarketDataEntryRejected:
        need(False)
    if entry != V2_ENTRY:return True
    need(type(specs) is list and all(type(s) is dict for s in specs))
    listed={s.get('module_id'):s for s in specs}
    need(len(listed)==len(specs))
    if 'terminan' in listed:
        need('market_data' in listed
             and type(listed['terminan'].get('dependencies')) in (tuple,list)
             and 'market_data' in listed['terminan']['dependencies'])
    return True


def child_environment(input=None):
    input=os.environ if input is None else input
    keep={'SYSTEMROOT','WINDIR','SYSTEMDRIVE','TEMP','TMP','COMPUTERNAME','USERPROFILE',
          'APPDATA','LOCALAPPDATA','OS','PROCESSOR_ARCHITECTURE'}
    e={k:v for k,v in input.items() if k.upper() in keep}
    e.update(UNIFIED_DEPLOYMENT_MODE='LAB_SIMULATION',UNIFIED_ORDER_MODE='PAPER_ONLY',
             UNIFIED_TRADING_AUTHORIZED='false',PYTHONDONTWRITEBYTECODE='1')
    return e


def _offline_context(context,node_id):
    """Untrusted OFFLINE validation data; never an execution capability."""
    if context is None:return None
    need(type(context) is dict and set(context)=={'scope','role','node_id','computer_name','credential_root'})
    need(context['scope']=='OFFLINE_VALIDATION_ONLY' and context['role'] in ('CONTROL','WORKER','SINGLE_PC'))
    need(context['node_id']==node_id and type(context['computer_name']) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{0,62}',context['computer_name']))
    need(type(context['credential_root']) is str and Path(context['credential_root']).is_absolute())
    return copy.deepcopy(context)


def launch_profile(name,p,root,m,state,node_id,*,offline_context=None):
    """Closed canonical source entrypoints; does not admit or launch a process."""
    need(name in ('math','market_data','terminan'))
    argv=p['argv'];source=root/m['sources'][name]['root']
    port=str(urlsplit(p['health_url']).port)
    if name=='math':
        need(len(argv)==2 and _safe_path(argv[1]).resolve()==source/'src/math-engine-server.mjs')
        return
    need(p['health_url']=='http://127.0.0.1:'+port+'/health')
    bootstrap=root/m['sources']['unified_system']['root']/'unified_system/owned_python.py'
    need(len(argv)>7 and argv[1:4]==['-I','-S','-B'] and _safe_path(argv[4]).resolve()==bootstrap)
    need(bootstrap.relative_to(root).as_posix() in m['files'])
    index=5;roots=[];dependencies=[]
    while index<len(argv) and argv[index] in ('--source-root','--dependency-root'):
        need(index+1<len(argv));value=_safe_path(argv[index+1]).resolve();need(root in value.parents)
        (roots if argv[index]=='--source-root' else dependencies).append(value);index+=2
    need(roots==[source] and len(dependencies)==len(set(dependencies)) and len(dependencies)<=16)
    # The same exact-v2 selector is used by the protected dispatcher.
    # No implicit Grid source migration or unpinned generic module loader.
    try:
        entry=entry_for_manifest(m) if name=='market_data' else 'terminan.server'
    except MarketDataEntryRejected:
        need(False)
    need(argv[index:index+3]==['--module',entry,'--'])
    tail=argv[index+3:]
    if name=='market_data':
        need(tail==['serve'])
        env={key.upper():value for key,value in p.get('env',{}).items()}
        need(env.get('MARKET_DATA_PORT')==port)
    else:
        need(tail==['--host','127.0.0.1','--port',port])


def validate_config(c,m,root,*,hostname=None,offline_context=None):
    root=_safe_path(root).resolve();c=copy.deepcopy(c)
    base_config(c,allow_physical=True)
    need(c['schema']=='unified.runtime.config.v2')
    need(type(m.get('sources')) is dict and set(m['sources'])==MODULE_IDS)
    context=_offline_context(offline_context,c['node_id'])
    actual_host=(hostname or socket.gethostname()).split('.')[0].casefold()
    if context is None:
        need(c['node_id'].upper() in LAB_NODES)
        need(actual_host in (c['node_id'].casefold(),LAB_HOSTNAMES[c['node_id'].upper()].casefold()))
    else:need(actual_host==context['computer_name'].casefold())
    control=c['node_id'].upper()=='LS5' if context is None else context['role'] in ('CONTROL','SINGLE_PC')
    need(c['release_id']==m['release_id'])
    state=_safe_path(c['state_root']).resolve();snapshot=_safe_path(c['snapshot_path']).resolve()
    need(state!=root and root not in state.parents and state not in root.parents and state in snapshot.parents)
    if context is not None:
        credential=_safe_path(context['credential_root']).resolve()
        need(credential!=root and root not in credential.parents and credential not in root.parents)
        need(credential!=state and state not in credential.parents and credential not in state.parents)
    def pin(path,sha):
        p=_safe_path(path).resolve()
        try:name=p.relative_to(root).as_posix()
        except ValueError:raise ValueError('LAB_RUNTIME_REJECTED') from None
        need(name in m['files'] and m['files'][name]['sha256']==sha)
    require_v2_terminan_dependency(m,c['specs'])
    for spec in c['specs']:
        source=m['sources'][spec['module_id']]
        need(spec['version']==source['version'] and set(spec['dependencies'])==set(source['dependencies']))
    for name,p in c['programs'].items():
        cwd=_safe_path(p['cwd']).resolve();need(cwd==root/m['sources'][name]['root'])
        pin(p['argv'][0],p['executable_sha256'])
        launch_profile(name,p,root,m,state,c['node_id'],offline_context=context)
        for argument in p['argv'][1:]:
            if Path(argument).is_absolute():
                value=_safe_path(argument).resolve()
                need(root in value.parents or state==value or state in value.parents)
            need(argument.casefold() not in ('--import','--require','-r','--eval','--loader','--experimental-loader'))
        for file,sha in p['file_pins'].items():pin(cwd/file,sha)
        for file,sha in p.get('external_file_pins',{}).items():pin(file,sha)
        env=p.get('env',{});need(len({k.upper() for k in env})==len(env))
        for key,value in env.items():
            key=key.upper();need(key in ENVIRONMENT_KEYS)
            if key in PUBLIC_ENDPOINTS:need(name=='market_data' and value==PUBLIC_ENDPOINTS[key])
            if key in ('PROGRAMDATA','PROGRAMFILES','ML_ARTIFACT_ROOT','ARCHIVE_ROOT','STRATEGY_CACHE_DIR','TERMINAN_RUNTIME_V2_SNAPSHOT','TERMINAN_LAB_SNAPSHOT','MARKET_DATA_PINNED_HISTORY_CATALOG','TEMP','TMP','USERPROFILE','HOME','APPDATA','LOCALAPPDATA'):
                target=_safe_path(value).resolve();need(target==state or state in target.parents)
                if key=='MARKET_DATA_PINNED_HISTORY_CATALOG':need(name=='market_data')
            if key=='MARKET_DATA_PORT':need(name=='market_data' and value==str(urlsplit(p['health_url']).port))
            if key=='MATH_ENGINE_PORT':need(name=='math' and value==str(urlsplit(p['health_url']).port))
            if key=='PATH':
                for entry in value.split(os.pathsep):
                    need(Path(entry).is_absolute());target=_safe_path(entry).resolve()
                    need(target==root or root in target.parents)
            if key=='UNIFIED_SOURCE_ROOT':need(_safe_path(value).resolve()==root/m['sources']['unified_system']['root'])
            if key=='UNIFIED_SOURCE_COMMIT':need(value==m['sources'][name]['commit'])
            if key=='UNIFIED_ROOT_SOURCE_COMMIT':need(value==m['sources']['unified_system']['commit'])
            if key=='UNIFIED_GIT_EXECUTABLE':need(_safe_path(value).resolve()==root/m['git'])
            if key=='UNIFIED_GIT_SHA256':need(value==m['files'][m['git']]['sha256'])
            if key=='MARKET_DATA_DSN':
                need(control and name=='market_data')
                u=urlsplit(value)
                need(u.scheme in ('postgres','postgresql') and u.hostname in ('127.0.0.1','::1')
                     and u.port is not None and u.username and u.username.startswith('unified_lab_') and u.password is None
                     and u.path.startswith('/unified_lab_') and not u.query and not u.fragment)
        env=p.setdefault('env',{})
        defaults={'PROGRAMDATA':'data','PROGRAMFILES':'program-files','ML_ARTIFACT_ROOT':'artifacts',
                  'ARCHIVE_ROOT':'archive','STRATEGY_CACHE_DIR':'strategies',
                  'TEMP':'temp','TMP':'temp','USERPROFILE':'profile','HOME':'profile',
                  'APPDATA':'profile/AppData/Roaming','LOCALAPPDATA':'profile/AppData/Local'}
        for key,suffix in defaults.items():
            if key not in {k.upper() for k in env}:env[key]=str(state/name/suffix)
    return c


def verify_sources(root,m,*,owner_admitted_root=None):
    # Explicit protected-service caller data only. prepare()/CLI do not opt in;
    # startup must separately verify kernel ownership and the complete capsule.
    admitted_root=None
    if owner_admitted_root is not None:
        need(isinstance(owner_admitted_root,(str,Path)) and Path(owner_admitted_root).is_absolute() and '*' not in str(owner_admitted_root))
        admitted_root=_safe_path(owner_admitted_root).resolve();need(admitted_root==root)
    from integration.source_guard import SourceFence
    git=root/m['git'];pin=m['files'][m['git']]['sha256'];results={}
    for name,s in m['sources'].items():
        options={} if admitted_root is None else {'owner_admitted_root':admitted_root/s['root']}
        fence=SourceFence(root/s['root'],s['commit'],git_executable=str(git),git_sha256=pin,**options)
        snapshot=fence.check()
        need(snapshot['tree']==s['tree'] and all(p['comparison']=='RAW_IDENTICAL' for p in snapshot['runtime_files'].values()))
        origin=fence.git('config','--get','remote.origin.url').decode().strip()
        need(origin in ('https://github.com/'+s['repository'],'https://github.com/'+s['repository']+'.git'))
        results[name]=snapshot
    return results


def prepare(root,manifest_sha256):
    root=_safe_path(root).resolve();report=lab_release.verify_capsule(root,manifest_sha256);m=report['manifest']
    c,raw=read_config(root/m['runtime_config'],allow_physical=True)
    need({'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}==m['files'][m['runtime_config']])
    c=validate_config(c,m,root);verify_sources(root,m)
    # Use the admitted manifest digest for runtime identity; the configuration
    # cannot recursively contain the digest of a manifest which hashes itself.
    c['release_sha256']=manifest_sha256
    return c,report


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=('LAB_SIMULATION','TRUSTED_RELEASE'),required=True)
    p.add_argument('--root',required=True);p.add_argument('--manifest-sha256',required=True)
    p.add_argument('--execute',action='store_true');a=p.parse_args(argv)
    try:
        if a.mode!='LAB_SIMULATION':
            print('BLOCKED_NO_TRUSTED_PUBLISHER; no unsigned fallback');return 1
        if a.execute:
            # Canonical managed entrypoints require a separately qualified live
            # startup_admission callback. A config/CLI flag cannot construct it.
            # Deny before privileges, directories, sockets or child processes.
            print('BLOCKED: CANONICAL_STARTUP_ADMISSION_REQUIRED; processes=NOT_STARTED');return 1
        prepare(_safe_path(a.root),a.manifest_sha256)
        print('LAB_SIMULATION_VERIFIED; processes=NOT_STARTED; physical=NOT_RUN');return 0
    except Exception:
        print('BLOCKED: LAB_RUNTIME_REJECTED; trading_authorized=false');return 1


if __name__=='__main__':raise SystemExit(main())
