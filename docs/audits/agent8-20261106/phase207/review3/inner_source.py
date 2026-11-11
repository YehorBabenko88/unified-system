"""REVIEW ONLY. Actual10 execution requires separate Root allocation."""
import sys,os,json,hashlib,stat,runpy,importlib.machinery,threading,asyncio,unittest,re
from pathlib import Path
ROOT=Path(__file__).parent
CAPSULE_SHA='b0b56441f797babc16d268b0015bd860a29a82f5e47e8fc789e324e586d1da55'

def ordinary(p,directory=False):
    for n in [*reversed(p.parents),p]:
        s=n.lstat()
        if stat.S_ISLNK(s.st_mode) or getattr(s,'st_reparse_tag',0) or getattr(s,'st_file_attributes',0)&1024:raise RuntimeError('LINK_OR_REPARSE')
        if n!=p or directory:
            if not stat.S_ISDIR(s.st_mode):raise RuntimeError('ANCESTOR_NOT_DIRECTORY')
        elif not stat.S_ISREG(s.st_mode) or s.st_nlink!=1:raise RuntimeError('NOT_SINGLE_REGULAR')
    return s
def bounded_read(p,limit):
    before=ordinary(p)
    if before.st_size>limit:raise RuntimeError('INPUT_LIMIT')
    with p.open('rb') as f:
        opened=os.fstat(f.fileno())
        if (opened.st_dev,opened.st_ino)!=(before.st_dev,before.st_ino):raise RuntimeError('INPUT_IDENTITY')
        data=f.read(limit+1);after=os.fstat(f.fileno())
    final=ordinary(p)
    if len(data)!=before.st_size or len(data)>limit or any((v.st_dev,v.st_ino,v.st_size,v.st_mtime_ns)!=(before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns) for v in (after,final)):raise RuntimeError('INPUT_CHANGED')
    return data
def closed_pairs(items):
    result={}
    for k,v in items:
        if k in result:raise RuntimeError('DUPLICATE_JSON')
        result[k]=v
    return result
def exact_tree(root,files,git_metadata=False):
    ordinary(root,directory=True)
    expected_dirs=set()
    for name in files:
        p=Path(name)
        expected_dirs.update(parent.as_posix() for parent in p.parents if parent!=Path('.'))
    seen_files=set();seen_dirs=set()
    pending=[root]
    while pending:
        current=pending.pop();ordinary(current,directory=True)
        # scandir is used only for names, never entry.is_dir/is_file, which may
        # follow an unknown link before the explicit lstat rejection.
        with os.scandir(current) as entries:
            for entry in entries:
                p=current/entry.name;s=p.lstat()
                if stat.S_ISLNK(s.st_mode) or getattr(s,'st_reparse_tag',0) or getattr(s,'st_file_attributes',0)&1024:raise RuntimeError('LINK_OR_REPARSE')
                rel=p.relative_to(root).as_posix()
                if stat.S_ISDIR(s.st_mode):
                    ordinary(p,directory=True)
                    if git_metadata and current==root and entry.name=='.git':continue
                    if rel not in expected_dirs:raise RuntimeError('EXTRA_DIRECTORY')
                    seen_dirs.add(rel);pending.append(p)
                else:
                    ordinary(p)
                    if rel not in files:raise RuntimeError('EXTRA_FILE')
                    seen_files.add(rel)
    if seen_files!=set(files) or seen_dirs!=expected_dirs:raise RuntimeError('EXACT_TREE_REQUIRED')
def checked(p,expected):
    before=ordinary(p)
    if before.st_size!=expected['bytes']:raise RuntimeError('RAW_SIZE')
    with p.open('rb') as f:
        h=hashlib.sha256()
        for b in iter(lambda:f.read(65536),b''):h.update(b)
        after=os.fstat(f.fileno())
    final=ordinary(p)
    if h.hexdigest()!=expected['sha256'] or any((s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)!=(before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns) for s in (after,final)):raise RuntimeError('RAW_CHANGED')
