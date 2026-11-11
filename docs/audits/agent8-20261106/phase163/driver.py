import hashlib,io,json,os,pathlib,subprocess,sys,unittest,threading,ssl,faulthandler,importlib.metadata
faulthandler.dump_traceback_later(55,exit=True)
root=pathlib.Path.cwd();expected='38572e56743692dd78f052c89125accec4677ea2';git='C:/Program Files/Git/cmd/git.exe'
out=pathlib.Path('C:/Users/LS-5/.codex/ci-boundary-evidence-20261110')
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
print(json.dumps({'head':expected,'python':sys.version,'openssl':ssl.OPENSSL_VERSION,'cryptography':cryptography.__version__,'scope':'ROOT_PURE_LAN_DIAGNOSTIC_ONLY'}),flush=True)

from unittest.mock import patch
inventory_json=json.loads((root/'release/component-test-inventory.json').read_bytes())
all_suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in inventory_json['modules'])
def ids(suite):
 for item in suite:
  if isinstance(item,unittest.TestSuite):yield from ids(item)
  else:yield item.id()
all_ids=list(ids(all_suite));assert len(all_ids)==len(set(all_ids))==161
assert sorted(all_ids)==inventory_json['expected_test_ids']
assert len(inventory_json['preserved_prior_ids'])==145 and set(inventory_json['preserved_prior_ids'])<=set(all_ids)
suite=unittest.defaultTestLoader.loadTestsFromName('tests.test_lan_transport.FailureDiagnosticsPureTests');selected_ids=list(ids(suite));assert len(selected_ids)==16
calls={'socket':0,'sqlite':0,'subprocess':0}
def deny(name):
 def fail(*args,**kwargs):calls[name]+=1;raise AssertionError('UNEXPECTED_RESOURCE_CALL')
 return fail
with patch('socket.socket',side_effect=deny('socket')),patch('sqlite3.connect',side_effect=deny('sqlite')),patch('subprocess.Popen',side_effect=deny('subprocess')):
 result=unittest.TextTestRunner(verbosity=2).run(suite)
assert result.wasSuccessful() and result.testsRun==16 and not result.skipped and not any(calls.values())
after=inventory();assert before==after
threads=[t.name for t in threading.enumerate() if t is not threading.main_thread()];assert not threads
receipt=dict(head=expected,tree=g('rev-parse','HEAD^{tree}').decode().strip(),qualification='PURE_DIAGNOSTIC_ONLY_NOT_161_CASE_EXECUTION',discovered_ids=all_ids,test_ids=selected_ids,tests_run=result.testsRun,skips=len(result.skipped),guarded_resource_calls=calls,source_before=before,source_after=after,threads_remaining=threads,native_execution=False,tls_execution=False,physical_admission=False)
(out/'lan-diag-38572e5-receipt.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode())
faulthandler.cancel_dump_traceback_later()
print('PURE_DIAG16_PASS discovery161_preserved145 source_prepost_equal=True resource_calls=0 fixture_execution=0 threads=0',flush=True)
