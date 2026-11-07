"""Exact source fake-feed/SQL regression execution; forbid provider/real DB traffic."""
import ast,hashlib,io,json,os,pathlib,subprocess,uuid
r=pathlib.Path(__file__).resolve().parents[1];repo=r/'work/review-book268-1f08';out=r/'outputs/phase64';out.mkdir(exist_ok=True);head='1f08e24dd9f554e4c4dfa49fb3815345cf27044a';base='7a19ab40c30efef431bb16f0ddc91960608bf597';py=r.parent/'codex-agent-3-bybit-historical-live/work/test-venv/Scripts/python.exe'
def git(*a):return subprocess.check_output(['git','--no-replace-objects','-C',str(repo),*a])
changes=git('diff','--name-only',base,head).decode().splitlines();assert len(changes)==5 and git('rev-parse',head+'^{tree}').decode().strip()=='fe885700161e027b8e017b826c32dc06b0c904b4'
def assertions(ref):
 tree=ast.parse(git('show',ref+':tests/test_unified_features.py'));f=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='test_unified_features_merge_microstructure');return [ast.dump(n) for n in ast.walk(f) if isinstance(n,ast.Assert)]
assert assertions(base)==assertions(head)
def identity():
 names=git('ls-tree','-r','--name-only',head).decode().splitlines();stream=io.BytesIO(subprocess.check_output(['git','--no-replace-objects','-C',str(repo),'cat-file','--batch'],input=''.join(head+':'+n+'\n' for n in names).encode()));rows={}
 for name in names:
  oid,kind,size=stream.readline().split();assert kind==b'blob';raw=stream.read(int(size));assert stream.read(1)==b'\n' and raw==(repo/name).read_bytes();rows[name]=hashlib.sha256(raw).hexdigest()
 assert len(rows)==691 and not any(p.suffix in ('.pyc','.pyo') for p in repo.rglob('*') if p.is_file());return rows
before=identity();files=json.loads((r.parent/'codex-agent-3-bybit-historical-live/outputs/book-capability-regression-files.json').read_bytes());assert len(files)==53;temp=r/'work'/('book268-a8-temp-'+uuid.uuid4().hex[:8]);temp.mkdir(exist_ok=False)
script='''import sys,pathlib,json,ipaddress,pytest
repo=pathlib.Path(sys.argv[1]);out=pathlib.Path(sys.argv[2]);files=json.loads(sys.argv[3]);label=sys.argv[4];sys.path.insert(0,str(repo))
def no_external(event,args):
 if event in ('socket.connect','socket.bind'):
  endpoint=args[1]
  if not isinstance(endpoint,tuple) or not ipaddress.ip_address(endpoint[0]).is_loopback:raise AssertionError('A8_EXTERNAL_PROVIDER_DATABASE_FORBIDDEN')
sys.addaudithook(no_external);reports=[]
class Capture:
 def pytest_runtest_logreport(self,report):
  if report.when=='call' or report.skipped:reports.append(dict(id=report.nodeid,phase=report.when,outcome=report.outcome,detail=str(report.longrepr) if report.skipped else None))
rc=pytest.main(['-q','-o','addopts=','-p','no:cacheprovider','--junitxml='+str(out/(label+'.junit.xml')),*files],plugins=[Capture()]);assert rc==0
passed=[x for x in reports if x['phase']=='call' and x['outcome']=='passed'];skips=[x for x in reports if x['outcome']=='skipped']
if label=='focused40':assert len(passed)==40 and not skips
else:assert len(passed)==259 and len(skips)==1 and 'explicit disposable PG18 required' in skips[0]['detail']
(out/(label+'.json')).write_text(json.dumps(dict(label=label,passed=len(passed),skips=skips,cases=reports,scope='FAKE_FEED_FAKE_SQL_NO_REAL_PROVIDER_OR_DB',environment='BORROWED_A3_PY312_PYTEST835_NOT_NEWLY_QUALIFIED'),indent=2),encoding='utf-8')
'''
env={k:v for k,v in os.environ.items() if not k.startswith(('GRID_','BYBIT_','TERMINAN_')) and 'DSN' not in k and not k.startswith('PG')};env.update(PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTHONDONTWRITEBYTECODE='1',TEMP=str(temp),TMP=str(temp))
for label,selection in [('focused40',['tests/test_scientific_book_capability.py','tests/test_unified_features.py']),('broader259',files)]:
 p=subprocess.run([str(py),'-I','-B','-c',script,str(repo),str(out),json.dumps(selection),label],cwd=repo,env=env,capture_output=True,timeout=120);(out/(label+'.stdout.log')).write_bytes(p.stdout);(out/(label+'.stderr.log')).write_bytes(p.stderr);assert p.returncode==0,p.stderr.decode(errors='replace')[-2000:]
assert before==identity();report=dict(head=head,tree=git('rev-parse','HEAD^{tree}').decode().strip(),base=base,changed_paths=changes,positive_fixture_assertions_preserved=True,focused_passed=40,focused_skips=0,broader_passed=259,broader_skips=1,broader_contains_focused_not_additive=True,skip='EXPLICIT_DISPOSABLE_PG18_NOT_PROVISIONED_NO_WAIVER',raw_primary_files_before_after=691,provider_or_real_DB_connections=0,scope='LOCAL_SOURCE_BOUND_FAKE_FEED_SQL_ONLY',residual_gap='OPEN_NOT_CLOSED_BY_THIS_FIX',hosted='NOT_ADMITTED',overall='NO_GO_END_TO_END_L3_NATIVE_PHYSICAL')
(out/'exact-review.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
