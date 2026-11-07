"""Exact raw source-bound mandatory unit + real Consul/HTTP slice execution."""
import argparse,hashlib,io,json,os,platform,subprocess,sys,unittest,stat
from pathlib import Path
if not sys.flags.isolated or not sys.dont_write_bytecode or sys.pycache_prefix is not None:raise RuntimeError('FRESH_ISOLATED_NO_BYTECODE_REQUIRED')

def git(root,*args):
    return subprocess.check_output(['git','--no-replace-objects','-C',str(root),*args],timeout=60)

def _no_links(path):
    for entry in (path,*path.parents):
        meta=entry.lstat()
        if stat.S_ISLNK(meta.st_mode) or getattr(meta,'st_file_attributes',0)&1024:raise AssertionError('SOURCE_LINK_OR_REPARSE')

def source_receipt(root,expected,excluded=()):
    _no_links(root)

    if git(root,'rev-parse','HEAD').decode().strip()!=expected:raise AssertionError('HEAD_MISMATCH')
    entries=[]
    for row in git(root,'ls-tree','-rz','--full-tree',expected).split(b'\0'):
        if not row:continue
        meta,name=row.split(b'\t',1);mode,kind,oid=meta.split()
        if kind!=b'blob' or mode not in (b'100644',b'100755'):raise AssertionError('UNSUPPORTED_SOURCE_ENTRY')
        path=name.decode('utf8');entries.append((path,oid.decode()))
    output=subprocess.run(['git','--no-replace-objects','-C',str(root),'cat-file','--batch'],input=(''.join(oid+'\n' for _,oid in entries)).encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,timeout=60).stdout
    stream=io.BytesIO(output);result={}
    for path,oid in entries:
        actual,kind,size=stream.readline().split();assert actual.decode()==oid and kind==b'blob'
        raw=stream.read(int(size));assert stream.read(1)==b'\n'
        file=root/path
        _no_links(file)
        if file.is_symlink() or not file.is_file() or file.read_bytes()!=raw:raise AssertionError('RAW_SOURCE_MISMATCH:'+path)
        result[path]=hashlib.sha256(raw).hexdigest()
    assert stream.read()==b''
    if sys.pycache_prefix is not None:raise AssertionError('PYCACHE_PREFIX')
    excluded={str(p.absolute()) for p in excluded}
    executable={'.py','.pyw','.pyi','.pyc','.pyo','.pyd','.so','.dll','.pth'}
    for parent,dirs,files in os.walk(root,followlinks=False):
        folder=Path(parent)
        for name in list(dirs):
            child=folder/name
            _no_links(child)
            if name=='.git' or str(child.absolute()) in excluded:dirs.remove(name)
        for name in files:
            child=folder/name;_no_links(child)
            rel=child.relative_to(root).as_posix()
            if child.suffix.lower() in ('.pyc','.pyo'):raise AssertionError('BYTECODE_PRESENT:'+rel)
            if child.suffix.lower() in executable and rel not in result:raise AssertionError('UNEXPECTED_IMPORTABLE:'+rel)
    return dict(head=expected,tree=git(root,'rev-parse',expected+'^{tree}').decode().strip(),raw_files=result)

UNITS={
 'test_codec.CodecTests.test_frozen_valid_vectors',
 'test_codec.CodecTests.test_numeric_aliases_and_noncanonical_rejected',
 'test_codec.CodecTests.test_depth_and_host_types',
 'test_codec.CodecTests.test_schema_specific',
 'test_commands.CommandTests.test_frozen_preimages',
 'test_commands.CommandTests.test_request_id_and_rbac_rejected',
 'test_http_api.DefaultClosedTests.test_missing_native_provider_never_reads_body_or_authority',
 'test_http_api.DefaultClosedTests.test_error_envelope_and_head',
 'test_http_api.DefaultClosedTests.test_head_has_no_body',
 'test_http_api.DefaultClosedTests.test_async_runtime_missing_native_provider_closed'}
