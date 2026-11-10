"""REVIEW ONLY: do not launch before separate Root allocation."""
import hashlib,json,os,stat,subprocess,threading,time
from pathlib import Path
ROOT=Path(__file__).parent
SEAL_SHA='de1a12aa4f0402e29abef4c593564b187dd5087cdeb04628f88deed6224d8159'
def ordinary(path,directory=False):
    for n in [*reversed(path.parents),path]:
        s=n.lstat()
        if stat.S_ISLNK(s.st_mode) or getattr(s,'st_reparse_tag',0) or getattr(s,'st_file_attributes',0)&1024:raise RuntimeError('LINK_OR_REPARSE')
        if n!=path or directory:
            if not stat.S_ISDIR(s.st_mode):raise RuntimeError('DIRECTORY_REQUIRED')
        elif not stat.S_ISREG(s.st_mode) or s.st_nlink!=1:raise RuntimeError('SINGLE_REGULAR_REQUIRED')
    return s
def bounded_read(path,limit):
    before=ordinary(path)
    if before.st_size>limit:raise RuntimeError('INPUT_LIMIT')
    with path.open('rb') as f:
        opened=os.fstat(f.fileno())
        if (opened.st_dev,opened.st_ino)!=(before.st_dev,before.st_ino):raise RuntimeError('INPUT_IDENTITY')
        data=f.read(limit+1);after=os.fstat(f.fileno())
    final=ordinary(path)
    if len(data)!=before.st_size or len(data)>limit or any((v.st_dev,v.st_ino,v.st_size,v.st_mtime_ns)!=(before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns) for v in (after,final)):raise RuntimeError('INPUT_CHANGED')
    return data
def closed_pairs(items):
    result={}
    for k,v in items:
        if k in result:raise RuntimeError('DUPLICATE_JSON')
        result[k]=v
    return result
def checked_file(path,expected):
    s=ordinary(path)
    if not stat.S_ISREG(s.st_mode) or s.st_nlink!=1 or s.st_size!=expected['bytes']:raise RuntimeError('FILE_METADATA')
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(65536),b''):h.update(b)
        after=os.fstat(f.fileno())
    final=ordinary(path)
    if h.hexdigest()!=expected['sha256'] or any((v.st_dev,v.st_ino,v.st_size,v.st_mtime_ns)!=(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns) for v in (after,final)):raise RuntimeError('FILE_CHANGED')
def main():
    ordinary(ROOT,directory=True)
    sealraw=bounded_read(ROOT/'DRIVER-SEAL.json',4096)
    if hashlib.sha256(sealraw).hexdigest()!=SEAL_SHA:raise RuntimeError('SEAL_PIN')
    seal=json.loads(sealraw,object_pairs_hook=closed_pairs)
    if type(seal) is not dict or set(seal)!={'CAPSULE.json','inner_source.py'}:raise RuntimeError('CLOSED_SEAL_NAMES')
    inputs={}
    for n,expected in seal.items():
        if type(expected) is not str or len(expected)!=64 or any(ch not in '0123456789abcdef' for ch in expected):raise RuntimeError('SEAL_HASH')
        b=bounded_read(ROOT/n,8*1024**2 if n=='CAPSULE.json' else 128*1024)
        if hashlib.sha256(b).hexdigest()!=expected:raise RuntimeError('DRIVER_PIN')
        inputs[n]=b
    capsule=json.loads(inputs['CAPSULE.json'],object_pairs_hook=closed_pairs);cache=Path(capsule['cache'])
    ordinary(cache,directory=True)
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
    held=None;threads=[];reason=None;lifecycle_errors=[];direct_retired=False;returncode=None
    def problem(stage,exc):lifecycle_errors.append(dict(stage=stage,type=type(exc).__name__))
    def alive(t):
        try:return t.is_alive()
        except BaseException as exc:problem('reader_alive',exc);return True
    def retire():
        nonlocal direct_retired,returncode
        if held is None:return
        # Never infer retirement after an unexpected poll error. Attempt kill on
        # the already held handle, then bounded wait, without rediscovering PID.
        try:
            if held.poll() is None:held.kill()
        except BaseException as exc:
            problem('cleanup_poll_or_kill',exc)
            try:held.kill()
            except BaseException as kill_error:problem('cleanup_kill',kill_error)
        try:returncode=held.wait(timeout=5);direct_retired=True
        except BaseException as exc:problem('cleanup_wait',exc)
        for t in threads:
            try:
                if t.ident is not None:t.join(timeout=1)
            except BaseException as exc:problem('cleanup_join',exc)
        if not any(alive(t) for t in threads):
            for pipe in (held.stdout,held.stderr):
                try:pipe.close()
                except BaseException as exc:problem('cleanup_pipe_close',exc)
    with (ROOT/'stdout.original.bin').open('xb') as out,(ROOT/'stderr.original.bin').open('xb') as err:
        try:
            # The first action after successful construction is retaining the
            # owned handle. Every subsequent operation is covered by finally.
            held=subprocess.Popen(cmd,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,close_fds=True)
            started=time.monotonic()
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
            for pipe,destination in ((held.stdout,out),(held.stderr,err)):
                t=threading.Thread(target=drain,args=(pipe,destination),daemon=True)
                threads.append(t);t.start()
            while held.poll() is None:
                if exceeded.wait(.02):reason='OUTPUT_OR_READER_BOUNDARY';break
                if time.monotonic()-started>=90:reason='CHILD_90S_TIMEOUT';break
        except BaseException as exc:
            reason='OUTER_LIFECYCLE_FAILURE';problem('post_creation_or_spawn',exc)
        finally:
            try:retire()
            except BaseException as exc:problem('retirement_unexpected',exc)
            readers_retired=not any(alive(t) for t in threads)
            # Sticky finalization check: a child can exit before polling sees
            # an overflow that the draining readers observe after its exit.
            if exceeded.is_set() or total>budget:reason='OUTPUT_OR_READER_BOUNDARY'
            if not direct_retired or not readers_retired:reason=reason or 'RETIREMENT_UNKNOWN'
            if lifecycle_errors or reader_errors:reason=reason or 'OUTER_BOUNDARY_FAILURE'
            receipt=dict(state='FAILED_OR_UNKNOWN' if reason else 'CHILD_RETIRED',child_created=held is not None,returncode=returncode,reason=reason,observed_output_bytes=total,output_limit=budget,elapsed_seconds=time.monotonic()-started,direct_handle_retired=direct_retired,reader_threads_retired=readers_retired,reader_errors=reader_errors,lifecycle_errors=lifecycle_errors,scope='LOCAL_MOCK_UNIT_ONLY_NOT_HOSTILE_FAMILY_SANDBOX',budget='90s child lifetime plus bounded 5s retirement and 1s per reader join; not strict whole-lane 90s',native=False,physical=False,public_submit=False)
            try:
                with (ROOT/'OUTER-RESULT.json').open('x',encoding='utf8') as f:json.dump(receipt,f,indent=2)
            except BaseException as exc:
                # Best effort only: uninterruptible/failed output cannot be
                # converted into a fabricated durable cleanup receipt.
                problem('receipt_write',exc);reason='RECEIPT_WRITE_FAILED'
                print('OUTER_RECEIPT_WRITE_FAILED',file=__import__('sys').stderr)
    return 0 if returncode==0 and not reason else 1
if __name__=='__main__':raise SystemExit(main())
