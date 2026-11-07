"""Independent pytest9.2 red/green of the test-only owned admission fixture."""
import ast,hashlib,ipaddress,json,os,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];out=ROOT/'outputs/phase12';out.mkdir(exist_ok=True)
old='71084a336520187d6e260531a2f5d15555ba0e0c';head='a17f1db6b9aa04c105d2e993496026a83849ecfd';repo=ROOT/'work/review-grid262';path='tests/test_owned_control_source.py'
def git(source,*args):return subprocess.check_output(['git','-C',str(source),*args])
assert git(repo,'diff','--name-only',old,head).decode().splitlines()==[path]
def functions(ref):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(git(repo,'show',ref+':'+path)).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name!='bound'}
assert functions(old)==functions(head)
def identity(source,sha):
 values=[]
 for row in git(source,'ls-tree','-rz',sha).split(b'\0'):
  if not row:continue
  meta,name=row.split(b'\t',1);mode,kind,oid=meta.split();data=(source/name.decode()).read_bytes()
  assert kind==b'blob' and hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==oid.decode(),name
  values.append([name.decode(),hashlib.sha256(data).hexdigest()])
 return hashlib.sha256(json.dumps(values).encode()).hexdigest()
results={}
for label,source,sha,version in [('red92',ROOT/'work/grid-isolated',old,'9.2'),('green92',repo,head,'9.2'),('green84',repo,head,'8.4')]:
 before=identity(source,sha);folder=out/label;folder.mkdir(exist_ok=True)
 paths=[str(source)]+([str(ROOT/'work/grid-pytest92')] if version=='9.2' else [])
 code='''import sys,os,socket,ipaddress
sys.path[:0]=__PATHS__
def deny(method):
 def wrapped(sock,address):
  if not isinstance(address,tuple) or not ipaddress.ip_address(address[0]).is_loopback:raise RuntimeError('A8_NON_LOOPBACK_DENIED')
  return method(sock,address)
 return wrapped
socket.socket.connect=deny(socket.socket.connect);socket.socket.connect_ex=deny(socket.socket.connect_ex)
import pytest
print('AUDITOR_PYTEST='+pytest.__version__)
raise SystemExit(pytest.main(['-q','--noconftest','-p','no:cacheprovider','--basetemp=__TEMP__','--junitxml=__XML__','tests/test_owned_control_source.py']))
'''.replace('__PATHS__',repr(paths)).replace('__TEMP__',(ROOT/'work'/('fixture-temp-'+label)).as_posix()).replace('__XML__',(folder/'results.xml').as_posix())
 env=os.environ.copy();env.update(PYTHONDONTWRITEBYTECODE='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
 for key in ('DATABASE_URL','PGHOST','PGPORT','PGDATABASE','PGUSER','PGPASSWORD'):env.pop(key,None)
 run=subprocess.run([str(ROOT/'work/audit-venv/Scripts/python.exe'),'-I','-B','-c',code],cwd=source,env=env,capture_output=True,timeout=90)
 (folder/'stdout.log').write_bytes(run.stdout);(folder/'stderr.log').write_bytes(run.stderr)
 after=identity(source,sha);assert before==after
 import xml.etree.ElementTree as ET
 xml=ET.parse(folder/'results.xml');cases=xml.findall('.//testcase');errors=len(xml.findall('.//error'));failures=len(xml.findall('.//failure'));skips=len(xml.findall('.//skipped'))
 if label=='red92':assert run.returncode!=0 and errors==4 and failures==skips==0
 else:assert run.returncode==0 and len(cases)==15 and errors==failures==skips==0
 results[label]={'head':sha,'exit_code':run.returncode,'testcases':len(cases),'errors':errors,'failures':failures,'skips':skips,'raw_source_pre_post':[before,after],'stdout_sha256':hashlib.sha256(run.stdout).hexdigest()}
result={'head':head,'tree':git(repo,'rev-parse',head+'^{tree}').decode().strip(),'base':old,'changed_paths':[path],'all_test_function_ASTs_unchanged':True,'test_functions':len(functions(head)),'cases':results,'scope':'ISOLATED_WINDOWS_SYNTHETIC_ASGI_GIT_FIXTURE_ONLY','hosted':'NOT_QUALIFIED','full_Grid_suite':'NOT_PASS_NOT_RERUN','admission_runtime':'UNCHANGED_NOT_QUALIFIED','physical':'BLOCKED','overall':'NO_GO'}
(out/'grid-fixture-review.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
