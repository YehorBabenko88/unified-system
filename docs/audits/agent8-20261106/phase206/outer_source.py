"""REVIEW ONLY: do not launch before separate Root allocation."""
import hashlib,json,os,stat,subprocess,threading,time
from pathlib import Path
ROOT=Path(__file__).parent
SEAL_SHA='22cd3b0e681e85da8e6ffa51d7d4b68ec9b1c63152404c7a2f923948c2a00faa'
def checked_file(path,expected):
    for n in [*reversed(path.parents),path]:
        s=n.lstat()
        if stat.S_ISLNK(s.st_mode) or getattr(s,'st_reparse_tag',0):raise RuntimeError('LINK_OR_REPARSE')
        if n!=path and not stat.S_ISDIR(s.st_mode):raise RuntimeError('ANCESTOR_NOT_DIRECTORY')
    if not stat.S_ISREG(s.st_mode) or s.st_nlink!=1 or s.st_size!=expected['bytes']:raise RuntimeError('FILE_METADATA')
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(65536),b''):h.update(b)
        after=os.fstat(f.fileno())
    final=path.lstat()
    if h.hexdigest()!=expected['sha256'] or any((v.st_dev,v.st_ino,v.st_size,v.st_mtime_ns)!=(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns) for v in (after,final)):raise RuntimeError('FILE_CHANGED')
def main():
    sealraw=(ROOT/'DRIVER-SEAL.json').read_bytes()
    if hashlib.sha256(sealraw).hexdigest()!=SEAL_SHA:raise RuntimeError('SEAL_PIN')
    for n,expected in json.loads(sealraw).items():
        b=(ROOT/n).read_bytes()
        if hashlib.sha256(b).hexdigest()!=expected:raise RuntimeError('DRIVER_PIN')
    capsule=json.loads((ROOT/'CAPSULE.json').read_bytes());cache=Path(capsule['cache'])
    if list(cache.iterdir()):raise RuntimeError('CACHE_NOT_EMPTY')
    # Interpreter/DLL/stdlib raw identity before even starting the inner interpreter.
    for name,expected in capsule['runtime'].items():checked_file(Path(name),expected)
    for source in capsule['sources']:
        for name,expected in source['files'].items():checked_file(Path(source['root'])/name,expected)
    for name,expected in capsule['deps'].items():checked_file(Path(capsule['deps_root'])/name,expected)
    env={k:v for k,v in os.environ.items() if k.upper() in ('SYSTEMROOT','WINDIR','SYSTEMDRIVE')}
    env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',PYTHONHASHSEED='0')
    cmd=[capsule['python'],'-I','-S','-B','-X','pycache_prefix='+str(cache),str(ROOT/'inner_source.py')]
    # Trusted reviewed test source permits no subprocess. This owns the direct
    # Python handle only; no Windows Job or malicious descendant containment claim.
    started=time.monotonic();budget=2*1024**2;total=0;exceeded=threading.Event();lock=threading.Lock();reader_errors=[]
    with (ROOT/'stdout.original.bin').open('xb') as out,(ROOT/'stderr.original.bin').open('xb') as err:
        child=subprocess.Popen(cmd,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,close_fds=True)
        def drain(pipe,destination):
            nonlocal total
            try:
                while True:
                    data=pipe.read(4096)
                    if not data:break
                    with lock:
                        remaining=max(0,budget-total);total+=len(data)
                        destination.write(data[:remaining]);destination.flush()
                        if total>budget:exceeded.set()
            except BaseException as exc:reader_errors.append(type(exc).__name__);exceeded.set()
        threads=[threading.Thread(target=drain,args=(child.stdout,out),daemon=True),threading.Thread(target=drain,args=(child.stderr,err),daemon=True)]
        for t in threads:t.start()
        reason=None
        while child.poll() is None:
            if exceeded.wait(.02):reason='OUTPUT_OR_READER_BOUNDARY';break
            if time.monotonic()-started>=90:reason='WHOLE_90S_TIMEOUT';break
        if reason:
            child.kill()
            try:child.wait(timeout=5)
            except subprocess.TimeoutExpired:reason+='__DIRECT_RETIREMENT_UNKNOWN'
        else:child.wait(timeout=5)
        for t in threads:t.join(timeout=1)
        if any(t.is_alive() for t in threads):reason=(reason or '')+'__PIPE_RETIREMENT_UNKNOWN'
        if not any(t.is_alive() for t in threads):child.stdout.close();child.stderr.close()
    receipt=dict(returncode=child.returncode,reason=reason,observed_output_bytes=total,output_limit=budget,elapsed_seconds=time.monotonic()-started,direct_handle_retired=child.poll() is not None,reader_threads_retired=not any(t.is_alive() for t in threads),reader_errors=reader_errors,scope='LOCAL_MOCK_UNIT_ONLY_NOT_HOSTILE_FAMILY_SANDBOX',native=False,physical=False,public_submit=False)
    with (ROOT/'OUTER-RESULT.json').open('x',encoding='utf8') as f:json.dump(receipt,f,indent=2)
    return 0 if child.returncode==0 and not reason else 1
if __name__=='__main__':raise SystemExit(main())