EVENTS=['ARBITRARY_OWNER_REJECTED_BEFORE_PREPARE','REAL_HTTP_POST_OPEN_TO_REAL_GRID_CONSUL',
 'LOST_FINAL_COMMIT_RESPONSE_RECONCILED_ACTUAL_RECEIPT','OPEN_ACTUAL_ATOMIC_RECEIPT_IDEMPOTENT_RECONCILE',
 'GLOBAL_REQUEST_UUID_CONFLICT','LOST_PREPARE_RESPONSE_PENDING_HOLD_AND_ADAPTER_RESTART_RESUME',
 'CAPACITY_PREPARATION_ATOMIC_BOUND_NO_DURABLE_OVERFLOW','CURRENT_REVOKED_IDENTITY_REJECTED',
 'DESTROYED_LEADER_SESSION_NEW_INTENT_DENIED','ONE_OF_THREE_NO_QUORUM_NO_SUCCESS']

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--real-only',action='store_true');p.add_argument('--expected-head',required=True);p.add_argument('--grid-source',type=Path,required=True);p.add_argument('--binary',required=True);p.add_argument('--scratch',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    root=Path(__file__).absolute().parents[2];grid=a.grid_source.absolute();a.output.mkdir(parents=True,exist_ok=a.real_only)
    exclusions=tuple(p for p in (grid,Path(sys.prefix).absolute()) if p.is_relative_to(root) and p!=root)
    if a.output.absolute().is_relative_to(root):
        if a.output.absolute()!=root/'.lab-evidence':raise AssertionError('UNEXPECTED_IN_SOURCE_EVIDENCE')
        exclusions=exclusions+(a.output.absolute(),)
    if Path(sys.prefix).is_relative_to(root) and Path(sys.prefix).absolute()!=root/'.runtime-env':raise AssertionError('UNEXPECTED_IN_SOURCE_ENVIRONMENT')
    before=source_receipt(root,a.expected_head,excluded=exclusions);grid_before=source_receipt(grid,'58cfe0f51bc05bb0ee2ed09368a9b64679358c63')
    if a.real_only:
        sys.path.insert(0,str(root));sys.path.insert(0,str(root/'tests/control_mux'))
        script=root/'tests/control_mux/test_real_consul.py'
        sys.argv=[str(script),'--binary',a.binary,'--scratch',a.scratch,'--grid-source',str(grid),'--output',str(a.output/'real-consul.json')]
        exec(compile(script.read_bytes(),str(script),'exec'),{'__name__':'__main__','__file__':str(script)})
        assert before==source_receipt(root,a.expected_head,excluded=exclusions) and grid_before==source_receipt(grid,'58cfe0f51bc05bb0ee2ed09368a9b64679358c63')
        raise SystemExit(0)
    controls=[sys.executable,'-I','-B',str(root/'tests/control_mux/verify_source_binding.py'),'--scratch',str(a.output/'source-guard-controls'),'--output',str(a.output/'source-guard-controls.json')]
    completed_controls=subprocess.run(controls,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90)
    (a.output/'source-guard-controls.log').write_bytes(completed_controls.stdout)
    assert completed_controls.returncode==0,completed_controls.stdout.decode(errors='replace')[-4000:]
    guard_report=json.loads((a.output/'source-guard-controls.json').read_bytes())
    assert guard_report['result']=='PASS' and len(guard_report['cases'])==8
    executed=[]
    class Result(unittest.TextTestResult):
        def startTest(self,test):executed.append(test.id());super().startTest(test)
    sys.path.insert(0,str(root))
    suite=unittest.defaultTestLoader.discover(str(root/'tests/control_mux'))
    result=unittest.TextTestRunner(verbosity=1,resultclass=Result).run(suite)
    assert result.wasSuccessful() and not result.skipped and set(executed)==UNITS and len(executed)==len(UNITS),'MANDATORY_UNIT_INVENTORY'
    command=[sys.executable,'-I','-B',str(root/'tests/control_mux/source_runner.py'),'--real-only','--expected-head',a.expected_head,'--binary',a.binary,'--scratch',a.scratch,'--grid-source',str(grid),'--output',str(a.output)]
    env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1';env['GIT_NO_REPLACE_OBJECTS']='1'
    completed=subprocess.run(command,cwd=root,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
    (a.output/'real-consul.log').write_bytes(completed.stdout)
    assert completed.returncode==0,completed.stdout.decode(errors='replace')[-4000:]
    real=json.loads((a.output/'real-consul.json').read_bytes());assert real['events']==EVENTS and real['result']=='PASS' and real['owned_processes_stopped'] is True
    assert before==source_receipt(root,a.expected_head,excluded=exclusions) and grid_before==source_receipt(grid,'58cfe0f51bc05bb0ee2ed09368a9b64679358c63')
    report=dict(schema='agent2.control-mux.incremental-source-bound.v1',result='PASS',qualification='REAL_HTTP_GRID_CONSUL_OPEN_PRIMITIVE_SYNTHETIC_NATIVE_IDENTITY_ONLY',python=platform.python_version(),platform=platform.platform(),primary=before,grid=grid_before,executed_unit_ids=executed,executed_real_case_ids=real['events'],executed_source_guard_case_ids=guard_report['cases'],skips=[],native_authentication=False,final_endpoint_integrated=False,windows_runtime_accepted=False,physical_qualified=False,production='NO_GO')
    (a.output/'source-bound.json').write_bytes((json.dumps(report,indent=2)+'\n').encode());print(json.dumps(dict(result='PASS',unit_cases=len(executed),real_cases=len(EVENTS),primary_raw_files=len(before['raw_files']),grid_raw_files=len(grid_before['raw_files']),production='NO_GO')))
