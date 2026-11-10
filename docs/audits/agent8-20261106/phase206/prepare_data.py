"""DATA inventory preparation; no project/third-party import or execution."""
import hashlib,json,os,stat,subprocess
from pathlib import Path
ROOT=Path(__file__).parent
PY=Path('C:/Users/LS-5/AppData/Local/Python/pythoncore-3.12-64/python.exe')
GIT='C:/Program Files/Git/cmd/git.exe'
DEPS=Path('C:/Users/LS-5/.codex/atomic-read-unit-deps-20261110')
def ordinary(p,directory=False):
    for n in [*reversed(p.parents),p]:
        s=n.lstat()
        if stat.S_ISLNK(s.st_mode) or getattr(s,'st_reparse_tag',0):raise ValueError('REPARSE')
        if n!=p or directory:
            if not stat.S_ISDIR(s.st_mode):raise ValueError('NOT_DIRECTORY')
        elif not stat.S_ISREG(s.st_mode) or s.st_nlink!=1:raise ValueError('NOT_SINGLE_REGULAR')
    return p.stat()
def raw(p):
    s=ordinary(p)
    with p.open('rb') as f:b=f.read();q=os.fstat(f.fileno())
    t=ordinary(p)
    if any((v.st_dev,v.st_ino,v.st_size,v.st_mtime_ns)!=(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns) for v in (q,t)) or len(b)!=s.st_size:raise ValueError('CHANGED')
    return b
def record(p):
    b=raw(p);return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def git(root,*args):
    env={k:v for k,v in os.environ.items() if not k.upper().startswith('GIT_')}
    env.update(GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL=os.devnull,GIT_CONFIG_SYSTEM=os.devnull,GIT_TERMINAL_PROMPT='0',GIT_NO_REPLACE_OBJECTS='1')
    return subprocess.run([GIT,'--no-replace-objects','-C',str(root),*args],env=env,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=60).stdout
def sources(name,head,tree,count):
    root=ROOT/name;ordinary(root,True)
    if git(root,'rev-parse','HEAD').decode().strip()!=head or git(root,'rev-parse','HEAD^{tree}').decode().strip()!=tree:raise ValueError('SOURCE_ID')
    if git(root,'status','--porcelain','--untracked-files=all'):raise ValueError('DIRTY')
    expected={}
    for row in git(root,'ls-tree','-rz','--full-tree','HEAD').split(b'\0'):
        if not row:continue
        meta,path=row.split(b'\t',1);mode,kind,oid=meta.split();name=path.decode('utf8')
        if kind!=b'blob' or mode not in (b'100644',b'100755'):raise ValueError('MODE')
        p=root/name;b=raw(p)
        if hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()!=oid.decode():raise ValueError('RAW_BLOB')
        expected[name]=dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),blob=oid.decode())
    found=set()
    for d,dirs,files in os.walk(root,followlinks=False):
        if Path(d)==root:dirs.remove('.git')
        ordinary(Path(d),True)
        for n in dirs:ordinary(Path(d)/n,True)
        for n in files:ordinary(Path(d)/n);found.add((Path(d)/n).relative_to(root).as_posix())
    if len(expected)!=count or found!=set(expected):raise ValueError('SOURCE_INVENTORY')
    return dict(root=str(root),head=head,tree=tree,files=expected)
def main():
    if record(PY)['sha256']!='4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a':raise ValueError('PYTHON_PIN')
    source=[sources('unified','228df98801c572286abc67731c3d3fadea5db061','92a05710c6f6c06dbef44f2dc7159e925be39e37',1870),sources('grid','fb177d14b1e6e399bd9b66ae7cb35d3838acbd81','2cba4b0a1ee7621ef213600d6334db8e9ac7dae1',824)]
    expected=json.loads(raw(DEPS/'EXTRACTED-FILES.json'));actual={}
    for d,dirs,files in os.walk(DEPS/'site',followlinks=False):
        ordinary(Path(d),True)
        for n in dirs:ordinary(Path(d)/n,True)
        for n in files:
            p=Path(d)/n;rel=p.relative_to(DEPS/'site').as_posix();actual[rel]=record(p)
    if set(actual)!=set(expected) or any(actual[n]!={k:expected[n][k] for k in ('bytes','sha256')} for n in actual):raise ValueError('DEPS_INVENTORY')
    ordinary(DEPS/'cache',True)
    if list((DEPS/'cache').iterdir()):raise ValueError('CACHE_NOT_EMPTY')
    runtime={};excluded=0
    for base in (PY.parent/'Lib',PY.parent/'DLLs'):
        for d,dirs,files in os.walk(base,followlinks=False):
            ordinary(Path(d),True)
            dirs[:]=[n for n in dirs if n not in ('site-packages','__pycache__')]
            for n in dirs:ordinary(Path(d)/n,True)
            for n in files:
                if n.lower().endswith(('.pyc','.pyo')):excluded+=1;continue
                p=Path(d)/n;runtime[str(p)]=record(p)
    for p in PY.parent.iterdir():
        if p.suffix.lower() in ('.exe','.dll','.pyd','.zip'):runtime[str(p)]=record(p)
    capsule=dict(state='SOURCE_DATA_READY_ACTUAL10_HELD',python=str(PY),sources=source,deps_root=str(DEPS/'site'),deps=actual,cache=str(DEPS/'cache'),runtime=runtime,excluded_cache_policy='Lib site-packages and every __pycache__ excluded; pyc/pyo not admitted; future -X pycache_prefix uses empty external cache',excluded_noncache_pyc_count=excluded,remaining_gaps=['Actual imports/DSO/transitive Windows DLL loaded origins pending','Audit hook cooperative trusted-source boundary, not hostile sandbox/process family containment','Runner source not executed or qualified','Direct Python handle cleanup only; no allowed descendants; no Windows Job guarantee'])
    with (ROOT/'CAPSULE.json').open('x',encoding='utf8') as f:json.dump(capsule,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps(dict(sources=[len(s['files']) for s in source],deps=len(actual),runtime=len(runtime),state=capsule['state'])))
if __name__=='__main__':main()
