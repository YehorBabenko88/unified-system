"""Run selected Grid negatives with process-wide outbound socket connect denied."""
import argparse,hashlib,ipaddress,json,os,pathlib,socket,subprocess,sys
parser=argparse.ArgumentParser();parser.add_argument('--source',type=pathlib.Path,required=True);parser.add_argument('--output',type=pathlib.Path,required=True);parser.add_argument('--scratch',type=pathlib.Path,required=True);parser.add_argument('--expected-head',default='71084a336520187d6e260531a2f5d15555ba0e0c');parser.add_argument('--suite',choices=['storage-coordination','budget'],default='storage-coordination')
args=parser.parse_args();source=args.source.resolve();out=args.output.resolve();scratch=args.scratch.resolve();out.mkdir(parents=True,exist_ok=True);scratch.mkdir(parents=True,exist_ok=True)
sha=args.expected_head
def git(*args):return subprocess.check_output(['git','-C',str(source),*args])
assert git('rev-parse','HEAD').decode().strip()==sha
assert not git('status','--porcelain','--untracked-files=all').strip()
def identity():
    entries=git('ls-tree','-r','-z',sha).split(b'\0');hashes={}
    for entry in filter(None,entries):
        meta,raw_name=entry.split(b'\t',1);mode,kind,oid=meta.split();name=raw_name.decode()
        assert kind==b'blob' and mode in (b'100644',b'100755')
        actual=(source/name).read_bytes()
        assert hashlib.sha1(b'blob '+str(len(actual)).encode()+b'\0'+actual).hexdigest()==oid.decode(),'RAW_SOURCE_MISMATCH '+name
        hashes[name]=hashlib.sha256(actual).hexdigest()
    return hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()
before=identity()
original_connect=socket.socket.connect;original_connect_ex=socket.socket.connect_ex
def guarded(method):
    def connect(sock,address):
        try:allowed=isinstance(address,tuple) and ipaddress.ip_address(address[0]).is_loopback
        except ValueError:allowed=False
        if not allowed:raise RuntimeError('AUDITOR_NON_LOOPBACK_NETWORK_DENIED')
        return method(sock,address)
    return connect
# Windows asyncio creates a loopback self-pipe; blocking that would invalidate every async test.
socket.socket.connect=guarded(original_connect);socket.socket.connect_ex=guarded(original_connect_ex)
os.environ['NODE_ID']='auditor-synthetic-node';os.environ['PROGRAMDATA']=str(scratch/'programdata')
os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1';sys.dont_write_bytecode=True
sys.path.insert(0,str(source));os.chdir(source)
import pytest
tests=['tests/coordination/test_consul_authority.py','tests/coordination/test_coordinated_runtime.py',
       'tests/coordination/test_coordination_commands.py','tests/coordination/test_budget_anchor.py',
       'tests/test_segment_wal.py','tests/test_control_replication.py','tests/test_archive_disk_budget.py']
tests+=sorted(p.relative_to(source).as_posix() for p in (source/'tests').glob('test_wal_*.py'))
if args.suite=='budget':tests=['tests/test_network_budget_model.py','tests/test_network_budget_simulation.py','tests/test_network_budget_store.py']
code=int(pytest.main(['-q','-p','no:cacheprovider','--basetemp',str(scratch/'pytest-owned'),
       '--junitxml',str(out/'grid-offline.xml'),*tests]))
after=identity();assert before==after
(out/'grid-run-receipt.json').write_text(json.dumps({'head':sha,'tree':git('rev-parse','HEAD^{tree}').decode().strip(),
 'python':sys.version,'exit_code':code,'tests':tests,'source_before_sha256':before,'source_after_sha256':after,
 'source_raw_blobs_verified':True,'non_loopback_socket_connect':'DENIED','consensus':'MODELED_ONLY',
 'storage':'TEMP_TEST_DATA_ONLY','physical':'BLOCKED','production_deployment':'NOT_AUTHORIZED'},indent=2))
raise SystemExit(code)
