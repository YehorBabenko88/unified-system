"""REVIEW ONLY. No execution before separate Root allocation."""
import sys,os,json,hashlib,stat,runpy,importlib.machinery,threading,unittest,re
from pathlib import Path
ROOT=Path(__file__).parent
CAPSULE_SHA='8a3b58ea8464d3488aff36c100f60929ed3190a5c04263bd602a3136b2e77f78'

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
    if not (sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
            and sys.pycache_prefix):raise RuntimeError('FLAGS_REQUIRED')
    raw=bounded_read(ROOT/'CAPSULE.json',8*1024**2)
    if hashlib.sha256(raw).hexdigest()!=CAPSULE_SHA:raise RuntimeError('CAPSULE_PIN')
    c=json.loads(raw,object_pairs_hook=closed_pairs)
    cache=Path(c['cache']);ordinary(cache,directory=True)
    if Path(sys.pycache_prefix)!=cache or list(cache.iterdir()):raise RuntimeError('NEW_EMPTY_CACHE_REQUIRED')
    if sys.version_info[:3]!=(3,12,10) or Path(sys.executable)!=Path(c['python']):raise RuntimeError('FIXED_PYTHON_REQUIRED')
    source=c['sources'][0];source_root=Path(source['root'])
    admitted={str(Path(p)):v for p,v in c['runtime'].items()}
    admitted.update({str(source_root/p):v for p,v in source['files'].items()})
    project_modules={str(source_root/p) for p in c['project_import_closure']}
    factory_path=source_root/'tests/storage/native_publication/review5_recovery_controls.py'
    def all_raw():
        for p,v in admitted.items():checked(Path(p),v)
        exact_tree(source_root,source['files'],git_metadata=True)
        exact_tree(Path(c['deps_root']),{})
        return dict(source['files'])
    before=all_raw();loaded=[];special=[]
    def origin(name,location):
        if location in ('built-in','frozen',None):
            special.append(dict(name=name,origin=location));return
        p=Path(location)
        if str(p) not in admitted:raise RuntimeError('UNADMITTED_MODULE_ORIGIN')
        if p.is_relative_to(source_root) and str(p) not in project_modules:
            raise RuntimeError('UNADMITTED_PROJECT_MODULE')
        checked(p,admitted[str(p)])
        loaded.append(dict(name=name,path=str(p),sha256=admitted[str(p)]['sha256']))
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
    sys.meta_path=[m for m in sys.meta_path if m is not importlib.machinery.PathFinder]
    sys.meta_path.append(Finder())
    runtime_root=Path(c['python']).parent
    sys.path[:]=[str(source_root),str(runtime_root/'Lib'),str(runtime_root/'DLLs')]
    effects={};baseline={id(t) for t in threading.enumerate()}
    def audit(event,args):
        if (event.startswith(('subprocess.','socket.','os.exec','os.spawn'))
                or event in ('os.system','os.fork','os.forkpty','ctypes.dlopen','ctypes.dlsym')
                or event.startswith('sqlite3.connect')):
            raise RuntimeError('FORBIDDEN_EFFECT_'+event)
        if event=='open':
            path,mode,flags=args
            writing=(type(mode) is str and any(ch in mode for ch in 'wax+')) or (
                type(flags) is int and bool(flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)))
            if writing and not (type(path) is str and Path(path)==ROOT/'ACTUAL-RESULT.json'):
                raise RuntimeError('WRITE_OUTSIDE_EXCLUSIVE_RECEIPT')
        if event=='import' and len(args)>1 and type(args[1]) is str and args[1].endswith('.pyd'):
            origin(args[0],args[1]);effects['extension_import']=effects.get('extension_import',0)+1
    sys.addaudithook(audit)
    journal_file=str(source_root/'unified_system/journal.py')
    store_file=str(source_root/'unified_system/storage/object_store.py')
    recovery_file=str(source_root/'unified_system/storage/publication_recovery.py')
    def prohibit_calls(frame,event,arg):
        if event=='call':
            code=frame.f_code
            if ((code.co_filename==journal_file and code.co_name not in ('<module>','Journal'))
                    or (code.co_filename==store_file and code.co_name not in ('<module>','ObjectStore','LocalObject'))
                    or (code.co_filename==recovery_file and code.co_qualname.startswith('PendingPublicationJournal.'))):
                raise RuntimeError('JOURNAL_OR_OBJECTSTORE_CALL_FORBIDDEN')
    sys.setprofile(prohibit_calls)
    state='PREREQUISITE_PENDING';failure=None;result=None;actual_ids=[];boundary=[];after=None
    try:
        # Actual qualified modules/classes only; never inject a helper substitute.
        import unified_system.storage.publication_recovery as recovery
        import unified_system.storage.publication_records as records
        import unified_system.storage.contracts as contracts
        controls=runpy.run_path(str(factory_path),run_name='a4_review5_recovery_controls')
        prepare=getattr(recovery,'prepare_local_review5_recovery_candidate',None)
        if prepare is None:
            state='NEW_FEATURE_PREREQUISITE_ABSENT_NOT_SIX_TEST_FAILURES'
        else:
            if (type(prepare).__name__!='function' or prepare.__module__!=recovery.__name__
                    or Path(prepare.__code__.co_filename)!=Path(recovery.__file__)):
                raise RuntimeError('ACTUAL_HELPER_ORIGIN_REQUIRED')
            suite=controls['make_suite'](prepare,records.RetainedPublicationIntent,contracts.StorageBlocked)
            def ids(s):
                for t in s:
                    if isinstance(t,unittest.TestSuite):yield from ids(t)
                    else:yield t.id()
            actual_ids=list(ids(suite))
            if sorted(actual_ids)!=sorted(c['expected_ids']) or len(set(actual_ids))!=6:
                raise RuntimeError('EXACT_SIX_FACTORY_IDS')
            result=unittest.TextTestRunner(verbosity=2).run(suite)
            state='PURE_LOCAL_PASS' if result.wasSuccessful() and not result.skipped else 'PURE_LOCAL_RED'
    except BaseException as exc:
        failure=type(exc).__name__;state='BOUNDARY_OR_PREREQUISITE_FAILURE_NOT_PRODUCT_RED'
    finally:
        sys.setprofile(None)
        try:
            for name,m in tuple(sys.modules.items()):
                if name=='__main__':continue
                spec=getattr(m,'__spec__',None)
                if spec:origin(name,spec.origin)
            checked(factory_path,source['files']['tests/storage/native_publication/review5_recovery_controls.py'])
            after=all_raw()
            if before!=after:raise RuntimeError('SOURCE_CHANGED')
        except BaseException as exc:boundary.append(type(exc).__name__)
        cleanup=dict(new_live_threads=None,cache_empty=None)
        try:
            cleanup['new_live_threads']=sum(id(t) not in baseline for t in threading.enumerate())
            ordinary(cache,directory=True)
            cleanup['cache_empty']=not any(cache.iterdir())
        except BaseException as exc:
            boundary.append(dict(stage='final_cache_observation',type=type(exc).__name__))
        if boundary or cleanup['new_live_threads'] or not cleanup['cache_empty']:
            state='BOUNDARY_FAILURE_NOT_PRODUCT_RED'
        receipt=dict(state=state,exception_type=failure,head=source['head'],tree=source['tree'],
            tests_run=result.testsRun if result else 0,failures=len(result.failures) if result else 0,
            errors=len(result.errors) if result else 0,skips=len(result.skipped) if result else 0,
            actual_ids=actual_ids,expected_ids=c['expected_ids'],source_before=before,source_after=after,
            loaded_origins=loaded,builtin_frozen=special,boundary_errors=boundary,cleanup=cleanup,effects=effects,
            native=False,provider=False,physical=False,publication_confirmed=False,
            scope='PURE_LOCAL_RECOVERY_PREREQUISITE_NOT_NATIVE_OR_FIXTURE_ACCEPTANCE')
        with (ROOT/'ACTUAL-RESULT.json').open('x',encoding='utf8') as f:json.dump(receipt,f,indent=2,sort_keys=True)
    return 0 if state=='PURE_LOCAL_PASS' else 1

if __name__=='__main__':raise SystemExit(main())
