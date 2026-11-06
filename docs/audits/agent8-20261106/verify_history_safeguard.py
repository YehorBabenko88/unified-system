"""Independent F13 exact-source negative oracle plus bounded regression rerun."""
import ast,asyncio,hashlib,importlib.util,json,os,pathlib,subprocess,sys
root=pathlib.Path(__file__).resolve().parents[1];repo=root/'work/review-grid263';oldrepo=root/'work/review-grid262';out=root/'outputs/phase15';out.mkdir(exist_ok=True)
head='ec967b3ebb67bb9f04d0d82c78bba5b4245a3333';base='a17f1db6b9aa04c105d2e993496026a83849ecfd';path='grid/instrument_lifecycle.py'
def git(source,*args):return subprocess.check_output(['git','-C',str(source),*args])
assert set(git(repo,'diff','--name-only',base,head).decode().splitlines())=={path,'tests/test_retired_history_preservation.py','docs/audits/retired-history-preservation.md'}
old_ast=ast.parse(git(repo,'show',base+':'+path));new_ast=ast.parse(git(repo,'show',head+':'+path))
def other(tree):return [ast.dump(n,include_attributes=False) for n in tree.body if not isinstance(n,ast.AsyncFunctionDef) or n.name!='purge_retired']
assert other(old_ast)==other(new_ast)
oldfn=next(n for n in old_ast.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='purge_retired');newfn=next(n for n in new_ast.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='purge_retired')
assert ast.dump(oldfn.args)==ast.dump(newfn.args)
def identity(source,sha):
 values=[]
 for row in git(source,'ls-tree','-rz',sha).split(b'\0'):
  if not row:continue
  meta,name=row.split(b'\t',1);mode,kind,oid=meta.split();data=(source/name.decode()).read_bytes()
  assert kind==b'blob' and hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==oid.decode(),name
  values.append([name.decode(),hashlib.sha256(data).hexdigest()])
 return hashlib.sha256(json.dumps(values).encode()).hexdigest()
before=identity(repo,head)
spec=importlib.util.spec_from_file_location('a8_history_fixed',repo/path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
probe_spec=importlib.util.spec_from_file_location('a8_original_probe',root/'outputs/probe_retired_history.py');original=importlib.util.module_from_spec(probe_spec);probe_spec.loader.exec_module(original)
pool=original.Pool();returned=asyncio.run(module.purge_retired(pool));assert returned==[] and pool.c.calls==[]
class NoAcquire:
 def acquire(self):raise AssertionError('DB_ACQUIRE_FORBIDDEN')
graces=[{}, {'grace_days':0},{'grace_days':365},{'grace_days':-1},{'grace_days':1000000}]
for kwargs in graces:assert asyncio.run(module.purge_retired(NoAcquire(),**kwargs))==[]
assert asyncio.run(module.purge_retired(None))==[]
results={}
scratch=root/'work/history-red-regression';scratch.mkdir(exist_ok=True);test=scratch/'test_retired_history_preservation.py';test.write_bytes((repo/'tests/test_retired_history_preservation.py').read_bytes())
for label,source,tests in [('red',oldrepo,[str(test)]),('green',repo,['tests/test_retired_history_preservation.py','tests/test_instrument_resilience.py','tests/test_bybit_resilience.py','tests/test_bybit_partial_discovery.py','tests/test_bybit_empty_discovery.py'])]:
 folder=out/label;folder.mkdir(exist_ok=True)
 code='''import sys,socket,ipaddress
sys.path.insert(0,__SOURCE__)
def deny(method):
 def wrapped(sock,address):
  if not isinstance(address,tuple) or not ipaddress.ip_address(address[0]).is_loopback:raise RuntimeError('A8_NON_LOOPBACK_DENIED')
  return method(sock,address)
 return wrapped
socket.socket.connect=deny(socket.socket.connect);socket.socket.connect_ex=deny(socket.socket.connect_ex)
import pytest
raise SystemExit(pytest.main(__ARGS__))
'''.replace('__SOURCE__',repr(str(source))).replace('__ARGS__',repr(['-q','--import-mode=importlib','--noconftest','-p','no:cacheprovider','--basetemp='+str(root/'work'/('history-fixture-'+label)),'--junitxml='+str(folder/'results.xml'),*tests]))
 env=os.environ.copy();env.update(PYTHONDONTWRITEBYTECODE='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
 run=subprocess.run([str(root/'work/audit-venv/Scripts/python.exe'),'-I','-B','-c',code],cwd=source,env=env,capture_output=True,timeout=60)
 (folder/'stdout.log').write_bytes(run.stdout);(folder/'stderr.log').write_bytes(run.stderr)
 import xml.etree.ElementTree as ET
 xml=ET.parse(folder/'results.xml');cases=xml.findall('.//testcase');failures=len(xml.findall('.//failure'));errors=len(xml.findall('.//error'));skips=len(xml.findall('.//skipped'))
 if label=='red':assert run.returncode!=0 and len(cases)==failures==4 and errors==skips==0
 else:assert run.returncode==0 and len(cases)==16 and failures==errors==skips==0
 results[label]={'head':base if label=='red' else head,'exit_code':run.returncode,'tests':len(cases),'failures':failures,'errors':errors,'skips':skips}
after=identity(repo,head);assert before==after
result={'head':head,'tree':git(repo,'rev-parse','HEAD^{tree}').decode().strip(),'base':base,'original_six_DELETE_oracle':'BASELINE_6_FIXED_0','fixed_pool_calls':pool.c.calls,'returned':returned,'no_acquire_graces':graces,'none_pool':'NO_IO_EMPTY_RESULT','AST_other_code_and_signature_unchanged':True,'all_other_tracked_files_unchanged':True,'source_raw_pre_post':[before,after],'regressions':results,'F13':'FIX_VERIFIED_OFFLINE_EXACT_SOURCE','production_affected':'NOT_DEPLOYED_BY_A8','broader_retention_protocol':'NOT_IMPLEMENTED_NOT_QUALIFIED','hosted':'NOT_QUALIFIED','physical':'BLOCKED','overall':'NO_GO'}
(out/'history-safeguard-review.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
