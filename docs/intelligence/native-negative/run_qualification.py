"""Exact-source actual internal negative composition; no public/effect admission."""
import argparse
import functools
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import unittest

GRID_HEAD='b0ddb78fed04cc29c7b0290ae75d1d8af84fcfec'
BASE='3af06455b601a328e94339327a0597eada802c38'
HELPER='tests/storage/native_publication/qualify.py'
HELPER_SHA='e71934d06625a5b1c2047cd32c23c4005f2c400b438717b6b3394ecb7855edee'
_EVIDENCE=None

def main():
    global _EVIDENCE
    parser=argparse.ArgumentParser()
    parser.add_argument('--expected-head',required=True)
    parser.add_argument('--grid-root',required=True)
    parser.add_argument('--consul-binary',required=True)
    parser.add_argument('--evidence',required=True)
    args=parser.parse_args()
    assert sys.flags.isolated and sys.dont_write_bytecode and sys.pycache_prefix is None
    assert platform.python_version()=='3.12.10'
    forbidden=('GIT_DIR','GIT_WORK_TREE','GIT_COMMON_DIR','GIT_INDEX_FILE','GIT_OBJECT_DIRECTORY','GIT_ALTERNATE_OBJECT_DIRECTORIES','GIT_REPLACE_REF_BASE','GIT_CONFIG','GIT_CONFIG_GLOBAL','GIT_CONFIG_SYSTEM','GIT_CONFIG_COUNT','GIT_CONFIG_PARAMETERS','GIT_CONFIG_KEY_','GIT_CONFIG_VALUE_')
    assert not any(name==prefix or prefix.endswith('_') and name.startswith(prefix) for name in os.environ for prefix in forbidden),'GIT_ENV_OVERRIDE_REJECTED'
    assert not any(value and name.startswith(('BYBIT_','BINANCE_','TRADING_')) and ('KEY' in name or 'SECRET' in name) for name,value in os.environ.items()),'TRADING_CREDENTIAL_ENV_REJECTED'
    root=Path(__file__).absolute().parents[3];grid=Path(args.grid_root).absolute();out=Path(args.evidence).absolute()
    assert not out.resolve().is_relative_to(root.resolve()) and not out.resolve().is_relative_to(grid.resolve())
    out.mkdir(exist_ok=False);_EVIDENCE=out
    git=Path('C:/Program Files/Git/cmd/git.exe' if os.name=='nt' else '/usr/bin/git').resolve(strict=True)
    os.environ['PATH']=str(git.parent);os.environ['GIT_NO_LAZY_FETCH']='1';os.environ['PYTHONDONTWRITEBYTECODE']='1'
    def primary_git(path,*arguments,input=None):
        return subprocess.check_output([str(git),'--no-replace-objects','--no-optional-locks','-c','core.fsmonitor=false','-C',str(path),*arguments],input=input,timeout=30)
    assert primary_git(root,'rev-parse','HEAD').decode().strip()==args.expected_head
    assert primary_git(grid,'rev-parse','HEAD').decode().strip()==GRID_HEAD
    helper=primary_git(root,'show',BASE+':'+HELPER);assert hashlib.sha256(helper).hexdigest()==HELPER_SHA
    os.environ['A4_RESULT_EVIDENCE']=str(out/'guard-bootstrap')
    guards={}
    for label,path in [('unified',root),('grid',grid)]:
        namespace={'__name__':'owned_guard_'+label,'__file__':str(root/HELPER)}
        exec(compile(helper,'<pinned-primary-source-guard>','exec'),namespace)
        namespace['ROOT']=path;namespace['git']=functools.partial(primary_git,path)
        guards[label]=namespace
    before={label:guard['primary']() for label,guard in guards.items()}
    for label,guard in guards.items():
        guard['physical'](before[label]);assert not guard['git']('status','--porcelain','--untracked-files=all').strip()
    manifest=json.loads((root/'release/integration/native-negative-v1/manifest.json').read_bytes())
    assert manifest['grid_head']==GRID_HEAD and manifest['public_submit']=='DENY'
    assert manifest['root_module_sha256']==before['unified']['unified_system/gateway_native_negative.py']['sha256']
    assert all(manifest[name] is False for name in ('public_http_endpoint','full_scientific_e2e','positive_job_or_worker_admission','quota_or_assignment_issuer'))
    expected=json.loads((Path(__file__).parent/'EXPECTED-TESTS.json').read_bytes())
    os.environ['A2_RESEARCH_GRID_SOURCE']=str(grid);os.environ['A2_RESEARCH_CONSUL_BINARY']=args.consul_binary
    sys.path[:0]=[str(root),str(grid),str(root/'tests/gateway_research_identity')]
    suite=unittest.defaultTestLoader.discover(str(root/'tests/gateway_native_negative'),pattern='test_*.py')
    def cases(value):
        for item in value:
            if isinstance(item,unittest.TestSuite):yield from cases(item)
            else:yield item.id()
    actual=list(cases(suite));assert len(actual)==len(set(actual))==len(expected)==len(set(expected))==20 and sorted(actual)==expected
    result=None;binding=False;failure=None;origins={};owned=[]
    try:
        with (out/'tests.log').open('w',encoding='utf-8') as log:
            result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    finally:
        try:
            for label,guard in guards.items():
                guard['physical'](before[label]);assert guard['primary']()==before[label]
                assert not guard['git']('status','--porcelain','--untracked-files=all').strip()
            for name,module in tuple(sys.modules.items()):
                if name=='unified_system' or name.startswith('unified_system.') or name=='grid' or name.startswith('grid.'):
                    label='grid' if name=='grid' or name.startswith('grid.') else 'unified'
                    owner=grid if label=='grid' else root
                    source=Path(module.__file__).resolve();relative=source.relative_to(owner.resolve()).as_posix()
                    assert source.suffix=='.py' and relative in before[label]
                    origins[name]={'project':label,'path':relative}
            module=sys.modules.get('test_actual');lab=getattr(getattr(module,'GatewayNegativeTests',None),'lab',None)
            processes=[] if lab is None else lab.processes
            owned=[dict(pid=process.pid,returncode=process.poll()) for process in processes]
            assert all(item['returncode'] is not None for item in owned),'OWNED_PROCESS_NOT_RETIRED'
            binding=True
        except BaseException as exc:
            failure=type(exc).__name__
            raise
        finally:
            passed=binding and result is not None and result.wasSuccessful() and result.testsRun==20 and not result.skipped and len(owned)==3
            report=dict(schema='unified.native-negative.source-qualification.v1',scope='REAL_MTLS_INTERNAL_NEGATIVE_COMPOSITION_NO_HTTP_ENDPOINT',head=args.expected_head,tree=primary_git(root,'rev-parse','HEAD^{tree}').decode().strip(),grid_head=GRID_HEAD,passed=passed,source_binding_passed=binding,source_failure_type=failure,tests=None if result is None else result.testsRun,errors=None if result is None else len(result.errors),failures=None if result is None else len(result.failures),skips=None if result is None else len(result.skipped),test_ids=actual,primary_before=before,primary_after_equal=binding,module_origins=origins,owned_processes_retired=owned,source_helper_sha256=HELPER_SHA,git_path=str(git),git_sha256=hashlib.sha256(git.read_bytes()).hexdigest(),python=sys.version,python_executable=sys.executable,run=os.environ.get('GITHUB_RUN_ID'),attempt=os.environ.get('GITHUB_RUN_ATTEMPT'),public_submit='DENY',native_job_permission=False,full_scientific_e2e=False,physical='NOT_RUN',production='NO_GO')
            if (out/'tests.log').exists():report['test_log_sha256']=hashlib.sha256((out/'tests.log').read_bytes()).hexdigest()
            (out/'qualification.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
    assert passed,'NATIVE_NEGATIVE_QUALIFICATION_FAILED'
    print(json.dumps(dict(passed=True,head=args.expected_head,grid_head=GRID_HEAD,tests=20,skips=0,source_files={k:len(v) for k,v in before.items()},scope=report['scope'])))

if __name__=='__main__':
    try:main()
    except BaseException as exc:
        if _EVIDENCE is not None:
            (_EVIDENCE/'failure.json').write_bytes((json.dumps(dict(status='FAILED_NO_QUALIFICATION',error_type=type(exc).__name__,native_job_permission=False,public_submit='DENY'))+'\n').encode())
        raise
