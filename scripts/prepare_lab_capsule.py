"""Prepare a new unsigned LS5 LAB capsule. Never starts a database or service.

Run only from independently reviewed builder sources. Failures retain new inactive
output directories for inspection. No overwrite, cleanup, signing or trust bypass.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
import socket
import stat
import subprocess
import sys
import zipfile

WORKSPACE=Path(r'C:\Projects\UnifiedWorkspace')
CACHE=WORKSPACE/'.local-runs/btc-20261102-01'
NAMES={'unified-system':'unified-system','grid':'bybit-cluster-grid','strattester':'strattester','math':'math','meta_analyse':'meta_analyse','terminan':'Terminan'}
GRAPH={'unified-system':[],'grid':['unified-system'],'math':['unified-system'],'meta_analyse':['grid','math'],'strattester':['grid','math'],'terminan':['meta_analyse','strattester']}
ARCHIVES={'python.3.12.10.nupkg':'0eb85c2dfccccf1b17352de4c397f69194035b7d37149eacc16f1147d93de3b8','node-v22.23.4-win-x64.zip':'cbc74b5e0982c9dbb41525fd8fb5dcd32fbee237863f7829072f4639a1ce5f20','MinGit-2.56.0.4-64-bit.zip':'e3bf78351fe777fba47ddee5950082f8a98bb0f02604fdc7ba3ee2cb68ffa877'}
LOCK_SHA='7eab2508a19e5b0ac54efbb9048c6841082edf140848982d6ace2c2983ff549c'
SYMBOLS=['BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','BNBUSDT','DOGEUSDT','ADAUSDT','AVAXUSDT','LINKUSDT','DOTUSDT']

def need(ok,reason):
    if not ok:raise ValueError(reason)
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):h.update(block)
    return h.hexdigest()
def canonical(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def write(path,value):
    with Path(path).open('xb') as stream:stream.write(canonical(value))
def safe(path):
    raw=str(path);p=Path(raw)
    need(p.is_absolute() and not raw.startswith(('\\\\','//')),'ABSOLUTE_LOCAL_PATH_REQUIRED')
    lexical=raw.replace('\\','/').split('/')
    need(not any(part in ('.','..') for part in lexical),'NONCANONICAL_PATH')
    need(not any(part.endswith((' ','.')) or ':' in part for part in p.parts[1:]),'NONCANONICAL_PATH')
    # lstat also sees dangling symlinks; exists() would silently skip those.
    for part in (*reversed(p.parents),p):
        try:facts=part.lstat()
        except FileNotFoundError:continue
        need(not stat.S_ISLNK(facts.st_mode) and not getattr(facts,'st_file_attributes',0)&1024,'LINK_REJECTED')
    need(p.resolve(strict=False)==p,'NONCANONICAL_PATH')
    return p

def destinations(output,state):
    output=safe(output);state=safe(state)
    need(output!=state and output.parent==state.parent,'SEPARATE_SIBLINGS_REQUIRED')
    need(output.parent.is_dir() and not output.exists() and not state.exists(),'NEW_DESTINATIONS_REQUIRED')
    return output,state

def inventory(root):
    from unified_system.lab_release import relative,hash_file
    files={};dirs=[];seen=set()
    for directory,children,names in os.walk(root,followlinks=False):
        safe(Path(directory))
        for name in children+names:
            p=safe(Path(directory)/name);rel=p.relative_to(root).as_posix();relative(rel)
            need(rel.casefold() not in seen,'CASE_ALIAS');seen.add(rel.casefold())
            need(p.name.casefold() not in ('.env','.env.local','.env.production'),'ACTIVE_ENV_REJECTED')
            if p.is_dir():dirs.append(rel)
            else:files[rel]=hash_file(p)
    return files,sorted(dirs)

def extract(archive,target,prefix=''):
    # Validate the entire selected archive namespace before writing any member.
    from unified_system.windows_wheels import zip_path
    with zipfile.ZipFile(archive) as z:
        selected=[];seen=set()
        for info in z.infolist():
            name,_=zip_path(info)
            if prefix and not name.startswith(prefix):continue
            name=name[len(prefix):]
            if not name:continue
            need(name.casefold() not in seen,'ARCHIVE_ALIAS');seen.add(name.casefold());selected.append((info,name))
        need(selected,'EMPTY_ARCHIVE_SELECTION')
        target.mkdir()
        for info,name in selected:
            dest=target/name
            if info.is_dir():dest.mkdir(parents=True,exist_ok=True)
            else:
                dest.parent.mkdir(parents=True,exist_ok=True)
                with z.open(info) as src,dest.open('xb') as out:shutil.copyfileobj(src,out)

def environment(git=None):
    allowed={'SYSTEMROOT','WINDIR','SYSTEMDRIVE','TEMP','TMP','COMPUTERNAME','USERPROFILE','APPDATA','LOCALAPPDATA','OS','PROCESSOR_ARCHITECTURE'}
    env={k:v for k,v in os.environ.items() if k.upper() in allowed}
    env.update(GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL=os.devnull,GIT_CONFIG_SYSTEM=os.devnull,GIT_TERMINAL_PROMPT='0',GIT_NO_REPLACE_OBJECTS='1',GIT_NO_LAZY_FETCH='1',PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',PIP_CONFIG_FILE=os.devnull,PIP_DISABLE_PIP_VERSION_CHECK='1')
    if git:env['PATH']=str(git.parent)
    return env

def run(argv,env,cwd=None,timeout=1200):
    result=subprocess.run(list(map(str,argv)),env=env,cwd=cwd,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
    need(result.returncode==0,'CHILD_COMMAND_FAILED:'+Path(str(argv[0])).name)
    return result.stdout.decode('utf8',errors='strict').strip()

def require_clean(source,git,env):
    from integration.source_guard import SourceFence
    SourceFence(source,git_executable=str(git),git_sha256=sha(git)).check_metadata()
    need(not run([git,'-C',source,'status','--porcelain','--untracked-files=all'],env),'SOURCE_DIRTY:'+source.name)
    return run([git,'-C',source,'rev-parse','HEAD'],env)

def clone_source(source,target,head,repository,git,env):
    run([git,'-c','init.templateDir=','init',target],env)
    def command(*args):return run([git,'-C',target,*args],env)
    command('config','core.autocrlf','false')
    command('-c','protocol.file.allow=always','fetch','--depth=1','--no-tags',source,head)
    command('checkout','--detach','FETCH_HEAD')
    command('remote','add','origin','https://github.com/'+repository+'.git')
    need(command('rev-parse','HEAD')==head,'SNAPSHOT_HEAD_CHANGED')

def new_auth(state,release,commit):
    need(os.name=='nt','WINDOWS_PRIVATE_ACL_REQUIRED')
    env=environment();system=Path(os.environ['SYSTEMROOT'])/'System32'
    sid=run([system/'whoami.exe','/user','/fo','csv','/nh'],env).split(',')[-1].strip('"')
    need(re.fullmatch(r'S-1-5-[0-9-]+',sid),'CURRENT_SID_UNVERIFIED')
    run([system/'icacls.exe',state,'/inheritance:r','/grant:r','*'+sid+':(OI)(CI)F','*S-1-5-18:(OI)(CI)F','*S-1-5-32-544:(OI)(CI)F'],env)
    # A new directory has no explicit inherited entries after inheritance removal.
    # Verify the resulting ACL through a fixed local PowerShell expression.
    literal="'"+str(state).replace("'","''")+"'"
    expression="$a=Get-Acl -LiteralPath "+literal+"; if(-not $a.AreAccessRulesProtected){exit 2}; $a.Access | ForEach-Object {if($_.AccessControlType -ne 'Allow' -or $_.IsInherited -or $_.FileSystemRights -ne 'FullControl'){exit 3}; $_.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value}"
    actual=run([system/'WindowsPowerShell/v1.0/powershell.exe','-NoProfile','-NonInteractive','-Command',expression],env).splitlines()
    need(set(actual)=={sid,'S-1-5-18','S-1-5-32-544'},'PRIVATE_ACL_UNVERIFIED')
    private=state/'private';private.mkdir();path=private/'grid-auth.json'
    write(path,dict(schema='unified.lab.grid-auth.v2',node_id='LS5',role='CONTROL',release_id=release,source_commit=commit,grid_shared_token=os.urandom(32).hex(),node_credential=None,postgres_password=os.urandom(32).hex()))
    return path,sha(path)

def free_ports(names):
    sockets=[]
    try:
        for _ in names:
            s=socket.socket();s.bind(('127.0.0.1',0));sockets.append(s)
        return dict(zip(names,[s.getsockname()[1] for s in sockets]))
    finally:
        for s in sockets:s.close()

def runtime_config(root,state,sources,snapshots,git,python,node,release,auth,pgport):
    ports=free_ports(NAMES);bootstrap=root/'sources/unified-system/unified_system/owned_python.py';deps=root/'dependencies/site-packages';unified=root/'sources/unified-system'
    common={'PATH':str(git.parent),'UNIFIED_GIT_EXECUTABLE':str(git),'UNIFIED_GIT_SHA256':sha(git),'UNIFIED_SOURCE_ROOT':str(unified),'UNIFIED_ROOT_SOURCE_COMMIT':sources['unified-system']['commit'],'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':os.devnull,'GIT_CONFIG_SYSTEM':os.devnull,'GIT_NO_REPLACE_OBJECTS':'1','GIT_NO_LAZY_FETCH':'1','NO_PROXY':'127.0.0.1,localhost'}
    programs={}
    for name,module,args in [('meta_analyse','meta_analyse.headless_service',['--execute','--port',str(ports['meta_analyse'])]),('strattester','strattester.owned_results_service',['--serve','--store',str(state/'results.sqlite3'),'--port',str(ports['strattester'])]),('terminan','terminan.unified_runner',['--expected-sha',sources['terminan']['commit'],'--port',str(ports['terminan'])]),('grid','uvicorn',['grid.coordinator:app','--host','127.0.0.1','--port',str(ports['grid']),'--no-access-log']),('math',None,[])]:
        source=root/sources[name]['root'];argv=[str(python),'-I','-S','-B',str(bootstrap),'--source-root',str(deps if name=='grid' else source)]
        for dep in ([source] if name=='grid' else [])+([unified] if name=='strattester' else [])+[deps]:
            if name=='grid' and dep==deps:continue
            argv+=['--dependency-root',str(dep)]
        argv+=['--module',module or '', '--',*args]
        if name=='math':argv=[str(node),str(source/'src/math-engine-server.mjs')]
        programs[name]={'argv':argv,'cwd':str(source),'executable_sha256':sha(node if name=='math' else python),'file_pins':{n:p['raw_sha256'] for n,p in snapshots[name]['runtime_files'].items()},'external_file_pins':{str(git):sha(git),**({str(bootstrap):sha(bootstrap)} if name!='math' else {})},'health_url':f'http://127.0.0.1:{ports[name]}/internal/v2/module/health','env':{**common,'UNIFIED_SOURCE_COMMIT':sources[name]['commit']}}
    programs['meta_analyse']['health_timeout_seconds']=1.
    programs['math']['env']['MATH_ENGINE_PORT']=str(ports['math'])
    programs['terminan']['env']['TERMINAN_RUNTIME_V2_SNAPSHOT']=str(state/'public/runtime.json')
    programs['terminan']['env']['TERMINAN_LAB_SNAPSHOT']=str(state/'public/lab-market-paper.json')
    suffix=re.sub('[^a-z0-9_]','_',release.lower())[:40]
    programs['grid']['env'].update(POSTGRES_DSN=f'postgresql://unified_lab_{suffix}@127.0.0.1:{pgport}/unified_lab_{suffix}',ROLE='coordinator',NODE_ID='LS5',NODE_ROLE='CONTROL',GRID_COORDINATION_MODE='legacy',GRID_COORDINATION_ISOLATED_LAB='true',GRID_HA_REQUIRED='false',GRID_LAB_AUTH_PATH=str(auth[0]),GRID_LAB_AUTH_SHA256=auth[1],GRID_CONTROL_JOURNAL=str(state/'grid/control.json'),GRID_CONTROL_SNAPSHOTS=str(state/'grid/snapshots'),LOG_LEVEL='WARNING',RETENTION_ENABLED='false')
    return dict(schema='unified.runtime.config.v2',node_id='LS5',release_id=release,release_sha256='0'*64,state_root=str(state),snapshot_path=str(state/'public/runtime.json'),http_port=ports['unified-system'],tick_seconds=.1,specs=[dict(module_id=n,version='1.0.0',api_major=1,dependencies=GRAPH[n],start_timeout=60) for n in NAMES],programs=programs)

# Distribution-to-native-module mapping for this admitted lock, not an inferred
# import-name transformation. Probe only installed, explicitly pinned packages.
NATIVE_MODULES={'numpy':'numpy','torch':'torch','psycopg':'psycopg',
    'psycopg-binary':'psycopg_binary','asyncpg':'asyncpg.protocol.protocol',
    'pydantic-core':'pydantic_core._pydantic_core','cffi':'_cffi_backend',
    'pillow':'PIL._imaging','psutil':'psutil._psutil_windows',
    'pyyaml':'yaml._yaml','pynacl':'nacl._sodium','pyside6-essentials':'PySide6.QtCore',
    'shiboken6':'shiboken6'}

def native_probe(pinned):
    need(set(NATIVE_MODULES)<=set(pinned),'NATIVE_PROBE_LOCK_MISMATCH')
    versions={n:pinned[n] for n in NATIVE_MODULES}
    return ('import sys, importlib, importlib.metadata\nsys.path.insert(0,sys.argv[1])\n'
        +'expected='+repr(versions)+'\n'
        +'for name,version in expected.items():\n assert importlib.metadata.version(name)==version, name\n'
        +'for module in '+repr(list(NATIVE_MODULES.values()))+':\n importlib.import_module(module)\n'
        +'import numpy, torch, psycopg\ntorch.set_num_threads(1)\n'
        +'assert int(numpy.dot(numpy.array([2,3]),numpy.array([4,5])))==23\n'
        +'assert int(torch.tensor([2,3]).sum())==5\n'
        +'assert torch.version.cuda is None and not torch.cuda.is_available()\n'
        +'assert psycopg.pq.__impl__=="binary"\n')

def bundled_pip_member(archive):
    with zipfile.ZipFile(archive) as z:
        matches=[n for n in z.namelist() if re.fullmatch(r'tools/Lib/ensurepip/_bundled/pip-[0-9.]+-py3-none-any[.]whl',n)]
        need(len(matches)==1,'BUNDLED_PIP_REQUIRED')
        return matches[0]

def pip_bootstrap():
    # Python is launched -I -S -B, so neither ambient .pth nor sitecustomize
    # executes. pip and all of its vendored dependencies come from this wheel.
    return ('import sys, runpy\n'
        'wheel=sys.argv.pop(1)\nsys.path.insert(0,wheel)\n'
        'runpy.run_module("pip",run_name="__main__")\n')

def npm_environment(env,node,git,cache,state):
    # npm rejects loading the same NUL path as both user and global config.
    # Separate new empty files also avoid loading ambient account settings.
    user=state/'npm-user.ini';global_config=state/'npm-global.ini'
    for path in (user,global_config):
        with path.open('xb'):pass
    return {**env,'PATH':str(node.parent)+os.pathsep+str(git.parent),
            'npm_config_cache':str(cache),'npm_config_userconfig':str(user),
            'npm_config_globalconfig':str(global_config),'npm_config_update_notifier':'false',
            'npm_config_audit':'false','npm_config_fund':'false'}

def build(args):
    root,state=destinations(args.output,args.state_root)
    need(args.node=='LS5' and socket.gethostname().split('.')[0].upper()=='LS5','LS5_ONLY')
    need(re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,79}',args.release_id),'RELEASE_ID_INVALID')
    need(1024<=args.postgres_port<=65535,'POSTGRES_PORT_INVALID')
    with socket.socket() as probe:probe.bind(('127.0.0.1',args.postgres_port))
    from unified_system import lab_release,windows_wheels
    from integration.source_guard import SourceFence
    cache=safe(args.cache);lock=WORKSPACE/'unified-system/integration/windows-candidate/requirements-cp312-win_amd64-cpu.lock'
    need(sha(lock)==LOCK_SHA,'LOCK_HASH_MISMATCH')
    for name,pin in ARCHIVES.items():need(sha(cache/name)==pin,'ARCHIVE_HASH_MISMATCH:'+name)
    wheels=windows_wheels.validate_windows_wheels(lock,cache/'wheels')
    need(wheels['result']=='CANDIDATE_BYTES_MATCH' and len(wheels['wheels'])==72 and wheels['candidate_bytes']==431771071,'WHEELS_REJECTED')
    pip_member=bundled_pip_member(cache/'python.3.12.10.nupkg')
    root.mkdir();state.mkdir();(root/'runtime').mkdir();(root/'sources').mkdir();(root/'locks').mkdir();(root/'dependencies').mkdir()
    # No executable or adjacent DLL is borrowed from an existing cache tree.
    extract(cache/'MinGit-2.56.0.4-64-bit.zip',root/'runtime/git')
    git=root/'runtime/git/ucrt64/bin/git.exe';env=environment(git)
    heads={n:require_clean(WORKSPACE/d,git,env) for n,d in NAMES.items()}
    extract(cache/'python.3.12.10.nupkg',root/'runtime/python','tools/')
    extract(cache/'node-v22.23.4-win-x64.zip',root/'runtime/node')
    python=root/'runtime/python/python.exe';node=root/'runtime/node/node-v22.23.4-win-x64/node.exe'
    sources={};snapshots={}
    for name,directory in NAMES.items():
        repository=lab_release.REPOSITORIES[name];target=root/'sources'/name
        clone_source(WORKSPACE/directory,target,heads[name],repository,git,env)
        snapshot=SourceFence(target,heads[name],git_executable=str(git),git_sha256=sha(git)).check()
        need(all(p['comparison']=='RAW_IDENTICAL' for p in snapshot['runtime_files'].values()),'RAW_SOURCE_REQUIRED')
        snapshots[name]=snapshot;sources[name]=dict(repository=repository,root='sources/'+name,commit=heads[name],tree=snapshot['tree'],version='1.0.0',dependencies={d:'1.0.0' for d in GRAPH[name]})
    target=root/'dependencies/site-packages'
    installer=state/'pip-bootstrap.py'
    with installer.open('x',encoding='utf8') as stream:stream.write(pip_bootstrap())
    pip_wheel=root/'runtime/python'/pip_member.removeprefix('tools/')
    run([python,'-I','-S','-B',installer,pip_wheel,'install','--no-index','--require-hashes','--only-binary=:all:','--no-compile','--target',target,'--find-links',cache/'wheels','-r',lock],env)
    expected={n:p['version'] for n,p in windows_wheels.parse_compiled_lock(lock.read_bytes()).items()}
    installed=list(importlib.metadata.distributions(path=[str(target)]))
    actual={windows_wheels.canonical(d.metadata['Name']):d.version for d in installed}
    need(actual==expected and len(actual)==len(installed)==72,'INSTALLED_METADATA_MISMATCH')
    # Fixed trusted probe is written by this builder, not loaded from candidate.
    verifier=state/'native-import-check.py'
    with verifier.open('x',encoding='utf8') as out:out.write(native_probe(expected))
    run([python,'-I','-S','-B',verifier,target],env)
    npm=node.parent/'node_modules/npm/bin/npm-cli.js'
    npm_env=npm_environment(env,node,git,safe(args.npm_cache) if args.npm_cache else cache/'npm-cache',state)
    run([node,npm,'ci','--ignore-scripts','--offline','--no-audit','--no-fund'],npm_env,cwd=root/'sources/math')
    shutil.copyfile(lock,root/'locks/requirements-cp312-win_amd64-cpu.lock')
    vendor={'schema':'unified.lab.vendor-lock.v1','archives':ARCHIVES,'wheels':wheels['wheels'],'postgresql':None,'npm_package_lock_sha256':sha(root/'sources/math/package-lock.json')}
    if args.include_postgres:
        origin=Path(r'C:\Program Files\PostgreSQL\18');dest=root/'runtime/postgresql';dest.mkdir()
        for part in ('bin','lib','share'):
            inventory(origin/part);shutil.copytree(origin/part,dest/part,symlinks=False)
        vendor['postgresql']={'version':run([dest/'bin/postgres.exe','--version'],env),'files':inventory(dest)[0]}
    write(root/'locks/vendor.json',vendor)
    auth=new_auth(state,args.release_id,heads['grid'])
    config=runtime_config(root,state,sources,snapshots,git,python,node,args.release_id,auth,args.postgres_port)
    write(root/'runtime-config.json',config)
    files,dirs=inventory(root)
    manifest=dict(schema='unified.lab-release.v1',mode='LAB_SIMULATION',release_id=args.release_id,sequence=args.sequence,market_access='PUBLIC_READ_ONLY',execution='PAPER_ONLY',credentials='FORBIDDEN',trading_authorized=False,sources=sources,files=files,directories=dirs,dependencies=[dict(name='python',version='3.12.10',lock_path='locks/vendor.json'),dict(name='node',version='22.23.4',lock_path='locks/vendor.json'),dict(name='mingit',version='2.56.0.4',lock_path='locks/vendor.json'),dict(name='python-packages',version='1',lock_path='locks/requirements-cp312-win_amd64-cpu.lock'),dict(name='npm',version='1',lock_path='sources/math/package-lock.json')],runtime_config='runtime-config.json',git=git.relative_to(root).as_posix(),instruments=SYMBOLS)
    write(root/'lab-release.json',manifest);digest=sha(root/'lab-release.json')
    lab_release.verify_capsule(root,digest)
    from unified_system.lab_runtime import validate_config,verify_sources
    validate_config(config,manifest,root,hostname='LS5');verify_sources(root,manifest)
    # Recheck original repositories so a concurrent edit cannot silently qualify.
    for n,d in NAMES.items():need(require_clean(WORKSPACE/d,git,environment(git))==heads[n],'SOURCE_CHANGED')
    return dict(result='PREPARED_UNSIGNED_LAB_CANDIDATE',capsule=str(root),state_root=str(state),manifest_sha256=digest,sources={n:{'commit':s['commit'],'tree':s['tree']} for n,s in sources.items()},database_provisioned=False,services_started=False)

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);p.add_argument('--state-root',required=True);p.add_argument('--release-id',required=True);p.add_argument('--node',default='LS5');p.add_argument('--sequence',type=int,default=1);p.add_argument('--cache',default=str(CACHE));p.add_argument('--postgres-port',type=int,default=55459);p.add_argument('--include-postgres',action='store_true');p.add_argument('--npm-cache');args=p.parse_args(argv)
    need(args.sequence>0,'SEQUENCE_INVALID');print(json.dumps(build(args),sort_keys=True));return 0

if __name__=='__main__':
    # Only this explicitly selected builder checkout supplies admission helpers.
    sys.dont_write_bytecode=True
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    raise SystemExit(main())
