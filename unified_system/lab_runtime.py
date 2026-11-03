"""Explicit owner-admitted lab entrypoint; never a trusted-release fallback.

Launch only reviewed/pinned own components. This is not an arbitrary-code sandbox.
The existing hosted-only CLI, signing gates and Grid fleet ownership are retained.
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
from .runtime_cli import validate_config as base_config,read_config,make_runtime,run_runtime
from .runtime_process import _safe_path

ENVIRONMENT_KEYS={
    'PATH','UNIFIED_GIT_EXECUTABLE','UNIFIED_GIT_SHA256','UNIFIED_SOURCE_ROOT',
    'UNIFIED_ROOT_SOURCE_COMMIT','UNIFIED_SOURCE_COMMIT','GIT_CONFIG_NOSYSTEM',
    'GIT_CONFIG_GLOBAL','GIT_CONFIG_SYSTEM','GIT_NO_REPLACE_OBJECTS','GIT_NO_LAZY_FETCH',
    'NO_PROXY','MATH_ENGINE_PORT','TERMINAN_RUNTIME_V2_SNAPSHOT','POSTGRES_DSN',
    'GRID_COORDINATION_MODE','GRID_COORDINATION_ISOLATED_LAB','GRID_HA_REQUIRED',
    'PROGRAMDATA','PROGRAMFILES','ML_ARTIFACT_ROOT','ARCHIVE_ROOT','STRATEGY_CACHE_DIR',
    'BYBIT_REST_URL','BYBIT_WS_URL','BYBIT_ARCHIVE_BASE_URL','LOG_LEVEL','RETENTION_ENABLED',
    'ROLE','NODE_ID','NODE_ROLE','COORDINATOR_URL','GRID_INSTALL_ROOT','GRID_RELEASE_MANIFEST',
    'GRID_CONTROL_JOURNAL','GRID_CONTROL_SNAPSHOTS','GRID_LAB_AUTH_PATH','GRID_LAB_AUTH_SHA256',
    'TEMP','TMP','USERPROFILE','HOME','APPDATA','LOCALAPPDATA','TERMINAN_LAB_SNAPSHOT',
}
PUBLIC_ENDPOINTS={'BYBIT_REST_URL':'https://api.bybit.com',
                  'BYBIT_WS_URL':'wss://stream.bybit.com/v5/public/linear',
                  'BYBIT_ARCHIVE_BASE_URL':'https://public.bybit.com/trading'}
LAB_NODES=frozenset(('LS5','PC1','PC2','PC3','PC4','LS7'))
LAB_HOSTNAMES={'LS5':'LS5','PC1':'Easy','PC2':'Leitstelle1','PC3':'LS03e','PC4':'LS4','LS7':'LS-07'}


def need(ok):
    if not ok:raise ValueError('LAB_RUNTIME_REJECTED')


def child_environment(input=None):
    input=os.environ if input is None else input
    keep={'SYSTEMROOT','WINDIR','SYSTEMDRIVE','TEMP','TMP','COMPUTERNAME','USERPROFILE',
          'APPDATA','LOCALAPPDATA','OS','PROCESSOR_ARCHITECTURE'}
    e={k:v for k,v in input.items() if k.upper() in keep}
    e.update(UNIFIED_DEPLOYMENT_MODE='LAB_SIMULATION',UNIFIED_ORDER_MODE='PAPER_ONLY',
             UNIFIED_TRADING_AUTHORIZED='false',PYTHONDONTWRITEBYTECODE='1')
    return e


def launch_profile(name,p,root,m,state,node_id):
    """Closed reviewed source entrypoints, not a generic command launcher."""
    argv=p['argv'];source=root/m['sources'][name]['root']
    port=str(urlsplit(p['health_url']).port)
    if name=='math':
        need(len(argv)==2 and _safe_path(argv[1]).resolve()==source/'src/math-engine-server.mjs')
        return
    bootstrap=root/m['sources']['unified-system']['root']/'unified_system/owned_python.py'
    need(len(argv)>7 and argv[1:4]==['-I','-S','-B'] and _safe_path(argv[4]).resolve()==bootstrap)
    need(bootstrap.relative_to(root).as_posix() in m['files'])
    index=5;roots=[];dependencies=[]
    while index<len(argv) and argv[index] in ('--source-root','--dependency-root'):
        need(index+1<len(argv));value=_safe_path(argv[index+1]).resolve();need(root in value.parents)
        (roots if argv[index]=='--source-root' else dependencies).append(value);index+=2
    need(len(roots)==1 and len(dependencies)==len(set(dependencies)) and len(dependencies)<=16)
    need(roots[0]==source if name!='grid' else root in roots[0].parents)
    control=node_id.upper()=='LS5'
    modules={'grid':'uvicorn' if control else 'grid.owned_worker_service','meta_analyse':'meta_analyse.headless_service',
             'strattester':'strattester.owned_results_service','terminan':'terminan.unified_runner'}
    need(argv[index:index+3]==['--module',modules[name],'--']);tail=argv[index+3:]
    if name=='grid':
        need(tail==(['grid.coordinator:app','--host','127.0.0.1','--port',port,'--no-access-log'] if control else ['--execute','--port',port]))
        if not control:need(roots[0]==source)
    if name=='meta_analyse':need(tail==['--execute','--port',port])
    if name=='terminan':need(tail==['--expected-sha',m['sources'][name]['commit'],'--port',port])
    if name=='strattester':
        need(len(tail)==5 and tail[:2]==['--serve','--store'] and tail[3:]==['--port',port])
        need(state in _safe_path(tail[2]).resolve().parents)


def validate_config(c,m,root,*,hostname=None):
    root=_safe_path(root).resolve();c=copy.deepcopy(c)
    base_config(c,allow_physical=True)
    need(c['schema']=='unified.runtime.config.v2')
    need(c['node_id'].upper() in LAB_NODES)
    actual_host=(hostname or socket.gethostname()).split('.')[0].casefold()
    need(actual_host in (c['node_id'].casefold(),LAB_HOSTNAMES[c['node_id'].upper()].casefold()))
    need(c['release_id']==m['release_id'])
    state=_safe_path(c['state_root']).resolve();snapshot=_safe_path(c['snapshot_path']).resolve()
    need(state!=root and root not in state.parents and state not in root.parents and state in snapshot.parents)
    def pin(path,sha):
        p=_safe_path(path).resolve()
        try:name=p.relative_to(root).as_posix()
        except ValueError:raise ValueError('LAB_RUNTIME_REJECTED') from None
        need(name in m['files'] and m['files'][name]['sha256']==sha)
    for spec in c['specs']:
        s=m['sources'][spec['module_id']]
        need(spec['version']==s['version'] and set(spec['dependencies'])==set(s['dependencies']))
    for name,p in c['programs'].items():
        cwd=_safe_path(p['cwd']).resolve();need(cwd==root/m['sources'][name]['root'])
        pin(p['argv'][0],p['executable_sha256'])
        launch_profile(name,p,root,m,state,c['node_id'])
        for argument in p['argv'][1:]:
            # Paths supplied to loaders/modules must stay in the admitted
            # capsule, or in the separate mutable state namespace.
            if Path(argument).is_absolute():
                value=_safe_path(argument).resolve()
                need(root in value.parents or state==value or state in value.parents)
            need(argument.casefold() not in ('--import','--require','-r','--eval','--loader','--experimental-loader'))
        for file,sha in p['file_pins'].items():pin(cwd/file,sha)
        for file,sha in p.get('external_file_pins',{}).items():pin(file,sha)
        env=p.get('env',{});need(len({k.upper() for k in env})==len(env))
        for key,value in env.items():
            key=key.upper();need(key in ENVIRONMENT_KEYS)
            if key in PUBLIC_ENDPOINTS:need(value==PUBLIC_ENDPOINTS[key])
            if key in ('PROGRAMDATA','PROGRAMFILES','ML_ARTIFACT_ROOT','ARCHIVE_ROOT','STRATEGY_CACHE_DIR','TERMINAN_RUNTIME_V2_SNAPSHOT','TERMINAN_LAB_SNAPSHOT','GRID_CONTROL_JOURNAL','GRID_CONTROL_SNAPSHOTS','GRID_LAB_AUTH_PATH','TEMP','TMP','USERPROFILE','HOME','APPDATA','LOCALAPPDATA'):
                target=_safe_path(value).resolve();need(target==state or state in target.parents)
            if key=='GRID_LAB_AUTH_SHA256':lab_release.digest(value)
            if key=='ROLE':need(name=='grid' and value==('coordinator' if c['node_id'].upper()=='LS5' else 'worker'))
            if key=='NODE_ID':need(name=='grid' and value==c['node_id'])
            if key=='NODE_ROLE':need(name=='grid' and value==('CONTROL' if c['node_id'].upper()=='LS5' else 'WORKER'))
            if key=='COORDINATOR_URL':
                u=urlsplit(value);need(name=='grid' and u.scheme=='http' and u.hostname=='127.0.0.1' and u.port is not None and not u.username and not u.password and not u.path and not u.query and not u.fragment)
            if key=='GRID_INSTALL_ROOT':need(name=='grid' and _safe_path(value).resolve()==root/m['sources']['grid']['root'])
            if key=='GRID_RELEASE_MANIFEST':
                need(name=='grid');path=_safe_path(value).resolve()
                try:relative=path.relative_to(root).as_posix()
                except ValueError:raise ValueError('LAB_RUNTIME_REJECTED') from None
                need(relative in m['files'])
            if key=='PATH':
                for entry in value.split(os.pathsep):
                    need(Path(entry).is_absolute());target=_safe_path(entry).resolve()
                    need(target==root or root in target.parents)
            if key=='UNIFIED_SOURCE_ROOT':need(_safe_path(value).resolve()==root/m['sources']['unified-system']['root'])
            if key=='UNIFIED_SOURCE_COMMIT':need(value==m['sources'][name]['commit'])
            if key=='UNIFIED_ROOT_SOURCE_COMMIT':need(value==m['sources']['unified-system']['commit'])
            if key=='UNIFIED_GIT_EXECUTABLE':need(_safe_path(value).resolve()==root/m['git'])
            if key=='UNIFIED_GIT_SHA256':need(value==m['files'][m['git']]['sha256'])
            if key=='GRID_COORDINATION_MODE':need(value in ('legacy','consul'))
            if key=='GRID_COORDINATION_ISOLATED_LAB':need(value=='true')
            if key=='POSTGRES_DSN':
                u=urlsplit(value)
                need(u.scheme in ('postgres','postgresql') and u.hostname in ('127.0.0.1','::1')
                     and u.username and u.username.startswith('unified_lab_')
                     and u.path.startswith('/unified_lab_') and not u.query and not u.fragment)
        # Never inherit a production ProgramData/ProgramFiles default. These
        # deterministic per-component paths also remain stable on restarts.
        env=p.setdefault('env',{})
        defaults={'PROGRAMDATA':'data','PROGRAMFILES':'program-files','ML_ARTIFACT_ROOT':'artifacts',
                  'ARCHIVE_ROOT':'archive','STRATEGY_CACHE_DIR':'strategies',
                  'TEMP':'temp','TMP':'temp','USERPROFILE':'profile','HOME':'profile',
                  'APPDATA':'profile/AppData/Roaming','LOCALAPPDATA':'profile/AppData/Local'}
        for key,suffix in defaults.items():
            if key not in {k.upper() for k in env}:env[key]=str(state/name/suffix)
        if name=='grid':
            if c['node_id'].upper()=='LS5':need(any(k.upper()=='POSTGRES_DSN' for k in env))
            else:need(not any(k.upper()=='POSTGRES_DSN' for k in env))
            normalized={k.upper():v for k,v in env.items()}
            need(('GRID_LAB_AUTH_PATH' in normalized)==('GRID_LAB_AUTH_SHA256' in normalized))
            env['ROLE']='coordinator' if c['node_id'].upper()=='LS5' else 'worker'
            env['NODE_ID']=c['node_id'];env['NODE_ROLE']='CONTROL' if c['node_id'].upper()=='LS5' else 'WORKER'
            if 'GRID_CONTROL_JOURNAL' not in normalized:env['GRID_CONTROL_JOURNAL']=str(state/name/'control-state.json')
            if 'GRID_CONTROL_SNAPSHOTS' not in normalized:env['GRID_CONTROL_SNAPSHOTS']=str(state/name/'control-snapshots')
            for key,value in PUBLIC_ENDPOINTS.items():
                if key not in {k.upper() for k in env}:env[key]=value
            if 'GRID_COORDINATION_ISOLATED_LAB' not in {k.upper() for k in env}:env['GRID_COORDINATION_ISOLATED_LAB']='true'
    return c


def read_grid_auth(path,expected_sha256,*,node_id,release_id,source_commit):
    """Read operator-provisioned private lab enrollment, never exchange secrets."""
    lab_release.digest(expected_sha256)
    path=lab_release.regular(path);need(path.stat().st_size<=8192)
    with path.open('rb') as stream:raw=stream.read(8193)
    need(len(raw)<=8192 and hashlib.sha256(raw).hexdigest()==expected_sha256)
    def unique(pairs):
        out={}
        for key,value in pairs:need(key not in out);out[key]=value
        return out
    record=json.loads(raw.decode('utf8'),object_pairs_hook=unique)
    lab_release.exact(record,('schema','node_id','role','release_id','source_commit','grid_shared_token','node_credential','postgres_password'))
    need(record['schema']=='unified.lab.grid-auth.v2' and node_id.upper() in LAB_NODES)
    need(record['node_id']==node_id and record['release_id']==release_id and record['source_commit']==source_commit)
    lab_release.digest(record['grid_shared_token'])
    need(record['role']==('CONTROL' if node_id.upper()=='LS5' else 'WORKER'))
    result={'GRID_SHARED_TOKEN':record['grid_shared_token']}
    if node_id.upper()=='LS5':
        need(record['node_credential'] is None)
        lab_release.digest(record['postgres_password'])
        result['PGPASSWORD']=record['postgres_password']
    else:
        need(record['postgres_password'] is None)
        need(type(record['node_credential']) is str and re.fullmatch('[A-Za-z0-9_-]{64,128}',record['node_credential']))
        result['NODE_CREDENTIAL']=record['node_credential']
    return result


def verify_sources(root,m):
    from integration.source_guard import SourceFence
    git=root/m['git'];pin=m['files'][m['git']]['sha256'];results={}
    for name,s in m['sources'].items():
        fence=SourceFence(root/s['root'],s['commit'],git_executable=str(git),git_sha256=pin)
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
            from .lab_privileges import remove_lab_write_bypass_privileges
            remove_lab_write_bypass_privileges()
        root=_safe_path(a.root);c,report=prepare(root,a.manifest_sha256)
        if not a.execute:
            print('LAB_SIMULATION_VERIFIED; processes=NOT_STARTED; physical=NOT_RUN');return 0
        def authorize(action,module):
            if action!='start' or module not in MODULE_IDS:return False
            # Recheck complete capsule/source identity on every start/restart.
            current,_=prepare(root,a.manifest_sha256)
            return current==c
        grid_env={k.upper():v for k,v in c['programs']['grid']['env'].items()}
        need('GRID_LAB_AUTH_PATH' in grid_env and 'GRID_LAB_AUTH_SHA256' in grid_env)
        auth=read_grid_auth(grid_env['GRID_LAB_AUTH_PATH'],grid_env['GRID_LAB_AUTH_SHA256'],node_id=c['node_id'],
                            release_id=c['release_id'],source_commit=report['manifest']['sources']['grid']['commit'])
        for program in c['programs'].values():
            for key,value in program['env'].items():
                if key.upper() in ('TEMP','TMP','USERPROFILE','HOME','APPDATA','LOCALAPPDATA','PROGRAMDATA','PROGRAMFILES','ML_ARTIFACT_ROOT','ARCHIVE_ROOT','STRATEGY_CACHE_DIR','GRID_CONTROL_SNAPSHOTS'):
                    _safe_path(value).mkdir(parents=True,exist_ok=True)
        def environment(module):
            env=child_environment()
            if module=='grid':env.update(auth)
            return env
        runtime=make_runtime(c,authorize,child_environment=environment);stop=threading.Event();previous={}
        try:
            for sig in (signal.SIGINT,signal.SIGTERM):previous[sig]=signal.signal(sig,lambda *_:stop.set())
            run_runtime(c,runtime,stop_event=stop)
        finally:
            for sig,handler in previous.items():signal.signal(sig,handler)
        return 0
    except Exception:
        print('BLOCKED: LAB_RUNTIME_REJECTED; trading_authorized=false');return 1


if __name__=='__main__':raise SystemExit(main())
