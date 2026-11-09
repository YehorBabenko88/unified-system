"""Fixed synthetic backend bootstrap. No target/child/network before bounded GO."""
import json,os,queue,re,sys,threading
from pathlib import Path

def allocate_stand_root(root):
    root=Path(root)
    if not root.is_absolute() or root!=root.resolve(strict=True):raise RuntimeError('OWN_CANONICAL_STATE_REQUIRED')
    state=root/'direct-state';state.mkdir()  # Existing stand expects caller-owned empty directory.
    return state

def source_git_argv(argv,git,roots):
    if not(isinstance(argv,(list,tuple)) and len(argv)==6 and argv[0]=='git'
            and list(argv[1:3])==['--no-replace-objects','-C'] and argv[4]=='show'
            and Path(argv[3]).resolve() in {path.resolve() for path in roots}
            and isinstance(argv[5],str) and re.fullmatch('[0-9a-f]{40}:[A-Za-z0-9_./-]{1,256}',argv[5])):
        raise RuntimeError('NON_SOURCE_GIT_CHILD_DENIED')
    return [str(git),*argv[1:]]

def validate_source_git_audit(executable,argv,git,selected,platform):
    # Windows CPython emits a canonical commandline STRING after list2cmdline;
    # POSIX emits a vector. Never parse/reinterpret a caller-provided string.
    import subprocess
    if not(isinstance(selected,(list,tuple)) and len(selected)==6 and str(executable)==str(git) and selected[0]==str(git)):
        raise RuntimeError('NON_SOURCE_GIT_CHILD_DENIED')
    if platform=='nt':valid=type(argv) is str and argv==subprocess.list2cmdline(selected)
    elif platform=='posix':valid=isinstance(argv,(list,tuple)) and list(argv)==list(selected)
    else:valid=False
    if not valid:raise RuntimeError('NON_SOURCE_GIT_CHILD_DENIED')

def validate_state_path(value,root):
    if isinstance(value,int):return
    text=os.fsdecode(value)
    if text.startswith('file:'):
        from urllib.parse import urlsplit,unquote
        uri=urlsplit(text)
        if uri.scheme!='file' or uri.netloc or uri.fragment or uri.query!='mode=ro':raise RuntimeError('SQLITE_URI_SCOPE')
        decoded=unquote(uri.path)
        if os.name=='nt' and len(decoded)>2 and decoded[0]=='/' and decoded[2]==':':decoded=decoded[1:]
        path=Path(decoded)
        if path.as_uri()+'?mode=ro'!=text:raise RuntimeError('SQLITE_URI_CANONICAL')
    else:path=Path(text)
    if '..' in path.parts:raise RuntimeError('STATE_PATH_ALIAS')
    if os.name=='nt' and ':' in str(path)[2:]:raise RuntimeError('STATE_STREAM_DENIED')
    resolved=path.resolve()
    if resolved!=root and not resolved.is_relative_to(root):raise RuntimeError('WRITE_OUTSIDE_OWN_STATE')

