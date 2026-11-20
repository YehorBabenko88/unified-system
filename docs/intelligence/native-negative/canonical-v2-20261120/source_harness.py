"""Root-only exact-source native harness. Importing this module performs no effects.

The pure guard group uses refusing crypto import shapes, never PKI success.
Only the separate mandatory native21/22 groups establish disposable native proof.
"""
import argparse,ast,functools,hashlib,json,os,platform,re,stat,subprocess,sys,unittest
from pathlib import Path
MANIFEST_SCHEMA='unified.native-negative.root-owned-source.v2'
BASE='3af06455b601a328e94339327a0597eada802c38'
HELPER='tests/storage/native_publication/qualify.py'
HELPER_SHA='e71934d06625a5b1c2047cd32c23c4005f2c400b438717b6b3394ecb7855edee'
OWNER_MODULES=["unified_system/consul_authority.py","unified_system/authority_codec.py","unified_system/research_authority.py","unified_system/gateway_research_identity.py","unified_system/gateway_native_negative.py","unified_system/gateway_identity.py"]
_OUT=None

def validate_ids(actual,expected):
    if (type(expected) is not list or not 0<len(expected)<=256 or
        any(type(x) is not str or re.fullmatch(r'[A-Za-z_]\w*\.[A-Za-z_]\w*\.test_\w+',x) is None for x in expected) or
        len(expected)!=len(set(expected)) or len(actual)!=len(set(actual)) or sorted(actual)!=sorted(expected)):
        raise ValueError('EXACT_UNIQUE_CASE_IDS_REQUIRED')
    return sorted(actual)

def validate_manifest(manifest,bindings):
    if manifest.get('schema')!=MANIFEST_SCHEMA or manifest.get('public_submit')!='DENY':raise ValueError('MANIFEST_SCOPE')
    for name in ('public_http_endpoint','full_scientific_e2e','positive_job_or_worker_admission','quota_or_assignment_issuer'):
        if manifest.get(name) is not False:raise ValueError('MANIFEST_DENIAL_REQUIRED')
    pins=manifest.get('root_modules_sha256')
    if type(pins) is not dict or set(pins)!=set(OWNER_MODULES):raise ValueError('ROOT_OWNER_PINS_REQUIRED')
    for name,digest in pins.items():
        if not name.startswith('unified_system/') or bindings.get(name,{}).get('sha256')!=digest:raise ValueError('ROOT_OWNER_SOURCE_MISMATCH')

def validate_retirement(rows,expected_count):
    if (len(rows)!=expected_count or len({r['pid'] for r in rows})!=expected_count or
        any(type(r['pid']) is not int or r['pid']<=0 or type(r['returncode']) is not int for r in rows)):
        raise ValueError('OWNED_PROCESS_NOT_RETIRED')

def result_passed(result,expected_count):
    return result is not None and result.wasSuccessful() and result.testsRun==expected_count and not result.skipped and not result.expectedFailures and not result.unexpectedSuccesses

def case_ids(suite):
    for test in suite:
        if isinstance(test,unittest.TestSuite):yield from case_ids(test)
        else:yield test.id()

def declared_ids(root,modules):
    result=[]
    for folder,module in modules:
        tree=ast.parse((root/'tests'/folder/(module+'.py')).read_bytes())
        for cls in tree.body:
            if isinstance(cls,ast.ClassDef):
                for method in cls.body:
                    if isinstance(method,(ast.FunctionDef,ast.AsyncFunctionDef)) and method.name.startswith('test_'):
                        result.append(module+'.'+cls.name+'.'+method.name)
    return sorted(result)

def ordinary(path):
    for part in (path,*path.parents):
        info=part.lstat()
        if part.is_symlink() or getattr(info,'st_file_attributes',0)&1024:raise ValueError('SOURCE_ALIAS')
        if not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):raise ValueError('SOURCE_SPECIAL')
        if stat.S_ISREG(info.st_mode) and info.st_nlink!=1:raise ValueError('SOURCE_HARDLINK')

