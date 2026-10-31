"""Immutable six-owner release contract; external CMS pin is the trust anchor.

Validation proves schema/version closure and integrity only. A GitHub workflow
success, content hash or manifest publisher field cannot authorize deployment.
"""
import hashlib
import json
import re
from pathlib import PurePosixPath
from .module_catalog import MODULE_IDS

MAX_BYTES=1048576


def need(ok):
    if not ok:raise ValueError('UNIFIED_RELEASE_REJECTED')


def canonical(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()


def fields(value,keys):need(type(value) is dict and set(value)==set(keys))
def hexdigest(value,size):need(type(value) is str and re.fullmatch('[0-9a-f]{'+str(size)+'}',value))
def label(value):
    need(type(value) is str and re.fullmatch('[a-zA-Z0-9][a-zA-Z0-9._-]{0,79}',value))
    need(not value.endswith('.') and not re.match(r'(?i)^(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])(?:\.|$)',value))


def validate_manifest(m,*,expected_publisher):
    hexdigest(expected_publisher,64)
    fields(m,('schema','release_id','sequence','publisher_sha256','modules','execution_authority','trading_authorized'))
    need(m['schema']=='unified.release.v3' and m['publisher_sha256']==expected_publisher)
    label(m['release_id']);need(type(m['sequence']) is int and 1<=m['sequence']<=2**53-1)
    need(m['execution_authority'] is False and m['trading_authorized'] is False)
    need(type(m['modules']) is dict and set(m['modules'])==MODULE_IDS)
    seen=set();total=0
    for name,x in m['modules'].items():
        fields(x,('version','commit','tree','api_major','dependencies','artifact','provenance'))
        need(type(x['version']) is str and re.fullmatch(r'\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]{1,40})?',x['version']))
        hexdigest(x['commit'],40);hexdigest(x['tree'],40)
        need(type(x['api_major']) is int and x['api_major']==1)
        need(type(x['dependencies']) is dict and set(x['dependencies'])<=MODULE_IDS-{name})
        for dep,version in x['dependencies'].items():need(version==m['modules'][dep]['version'])
        a=x['artifact'];fields(a,('path','sha256','bytes'));hexdigest(a['sha256'],64)
        need(a['path']=='modules/'+name+'.zip')
        need(a['path'].casefold() not in seen);seen.add(a['path'].casefold())
        need(type(a['bytes']) is int and 1<=a['bytes']<=536870912);total+=a['bytes']
        p=x['provenance'];fields(p,('repository','run_id','attempt','workflow_sha'))
        need(type(p['repository']) is str and re.fullmatch('[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',p['repository']))
        need(type(p['run_id']) is str and re.fullmatch('[1-9][0-9]{0,19}',p['run_id']))
        need(type(p['attempt']) is int and 1<=p['attempt']<=10000)
        need(p['workflow_sha']==x['commit'])
    need(total<=1073741824)
    visited=set();visiting=set()
    def visit(name):
        need(name not in visiting)
        if name in visited:return
        visiting.add(name)
        for dep in m['modules'][name]['dependencies']:visit(dep)
        visiting.remove(name);visited.add(name)
    for name in sorted(MODULE_IDS):visit(name)
    need(len(canonical(m))<=MAX_BYTES)
    return m


def parse_manifest(raw,*,expected_publisher):
    need(type(raw) is bytes and 0<len(raw)<=MAX_BYTES)
    def unique(pairs):
        out={}
        for key,value in pairs:need(key not in out);out[key]=value
        return out
    try:m=json.loads(raw.decode('utf-8'),object_pairs_hook=unique,parse_constant=lambda _:need(False))
    except (ValueError,UnicodeError,RecursionError):raise ValueError('UNIFIED_RELEASE_REJECTED') from None
    validate_manifest(m,expected_publisher=expected_publisher)
    need(canonical(m)==raw)
    return m


def build_module_capsule(repository,descriptor,output,*,git_executable,git_sha256):
    """Prepare one exact-HEAD source capsule, never publish or install it.

    A temporary independent local clone leaves source refs/index untouched. The
    bundle carries only selected HEAD ancestry, not every repository branch.
    """
    import os,subprocess,tempfile,zipfile
    from pathlib import Path
    git=Path(git_executable);repository=Path(repository);output=Path(output)
    need(git.is_absolute() and git.is_file() and not git.is_symlink())
    need(hashlib.sha256(git.read_bytes()).hexdigest()==git_sha256)
    need(repository.is_dir() and (repository/'.git').exists() and not output.exists())
    hexdigest(descriptor['commit'],40);hexdigest(descriptor['tree'],40)
    env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')}
    env.update(GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL=os.devnull,GIT_CONFIG_SYSTEM=os.devnull,GIT_NO_REPLACE_OBJECTS='1',GIT_TERMINAL_PROMPT='0')
    def command(*args):return subprocess.check_output([str(git),'-c','core.hooksPath='+os.devnull,'-c','pack.threads=1','-c','pack.window=0','-c','pack.compression=9',*args],env=env,stderr=subprocess.PIPE,timeout=30)
    with tempfile.TemporaryDirectory(prefix='mission3-capsule-build-') as temp:
        root=Path(temp);source=root/'source'
        command('clone','--local','--no-hardlinks','--no-checkout',str(repository.absolute()),str(source))
        command('-C',str(source),'update-ref','refs/heads/capsule',descriptor['commit'])
        command('-C',str(source),'symbolic-ref','HEAD','refs/heads/capsule')
        need(command('-C',str(source),'rev-parse','HEAD^{tree}').decode().strip()==descriptor['tree'])
        bundle=root/'source.bundle';command('-C',str(source),'bundle','create',str(bundle),'HEAD')
        need(0<bundle.stat().st_size<=536870000)
        info=zipfile.ZipInfo('source.bundle',date_time=(1980,1,1,0,0,0))
        info.create_system=3;info.external_attr=0o100644<<16
        with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_STORED) as archive:
            archive.writestr(info,bundle.read_bytes())
    raw=output.read_bytes()
    return dict(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
