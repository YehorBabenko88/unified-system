"""Pure parser acceptance; no provider or network use."""
import hashlib,io,json,os,pathlib,subprocess
r=pathlib.Path(__file__).resolve().parents[1];repo=r/'work/review-grid-response9d71';out=r/'outputs/phase55';out.mkdir(exist_ok=True);head='9d71ee33b35048f5bb27875f5f81d151a1184c32'
def git(*a):return subprocess.check_output(['git','--no-replace-objects','-C',str(repo),*a])
assert git('rev-parse','HEAD').decode().strip()==head and git('rev-parse','HEAD^{tree}').decode().strip()=='8a05f8f6fe21f38328aeecd9a1c0288067003061';changes=git('diff','--name-status','HEAD^','HEAD').decode().splitlines();assert len(changes)==5 and all(x.startswith('A\t') for x in changes)
def identity():
 names=git('ls-tree','-r','--name-only',head).decode().splitlines();stream=io.BytesIO(subprocess.check_output(['git','--no-replace-objects','-C',str(repo),'cat-file','--batch'],input=''.join(head+':'+n+'\n' for n in names).encode()));result={}
 for name in names:
  oid,kind,size=stream.readline().split();assert kind==b'blob';raw=stream.read(int(size));assert stream.read(1)==b'\n' and raw==(repo/name).read_bytes();result[name]=hashlib.sha256(raw).hexdigest()
 assert not any(p.suffix.lower() in ('.pyc','.pyo') for p in repo.rglob('*') if p.is_file());return result
before=identity();profile='tests/fixtures/agent3-bybit-response/profile.json';inventory='tests/fixtures/agent3-bybit-response/test-inventory.json';assert before[profile]=='10a85b32e4f4485467bb5d74077d7efb40e9f23e033adcbfb64c2e04974b0921' and before[inventory]=='abaf41c29beb4476a89191ea7023fdfe9bfed87a9b1700c3b557897ac8aa515d'
script='''import sys,json,pathlib,pytest
repo=pathlib.Path(sys.argv[1]);out=pathlib.Path(sys.argv[2]);sys.path.insert(0,str(repo));inventory=json.loads((repo/'tests/fixtures/agent3-bybit-response/test-inventory.json').read_bytes());observed=[];skips=[]
class Recorder:
 def pytest_collection_modifyitems(self,items):assert sorted(x.nodeid for x in items)==sorted(inventory['nodeids']) and len(items)==44
 def pytest_runtest_logreport(self,report):
  if report.skipped:skips.append(report.nodeid)
  if report.when=='call':observed.append(dict(id=report.nodeid,outcome=report.outcome))
code=pytest.main(['-q','-o','addopts=','-p','no:cacheprovider','tests/test_bybit_response_advice.py','--junitxml='+str(out/'original.junit.xml')],plugins=[Recorder()]);assert code==0 and len(observed)==44 and not skips and all(x['outcome']=='passed' for x in observed)
(out/'exact44.json').write_text(json.dumps(dict(cases=observed,skips=skips,passed=True),indent=2),encoding='utf-8')
from grid.bybit_response_advice import parse_response_advice as parse,ResponseAdviceFormatError,PROFILE_SHA256
from unittest.mock import patch
body=lambda code=0,msg='OK':json.dumps(dict(retCode=code,retMsg=msg)).encode();extra=[]
invalid=[('duplicate_case_header',[['Date','Fri, 06 Nov 2026 12:00:00 GMT'],['DATE','Fri, 06 Nov 2026 12:00:00 GMT']],body()),('plus_seconds',[['Retry-After','+1']],body()),('unicode_digits',[['Retry-After','１']],body()),('control_header',[['Retry-After','1\\x00']],body()),('escaped_duplicate_body',[],b'{"retCode":0,"ret\\\\u0043ode":0,"retMsg":"OK"}'),('unicode_message',[],b'{"retCode":0,"retMsg":"\\\\u00e9"}'),('33members',[],json.dumps(dict(retCode=0,retMsg='OK',**{'k'+str(i):0 for i in range(31)})).encode())]
for name,headers,raw in invalid:
 try:parse('429',headers,raw)
 except ResponseAdviceFormatError:extra.append(dict(name=name,result='REJECTED'))
 else:raise AssertionError(name)
def forbidden(*a,**k):raise AssertionError('UNEXPECTED_IO_OR_CLOCK')
with patch('socket.socket',forbidden),patch('time.time',forbidden),patch('time.monotonic',forbidden):
 a=parse('403',[],body(10006,'different forbidden'));assert a.classification=='FORBIDDEN_AMBIGUOUS' and a.minimum_backoff_seconds is None;extra.append(dict(name='mixed403_UID_remains_ambiguous',result='PASS'))
 a=parse('429',[['Retry-After','900']],body(10006));assert a.classification=='HTTP_SYSTEM_FREQUENCY' and a.minimum_backoff_seconds=='900';extra.append(dict(name='system_priority_delta_increases_floor',result='PASS'))
 a=parse('403',[['Retry-After','0']],b'Access Too Frequent');assert a.minimum_backoff_seconds=='600' and a.session_action=='REQUIRE_HTTP_SESSION_CONTAINMENT';extra.append(dict(name='ban_floor_not_cleared_by_zero',result='PASS'))
 a=parse('429',[['Retry-After','Thu, 01 Jan 1970 00:00:00 GMT']],body());assert a.retry_after_http_date=='Thu, 01 Jan 1970 00:00:00 GMT' and a.minimum_backoff_seconds=='1';extra.append(dict(name='past_date_not_clock_resolved',result='PASS'))
 a=parse('200',[['X-Bapi-Limit','9007199254740991'],['X-Bapi-Limit-Status','9007199254740991']],body());assert a.authority_status=='UNTRUSTED_ADVICE_ONLY' and a.minimum_backoff_seconds is None and not any(hasattr(a,k) for k in ['permit','quota_delta','retry_at','ip_remaining']);extra.append(dict(name='max_remaining_not_permission',result='PASS'))
assert len(extra)==12;(out/'independent12.json').write_text(json.dumps(dict(cases=extra,skips=[],profile_sha256=PROFILE_SHA256,scope='PURE_ADVICE_NO_IO_CLOCK_AUTHORITY'),indent=2),encoding='utf-8')
'''
env=os.environ.copy();env.update(PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTHONDONTWRITEBYTECODE='1');p=subprocess.run([str(r/'work/audit-venv/Scripts/python.exe'),'-I','-B','-c',script,str(repo),str(out)],cwd=repo,env=env,capture_output=True,timeout=60);(out/'execution.stdout.log').write_bytes(p.stdout);(out/'execution.stderr.log').write_bytes(p.stderr);assert p.returncode==0,p.stderr.decode(errors='replace')[-2500:];assert before==identity()
report=dict(head=head,tree=git('rev-parse','HEAD^{tree}').decode().strip(),added_paths=changes,exact_tests=44,additional_cases=12,skips=0,primary_raw_files_before_after=len(before),profile_sha256=before[profile],inventory_sha256=before[inventory],network_or_provider_calls=0,qualification='PURE_UNTRUSTED_ADVICE_ONLY',provenance='PROJECTION_HASHES_NOT_SOURCE_OR_ATTEMPT_ATTESTATION',rate_enforcement=False,consumer_wiring=False,permission=False,clock_deadline=False,native_admission=False,overall='NO_GO_BROADER_ADMISSION')
(out/'independent-review.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