def main():
    if not(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):raise RuntimeError('SITE_FREE_BOOTSTRAP_REQUIRED')
    if len(sys.argv)!=6:raise RuntimeError('BOOTSTRAP_ARGUMENTS')
    nonce,package_raw,run_raw,git_raw,role=sys.argv[1:]
    if re.fullmatch('[0-9a-f]{32}',nonce) is None or role!='SYNTHETIC_DIRECT_ONLY':raise RuntimeError('BOOTSTRAP_ARGUMENTS')
    # Only stdlib startup and bounded own stdin precede the parent-owned GO.
    print(json.dumps(dict(pid=os.getpid(),nonce=nonce),separators=(',',':')),flush=True)
    received=queue.Queue(maxsize=1)
    def reader():
        try:received.put(sys.stdin.buffer.readline(1025))
        except BaseException:received.put(b'')
    threading.Thread(target=reader,daemon=True).start()
    try:frame=received.get(timeout=5)
    except queue.Empty:raise RuntimeError('BOOTSTRAP_GO_TIMEOUT') from None
    if frame!=('GO '+nonce+'\n').encode('ascii'):raise RuntimeError('BOOTSTRAP_GO_REFUSED')
    package=Path(package_raw).resolve(strict=True);root=Path(run_raw).resolve(strict=True);git=Path(git_raw).resolve(strict=True)
    if package==root or root.is_relative_to(package):raise RuntimeError('STATE_INSIDE_PACKAGE')
    unified=package/'sources/runtime-unified';stratt=package/'sources/strattester';meta=package/'sources/meta_analyse'
    sys.path.insert(0,str(unified))
    def own_write(value):
        validate_state_path(value,root)
    pending_git=threading.local()
    def audit(event,args):
        if event.startswith('socket.'):raise RuntimeError('BACKEND_NETWORK_DENIED')
        if event=='open':
            path,mode,flags=args
            if (isinstance(mode,str) and any(x in mode for x in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)):own_write(path)
        elif event=='sqlite3.connect':own_write(args[0])
        elif event in ('os.mkdir','os.remove','os.rmdir','os.chmod','os.utime'):own_write(args[0])
        elif event in ('os.rename','os.replace'):
            own_write(args[0]);own_write(args[1])
        elif event=='subprocess.Popen':
            executable,argv,_,_=args
            try:validate_source_git_audit(executable,argv,git,getattr(pending_git,'argv',None),os.name)
            except RuntimeError:
                print('SOURCE_GIT_AUDIT_DENIED',file=sys.stderr,flush=True);raise
    # The caller selected and verified this source Git executable before GO.
    os.environ['PATH']=str(git.parent)+os.pathsep+os.environ.get('PATH','')
    # Select the exact admitted executable for the existing adapter's unchanged
    # ['git', ...] source reads. No target algorithm, request or source is patched.
    import subprocess
    native_popen=subprocess.Popen
    def pinned_source_popen(argv,*args,**kwargs):
        if args or 'executable' in kwargs or kwargs.get('shell',False):raise RuntimeError('SOURCE_GIT_OPTIONS')
        selected=source_git_argv(argv,git,{stratt,meta})
        if getattr(pending_git,'argv',None) is not None:raise RuntimeError('NESTED_SOURCE_GIT_DENIED')
        pending_git.argv=tuple(selected)
        try:return native_popen(selected,executable=str(git),**kwargs)
        finally:pending_git.argv=None
    subprocess.Popen=pinned_source_popen
    sys.addaudithook(audit)
    from unified_system.gateway_target_adapter import DisposableTargetStand,prepare_target,template_request
    request=json.dumps(template_request(),sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')
    state=allocate_stand_root(root)
    stand=DisposableTargetStand(str(state),stratt_source_root=str(stratt),meta_source_root=str(meta))
    try:
        value=stand.execute(prepare_target(request),context=stand.local_test_context())
        if value['status']!='DIRECT_TARGET_PASS' or stand.invocations!=1:
            print('DIRECT_TARGET_COMPLETION_UNAVAILABLE',file=sys.stderr,flush=True)
            raise RuntimeError('ACTUAL_DIRECT_TARGET_NOT_COMPLETED')
        envelope=json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')
        artifact=json.dumps(value['result'],sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')
        import hashlib
        if len(artifact)!=2070 or hashlib.sha256(artifact).hexdigest()!='f4997d7d26211676cd8664e53d7999f8b71f203510f3b9a275b439c403e03940':raise RuntimeError('ACTUAL_ARTIFACT_DIGEST')
        for name,raw in [('fresh-request.json',request),('fresh-envelope.json',envelope),('fresh-artifact.json',artifact)]:
            if not 0<len(raw)<=16384:raise RuntimeError('OUTPUT_BOUND')
            with (root/name).open('xb') as stream:stream.write(raw)
        print(json.dumps(dict(status='DIRECT_TARGET_PASS',artifact_sha256=hashlib.sha256(artifact).hexdigest(),publication='LOCAL_UNATTESTED',native_admission=False),separators=(',',':')),flush=True)
    finally:stand.close()

if __name__=='__main__':
    try:main()
    except BaseException as error:
        known={'DISPOSABLE_STAND_UNAVAILABLE','LOCAL_TEST_SCOPE_DENIED','TARGET_CONTRACT_REJECTED','TARGET_SOURCE_UNAVAILABLE','TARGET_INPUT_UNAVAILABLE','TARGET_DATASET_UNAVAILABLE'}
        code=str(error) if str(error) in known else 'DETAILS_WITHHELD'
        print('SYNTHETIC_BOOTSTRAP_FAILED:'+type(error).__name__+':'+code,file=sys.stderr,flush=True);raise SystemExit(71)
