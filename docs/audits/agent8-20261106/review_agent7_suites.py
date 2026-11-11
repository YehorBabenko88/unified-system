"""Reproduce Agent7 added Python suites on clean exact sources; no non-loopback IO."""
import argparse,hashlib,ipaddress,json,os,pathlib,socket,subprocess,sys,tempfile
p=argparse.ArgumentParser();p.add_argument('--repo',choices=['strattester','meta_analyse'],required=True);a=p.parse_args()
ROOT=pathlib.Path(__file__).resolve().parents[1];source=ROOT/'work'/('review7-'+a.repo);out=ROOT/'outputs/phase4';scratch=ROOT/'work'/('review7-scratch-'+a.repo);scratch.mkdir(parents=True,exist_ok=True)
sha={'strattester':'1722244f42d5d71a29b89bdec0e7211f2b723158','meta_analyse':'88b45c328bfdc8131ff0c6d139fddd8b27a4050c'}[a.repo]
def git(*args):return subprocess.check_output(['git','-C',str(source),*args])
assert git('rev-parse','HEAD').decode().strip()==sha and not git('status','--porcelain').strip()
def identity():
    hashes={}
    for row in filter(None,git('ls-tree','-r','-z',sha).split(b'\0')):
        meta,name=row.split(b'\t',1);mode,kind,oid=meta.split();name=name.decode();data=(source/name).read_bytes()
        assert kind==b'blob' and mode in (b'100644',b'100755')
        assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==oid.decode(),name
        hashes[name]=hashlib.sha256(data).hexdigest()
    return hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()
before=identity();sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1';os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1'
tempfile.tempdir=str(scratch);os.environ.update(TEMP=str(scratch),TMP=str(scratch))
for key in ('META_ANALYSE_TEST_ADMIN_DSN','DATABASE_URL','STRATTESTER_GRID_DSN','PGHOST','PGPORT','PGDATABASE','PGUSER','PGPASSWORD'):os.environ.pop(key,None)
def guarded(method):
    def invoke(sock,address):
        try:allowed=isinstance(address,tuple) and ipaddress.ip_address(address[0]).is_loopback
        except ValueError:allowed=False
        if not allowed:raise RuntimeError('AUDITOR_NON_LOOPBACK_NETWORK_DENIED')
        return method(sock,address)
    return invoke
socket.socket.connect=guarded(socket.socket.connect);socket.socket.connect_ex=guarded(socket.socket.connect_ex)
os.chdir(source);sys.path.insert(0,str(source));sys.path.insert(0,str(source/'src'))
import pytest
tests=['tests/research/test_agent7_paper_integrity.py','tests/research/test_agent7_research_replay.py'] if a.repo=='strattester' else ['tests/test_agent7_ohlcv_research_contract.py']
code=int(pytest.main(['-q','--noconftest','-p','no:cacheprovider','--basetemp',str(scratch/'pytest-owned'),'--junitxml',str(out/(a.repo+'-added-tests.xml')),*tests]))
after=identity();assert before==after
(out/(a.repo+'-suite-receipt.json')).write_text(json.dumps({'head':sha,'tree':git('rev-parse','HEAD^{tree}').decode().strip(),'suite':tests,'exit_code':code,'source_before_sha256':before,'source_after_sha256':after,'source_raw_git_blobs_verified':True,'scope':'LOCAL_WINDOWS_SYNTHETIC_SELECTED_ADDED_TESTS','non_loopback_network':'DENIED','physical':'BLOCKED','endpoint_ACK':'PENDING','mandatory_system_acceptance':'NOT_QUALIFIED'},indent=2))
raise SystemExit(code)
