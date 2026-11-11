import hashlib,io,json,os,pathlib,subprocess,sys,unittest,threading,ssl,faulthandler,importlib.metadata
faulthandler.dump_traceback_later(55,exit=True)
root=pathlib.Path.cwd();expected='71989562c51a008201babb222391211757eaf402';git='C:/Program Files/Git/cmd/git.exe'
out=pathlib.Path('C:/Users/LS-5/.codex/gateway-strict-pki-evidence-20261110')
assert sys.version_info[:3]==(3,12,10) and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode and sys.pycache_prefix is None
assert not os.environ.get('SSLKEYLOGFILE')
def g(*args,input=None):return subprocess.check_output([git,'--no-replace-objects','--no-optional-locks','-c','core.fsmonitor=false',*args],cwd=root,input=input)
assert g('rev-parse','HEAD').decode().strip()==expected
def inventory():
 entries=[];dirs={''}
 for row in g('ls-tree','-rz','--full-tree','HEAD').split(b'\0'):
  if not row:continue
  meta,name=row.split(b'\t',1);mode,kind,oid=meta.split();assert mode in (b'100644',b'100755') and kind==b'blob'
  name=name.decode();entries.append((name,oid.decode()));dirs.update(p.as_posix() for p in pathlib.PurePosixPath(name).parents if p.as_posix()!='.')
 stream=io.BytesIO(g('cat-file','--batch',input=''.join(oid+'\n' for _,oid in entries).encode()));result={}
 for name,oid in entries:
  actual,kind,size=stream.readline().split();data=stream.read(int(size));assert actual.decode()==oid and kind==b'blob' and stream.read(1)==b'\n'
  path=root/name;assert path.is_file() and not path.is_symlink() and path.read_bytes()==data,name;result[name]=hashlib.sha256(data).hexdigest()
 assert not stream.read()
 for path in root.rglob('*'):
  rel=path.relative_to(root)
  if rel.parts[0]=='.git':continue
  assert not path.is_symlink() and not (getattr(path.lstat(),'st_file_attributes',0)&1024),str(rel)
  if path.is_file():assert rel.as_posix() in result and path.suffix not in ('.pyc','.pyo'),str(rel)
  elif path.is_dir():assert rel.as_posix() in dirs,str(rel)
  else:raise AssertionError(str(rel))
 return result
before=inventory();deps=pathlib.Path('C:/Users/LS-5/Documents/Codex/2026-11-06/codex-agent-8-independent-security-ci/work/identity-a8-env/Lib/site-packages');sys.path[:0]=[str(root),str(root/'tests'),str(deps)]
import cryptography
assert pathlib.Path(cryptography.__file__).resolve().is_relative_to(deps)
assert importlib.metadata.version('cryptography')=='46.0.3'
print(json.dumps({'head':expected,'python':sys.version,'openssl':ssl.OPENSSL_VERSION,'cryptography':cryptography.__version__,'scope':'ROOT_SERIAL_GATEWAY_ONLY'}),flush=True)
suite=unittest.defaultTestLoader.loadTestsFromName('test_gateway_identity');ids=[]
def collect(s):
 for item in s:
  if isinstance(item,unittest.TestSuite):collect(item)
  else:ids.append(item.id())
collect(suite);assert len(ids)==len(set(ids))==25
result=None;after=None
try:
 result=unittest.TextTestRunner(verbosity=2).run(suite)
 assert result.wasSuccessful() and result.testsRun==25 and not result.skipped
finally:
 after=inventory();assert before==after
 threads=[t.name for t in threading.enumerate() if t is not threading.main_thread()]
 receipt=dict(head=expected,python=sys.version,openssl=ssl.OPENSSL_VERSION,cryptography=cryptography.__version__,test_ids=ids,tests_run=None if result is None else result.testsRun,skips=None if result is None else len(result.skipped),source_before=before,source_after=after,threads_remaining=threads,qualification='SYNTHETIC_GATEWAY_STRICT_FIXTURE_ONLY',runtime_admission=False,physical_admission=False)
 (out/'final-exact-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
 assert not threads,threads
 faulthandler.cancel_dump_traceback_later()
print('ROOT_GATEWAY_SERIAL_LANE_RETIRED source_prepost_equal=True threads_remaining=0 tests=25 skips=0',flush=True)