def main():
    if not(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode and sys.pycache_prefix):raise RuntimeError('FLAGS_REQUIRED')
    ordinary(ROOT,directory=True)
    raw=bounded_read(ROOT/'CAPSULE.json',8*1024**2)
    if hashlib.sha256(raw).hexdigest()!=CAPSULE_SHA:raise RuntimeError('CAPSULE_PIN')
    c=json.loads(raw,object_pairs_hook=closed_pairs);cache=Path(c['cache'])
    ordinary(cache,directory=True)
    if Path(sys.pycache_prefix)!=cache or list(cache.iterdir()):raise RuntimeError('NEW_EMPTY_CACHE_REQUIRED')
    admitted={str(Path(p)):v for p,v in c['runtime'].items()}
    for source in c['sources']:
        admitted.update({str(Path(source['root'])/p):v for p,v in source['files'].items()})
    admitted.update({str(Path(c['deps_root'])/p):v for p,v in c['deps'].items()})
    def all_raw():
        for p,v in admitted.items():checked(Path(p),v)
        for source in c['sources']:
            exact_tree(Path(source['root']),source['files'],git_metadata=True)
        exact_tree(Path(c['deps_root']),c['deps'])
    all_raw()
    loaded=[];special=[]
    def origin(name,location):
        if location in ('built-in','frozen',None):special.append(dict(name=name,origin=location));return
        p=Path(location)
        if str(p) not in admitted:raise RuntimeError('UNADMITTED_MODULE_ORIGIN')
        checked(p,admitted[str(p)]);loaded.append(dict(name=name,path=str(p),sha256=admitted[str(p)]['sha256']))
    # Validate already loaded stdlib separately; __main__ is the reviewed driver.
    for name,m in tuple(sys.modules.items()):
        if name=='__main__':continue
        spec=getattr(m,'__spec__',None)
        if spec:origin(name,spec.origin)
    class Loader:
        def __init__(self,name,spec):self.name=name;self.spec=spec;self.delegate=spec.loader
        def create_module(self,spec):
            origin(self.name,self.spec.origin)
            return self.delegate.create_module(spec) if hasattr(self.delegate,'create_module') else None
        def exec_module(self,module):origin(self.name,self.spec.origin);return self.delegate.exec_module(module)
        def get_code(self,name):origin(self.name,self.spec.origin);return self.delegate.get_code(name)
        def get_source(self,name):origin(self.name,self.spec.origin);return self.delegate.get_source(name)
        def __getattr__(self,name):return getattr(self.delegate,name)
    class Finder:
        def find_spec(self,name,path=None,target=None):
            spec=importlib.machinery.PathFinder.find_spec(name,path,target)
            if spec:
                if spec.loader is None:raise RuntimeError('UNADMITTED_NAMESPACE_PACKAGE')
                origin(name,spec.origin);spec.loader=Loader(name,spec)
            return spec
    # Builtin/Frozen finders retain their standard order; all filesystem loaders use our gate.
    sys.meta_path=[m for m in sys.meta_path if m is not importlib.machinery.PathFinder]
    sys.meta_path.append(Finder())
    stdpaths=[p for p in sys.path if p and Path(p).is_absolute() and (Path(p)==Path(c['python']).parent/'Lib' or Path(p)==Path(c['python']).parent/'DLLs' or str(p).lower().endswith('python312.zip'))]
    sys.path[:]=[c['sources'][0]['root'],c['sources'][1]['root'],c['deps_root'],*stdpaths]
    effects={};owned_sockets=[]
    socketfile=str(Path(c['python']).parent/'Lib/socket.py')
    def selfpipe(event,args):
        frame=sys._getframe(2);fallback=None;pipe=False
        while frame:
            if frame.f_code.co_filename==socketfile and frame.f_code.co_name=='_fallback_socketpair':fallback=frame
            if frame.f_code.co_name=='_make_self_pipe' and frame.f_code.co_filename in admitted and '/asyncio/' in frame.f_code.co_filename.replace('\\','/'):pipe=True
            frame=frame.f_back
        if not (fallback and pipe):return False
        sock,address=args
        if event=='socket.bind':return sock is fallback.f_locals.get('lsock') and address in (('127.0.0.1',0),('::1',0))
        return sock is fallback.f_locals.get('csock') and address==(fallback.f_locals.get('addr'),fallback.f_locals.get('port')) and address[0] in ('127.0.0.1','::1') and type(address[1]) is int and 0<address[1]<65536
    def audit(event,args):
        if event in ('subprocess.Popen','os.system','os.posix_spawn','os.posix_spawnp','os.fork','os.forkpty','os.exec','os.spawn','ctypes.dlopen','ctypes.dlsym') or event.startswith('os.exec') or event.startswith('os.spawn'):raise RuntimeError('CHILD_OR_DYNAMIC_LOADER_FORBIDDEN')
        if event.startswith(('socket.getaddrinfo','socket.gethostby','socket.getnameinfo')):raise RuntimeError('DNS_FORBIDDEN')
        if event in ('socket.connect','socket.bind'):
            if not selfpipe(event,args):raise RuntimeError('ONLY_OWNED_ASYNCIO_SELFPIPE_PERMITTED')
            owned_sockets.append(args[0]);effects[event]=effects.get(event,0)+1
    sys.addaudithook(audit)
    loops=[];new_loop=asyncio.events.new_event_loop
    def observed_loop():
        loop=new_loop();loops.append(loop);return loop
    asyncio.events.new_event_loop=observed_loop
    baseline={id(t) for t in threading.enumerate()};test_records=[];captured=[]
    class Result(unittest.TextTestResult):
        def startTest(self,test):test_records.append(test.id());super().startTest(test)
    runner=unittest.TextTestRunner
    class RecordedRunner(runner):
        resultclass=Result
        def run(self,suite):
            result=super().run(suite);captured.append(result);return result
    unittest.TextTestRunner=RecordedRunner
    code=None;failure=None;boundary_errors=[]
    test=Path(c['sources'][0]['root'])/'tests/test_research_identity_atomic_snapshot_unit.py'
    try:
        sys.argv=[str(test)]
        try:runpy.run_path(str(test),run_name='__main__')
        except SystemExit as exc:code=exc.code
    except BaseException as exc:failure=type(exc).__name__
    finally:
        unittest.TextTestRunner=runner;asyncio.events.new_event_loop=new_loop
        try:
            for name,m in tuple(sys.modules.items()):
                if name=='__main__':continue
                spec=getattr(m,'__spec__',None)
                if spec:origin(name,spec.origin)
        except BaseException as exc:
            boundary_errors.append(dict(stage='post_origin',type=type(exc).__name__))
            print('INNER_POST_ORIGIN_BOUNDARY_FAILURE',file=sys.stderr)
        try:all_raw()
        except BaseException as exc:
            boundary_errors.append(dict(stage='post_raw',type=type(exc).__name__))
            print('INNER_POST_RAW_BOUNDARY_FAILURE',file=sys.stderr)
        try:
            checked(test,admitted[str(test)])
            expected=re.findall(r"^    '(test_mock_backend_[a-z_]+)',$",bounded_read(test,128*1024).decode('utf8'),re.M)
        except BaseException as exc:
            expected=[];boundary_errors.append(dict(stage='post_test_inventory',type=type(exc).__name__))
            print('INNER_POST_INVENTORY_BOUNDARY_FAILURE',file=sys.stderr)
        ids=['__main__.ControlledBackendBrokerUnitTests.'+n for n in expected]
        try:
            ordinary(cache,directory=True)
            cleanup=dict(loops_created=len(loops),all_loops_closed=all(l.is_closed() for l in loops),all_tasks_done=all(all(t.done() for t in asyncio.all_tasks(l)) for l in loops),new_live_threads=sum(id(t) not in baseline for t in threading.enumerate()),selfpipe_sockets_closed=all(s.fileno()==-1 for s in owned_sockets),cache_empty=not any(cache.iterdir()))
        except BaseException as exc:
            cleanup=dict(loops_created=len(loops),all_loops_closed=False,all_tasks_done=False,new_live_threads=None,selfpipe_sockets_closed=False,cache_empty=False)
            boundary_errors.append(dict(stage='cleanup_observation',type=type(exc).__name__))
            print('INNER_CLEANUP_OBSERVATION_UNKNOWN',file=sys.stderr)
        r=captured[0] if len(captured)==1 else None
        inventory_ok=len(ids)==10 and len(set(test_records))==10 and len(test_records)==10 and set(ids)==set(test_records)
        passed=code==0 and failure is None and not boundary_errors and r is not None and r.wasSuccessful() and not r.skipped and inventory_ok and all(cleanup[k] for k in ('all_loops_closed','all_tasks_done','selfpipe_sockets_closed','cache_empty')) and cleanup['new_live_threads']==0
        result=dict(state='LOCAL_MOCK_UNIT_PASS' if passed else 'LOCAL_MOCK_UNIT_RED_OR_BOUNDARY_FAILURE',exit_code=code,exception_type=failure,tests_run=r.testsRun if r else None,failures=[t.id() for t,_ in r.failures] if r else [],errors=[t.id() for t,_ in r.errors] if r else [],skips=len(r.skipped) if r else None,actual_ids=test_records,exact_inventory=inventory_ok,cleanup=cleanup,effects=effects,loaded_origins=loaded,builtin_frozen=special,source_prepost='ALL_ADMITTED_RAW_CHECKED',flags=dict(native=False,physical=False,provider=False,deployment=False,public_submit=False),limits=['Local mock only; model backend and peer','Not hostile process-family containment','No transitive DLL publisher/signature closure','Raw origin identity is not proof source bytes executed'])
        result['boundary_errors']=boundary_errors
        if boundary_errors or failure is not None:
            result['state']='BOUNDARY_FAILURE_NOT_PRODUCT_RED';result['source_prepost']='FAILED_OR_UNKNOWN'
        try:
            with (ROOT/'ACTUAL-RESULT.json').open('x',encoding='utf8') as f:json.dump(result,f,indent=2,sort_keys=True)
        except BaseException:
            print('INNER_RECEIPT_WRITE_FAILED',file=sys.stderr)
            raise
    return 0 if passed else 1
if __name__=='__main__':raise SystemExit(main())