def main(profile,script):
    global _OUT
    parser=argparse.ArgumentParser()
    parser.add_argument('--expected-head',required=True)
    parser.add_argument('--consul-binary',required=True)
    parser.add_argument('--evidence',required=True)
    args=parser.parse_args()
    if not (sys.flags.isolated and sys.dont_write_bytecode and sys.pycache_prefix is None):raise ValueError('PYTHON_ISOLATION')
    if platform.python_version()!='3.12.10':raise ValueError('CPYTHON_VERSION')
    if re.fullmatch('[a-f0-9]{40}',args.expected_head) is None:raise ValueError('EXPECTED_HEAD')
    forbidden=('GIT_DIR','GIT_WORK_TREE','GIT_COMMON_DIR','GIT_INDEX_FILE','GIT_OBJECT_DIRECTORY','GIT_ALTERNATE_OBJECT_DIRECTORIES','GIT_REPLACE_REF_BASE','GIT_CONFIG','GIT_CONFIG_GLOBAL','GIT_CONFIG_SYSTEM','GIT_CONFIG_COUNT','GIT_CONFIG_PARAMETERS','GIT_CONFIG_KEY_','GIT_CONFIG_VALUE_')
    if any(name==prefix or prefix.endswith('_') and name.startswith(prefix) for name in os.environ for prefix in forbidden):raise ValueError('GIT_ENV_OVERRIDE_REJECTED')
    if 'A2_RESEARCH_GRID_SOURCE' in os.environ:raise ValueError('RETIRED_SOURCE_ENV_REJECTED')
    if any(value and name.startswith(('BYBIT_','BINANCE_','TRADING_')) and ('KEY' in name or 'SECRET' in name) for name,value in os.environ.items()):raise ValueError('TRADING_CREDENTIAL_ENV_REJECTED')
    root=Path(script).absolute().parents[4];out=Path(args.evidence).absolute()
    ordinary(Path(script).absolute())
    ordinary(root/'.git')
    if out.resolve().is_relative_to(root.resolve()):raise ValueError('EVIDENCE_INSIDE_SOURCE')
    out.mkdir(exist_ok=False);_OUT=out
    git_path=Path('C:/Program Files/Git/cmd/git.exe' if os.name=='nt' else '/usr/bin/git').resolve(strict=True)
    os.environ['PATH']=str(git_path.parent);os.environ['GIT_NO_LAZY_FETCH']='1';os.environ['PYTHONDONTWRITEBYTECODE']='1'
    def primary_git(*arguments,input=None):
        return subprocess.check_output([str(git_path),'--no-replace-objects','--no-optional-locks','-c','core.fsmonitor=false','-C',str(root),*arguments],input=input,timeout=30)
    if primary_git('rev-parse','HEAD').decode().strip()!=args.expected_head:raise ValueError('HEAD_MISMATCH')
    tree=primary_git('rev-parse','HEAD^{tree}').decode().strip()
    helper=primary_git('show',BASE+':'+HELPER)
    if hashlib.sha256(helper).hexdigest()!=HELPER_SHA:raise ValueError('SOURCE_GUARD_MISMATCH')
    os.environ['A4_RESULT_EVIDENCE']=str(out/'guard-bootstrap')
    guard={'__name__':'pinned_root_primary_guard','__file__':str(root/HELPER)}
    exec(compile(helper,'<pinned-primary-source-guard>','exec'),guard)
    guard['ROOT']=root;guard['git']=primary_git
    before=guard['primary']();guard['physical'](before)
    if primary_git('status','--porcelain','--untracked-files=all').strip():raise ValueError('DIRTY_SOURCE')
    manifest=json.loads((root/'release/integration/native-negative-v2/manifest.json').read_bytes());validate_manifest(manifest,before)
    guard_cases=json.loads((root/manifest['root_source_guards']['expected_cases']).read_bytes())
    validate_ids(guard_cases,guard_cases)
    if manifest['root_source_guards']['tests']!=len(guard_cases):raise ValueError('ROOT_GUARD_MANIFEST_COUNT')
    os.environ['A2_RESEARCH_CONSUL_BINARY']=args.consul_binary
    # Separate refusing-stub source guards cannot qualify TLS or Consul success.
    pure=subprocess.run([sys.executable,'-I','-B',str(root/'tests/gateway_research_identity/run_root_authority_inert.py')],capture_output=True,timeout=60)
    (out/'root-source-guards.log').write_bytes(pure.stdout+pure.stderr)
    if pure.returncode:raise ValueError('ROOT_SOURCE_GUARDS_FAILED')
    binding_pure=subprocess.run([sys.executable,'-I','-B',str(root/'tests/gateway_research_identity/run_canonical_binding_inert.py')],capture_output=True,timeout=60)
    (out/'canonical-binding-data.log').write_bytes(binding_pure.stdout+binding_pure.stderr)
    if binding_pure.returncode:raise ValueError('CANONICAL_BINDING_DATA_FAILED')
    guard['physical'](before)
    config=manifest['profiles'][profile]
    expected=json.loads((root/config['expected_cases']).read_bytes())
    validate_ids(declared_ids(root,config['test_modules']),expected)
    sys.path[:0]=[str(root),str(root/'tests/gateway_research_identity'),str(root/'tests/gateway_native_negative')]
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in expected)
    actual=validate_ids(list(case_ids(suite)),expected)
    result=None;binding=False;owned=[];origins={}
    try:
        with (out/'native-tests.log').open('w',encoding='utf-8') as log:result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    finally:
        guard['physical'](before)
        if guard['primary']()!=before or primary_git('rev-parse','HEAD').decode().strip()!=args.expected_head or primary_git('rev-parse','HEAD^{tree}').decode().strip()!=tree:raise ValueError('SOURCE_CHANGED')
        if primary_git('status','--porcelain','--untracked-files=all').strip():raise ValueError('DIRTY_SOURCE_AFTER')
        for name,module in tuple(sys.modules.items()):
            if name.split('.')[0] in ('grid','strattester','meta_analyse'):raise ValueError('RETIRED_MODULE_IMPORTED')
            if name=='unified_system' or name.startswith('unified_system.'):
                source=Path(module.__file__).resolve();relative=source.relative_to(root.resolve()).as_posix()
                if source.suffix!='.py' or relative not in before:raise ValueError('PROJECT_ORIGIN')
                origins[name]=relative
        for module_name,class_name in config['native_classes']:
            cls=getattr(sys.modules.get(module_name),class_name,None);lab=getattr(cls,'lab',None)
            for process in [] if lab is None else lab.processes:owned.append({'pid':process.pid,'returncode':process.poll()})
        validate_retirement(owned,config['owned_processes'])
        binding=True
        passed=result_passed(result,len(expected))
        report=dict(schema='unified.root-owned-native.source-qualification.v2',profile=profile,scope=config['scope'],head=args.expected_head,tree=tree,passed=passed,source_binding_passed=binding,native_test_ids=actual,native_tests=None if result is None else result.testsRun,failures=None if result is None else len(result.failures),errors=None if result is None else len(result.errors),skips=None if result is None else len(result.skipped),root_source_guard_tests=len(guard_cases),canonical_binding_data_tests=9,canonical_binding_native_proof=False,pure_guard_process_retired=True,root_source_guard_scope='INERT_SOURCE_ONLY_CRYPTO_OPERATIONS_REFUSE',primary_before=before,module_origins=origins,owned_processes_retired=owned,source_helper_sha256=HELPER_SHA,python=sys.version,git_path=str(git_path),git_sha256=hashlib.sha256(git_path.read_bytes()).hexdigest(),public_submit='DENY',native_job_permission=False,full_scientific_e2e=False,physical='NOT_RUN',production='NO_GO')
        report['native_log_sha256']=hashlib.sha256((out/'native-tests.log').read_bytes()).hexdigest()
        (out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    if not passed:raise ValueError('NATIVE_QUALIFICATION_FAILED_OR_SKIPPED')
    print(json.dumps({'passed':True,'head':args.expected_head,'native_tests':len(expected),'root_source_guard_tests':len(guard_cases),'scope':config['scope'],'native_job_permission':False}))

def entrypoint(profile,script):
    try:main(profile,script)
    except BaseException as exc:
        if _OUT is not None:(_OUT/'failure.json').write_text(json.dumps({'status':'FAILED_NO_QUALIFICATION','error_type':type(exc).__name__,'native_job_permission':False,'public_submit':'DENY'})+'\n',encoding='utf-8')
        raise
