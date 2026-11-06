"""Source-bound Terminan synthetic cache/session/reconnect tests, loopback only."""
import hashlib,ipaddress,json,os,pathlib,socket,subprocess,sys,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];source=ROOT/'work/terminan-isolated';out=ROOT/'outputs/phase2';scratch=ROOT/'work/terminan-scratch'
scratch.mkdir(parents=True,exist_ok=True);tempfile.tempdir=str(scratch)
os.environ.update(TEMP=str(scratch),TMP=str(scratch),PYTHONDONTWRITEBYTECODE='1',NODE_ID='auditor-synthetic')
sys.dont_write_bytecode=True
sha='7ed3708df53c8850fd11fc8331440bdfee99aa3e'
def git(*args):return subprocess.check_output(['git','-C',str(source),*args])
assert git('rev-parse','HEAD').decode().strip()==sha and not git('status','--porcelain').strip()
def identity():
    hashes={}
    for entry in filter(None,git('ls-tree','-r','-z',sha).split(b'\0')):
        meta,name=entry.split(b'\t',1);mode,kind,oid=meta.split();name=name.decode();data=(source/name).read_bytes()
        assert kind==b'blob' and mode in (b'100644',b'100755')
        assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==oid.decode(),name
        hashes[name]=hashlib.sha256(data).hexdigest()
    return hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()
before=identity()
def guarded(method):
    def invoke(sock,address):
        try:allowed=isinstance(address,tuple) and ipaddress.ip_address(address[0]).is_loopback
        except ValueError:allowed=False
        if not allowed:raise RuntimeError('AUDITOR_NON_LOOPBACK_SOCKET_DENIED')
        return method(sock,address)
    return invoke
socket.socket.connect=guarded(socket.socket.connect);socket.socket.connect_ex=guarded(socket.socket.connect_ex);socket.socket.bind=guarded(socket.socket.bind)
os.chdir(source);sys.path.insert(0,str(source));sys.path.insert(0,str(source/'tests'))
names=['tests.test_cache_queue','tests.test_cache_reliability','tests.test_saved_cache',
 'tests.test_snapshot_recovery_audit','tests.test_dom_stream','tests.test_r4_session',
 'tests.test_r4_contracts','tests.test_trade_contract_numeric','tests.test_r3_reliability']
suite=unittest.defaultTestLoader.loadTestsFromNames(names)
result=unittest.TextTestRunner(verbosity=2).run(suite)
after=identity();assert before==after
(out/'terminan-receipt.json').write_text(json.dumps({'head':sha,'tree':git('rev-parse','HEAD^{tree}').decode().strip(),
 'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),
 'source_before_sha256':before,'source_after_sha256':after,'modules':names,
 'scope':'LOCAL_WINDOWS_SYNTHETIC_TEMP_SQLITE_AND_LOOPBACK','non_loopback_connect_and_bind':'DENIED',
 'physical':'BLOCKED','real_operator_authentication':'NOT_RUN','distributed_relocation':'NOT_RUN'},indent=2))
raise SystemExit(not(result.wasSuccessful() and not result.skipped))
