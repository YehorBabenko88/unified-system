"""Independent bounded Meta historical gate cause and Stratt fail-closed review."""
import concurrent.futures,hashlib,json,os,pathlib,subprocess,sys,zipfile,xml.etree.ElementTree as ET
root=pathlib.Path(__file__).resolve().parents[1];out=root/'outputs/phase23';out.mkdir(exist_ok=True);a7=root.parent/'codex-agent-7-distributed-research-math/outputs';meta=root/'work/review7-meta_analyse';strat=root/'work/review7-strattester'
def git(repo,*args):return subprocess.check_output(['git','-C',str(repo),*args])
metasha='88b45c328bfdc8131ff0c6d139fddd8b27a4050c';stratsha='1722244f42d5d71a29b89bdec0e7211f2b723158';historic='fa487affd99310bd523f31f8c6935132a57e745a'
def identity(repo,sha):
 values=[]
 for row in git(repo,'ls-tree','-rz',sha).split(b'\0'):
  if not row:continue
  metadata,name=row.split(b'\t',1);mode,kind,oid=metadata.split();raw=(repo/name.decode()).read_bytes();assert kind==b'blob' and hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==oid.decode();values.append([name.decode(),hashlib.sha256(raw).hexdigest()])
 return hashlib.sha256(json.dumps(values).encode()).hexdigest()
before={name:identity(repo,sha) for name,repo,sha in [('Meta',meta,metasha),('Stratt',strat,stratsha)]}
def api(path):
 p=subprocess.run(['gh','api',path]+(['--allow-escape-sequences'] if path.endswith('/logs') else []),capture_output=True)
 if p.returncode:
  name=path.rsplit('/',2)[-2]+'-'+path.rsplit('/',1)[-1];(out/('api-error-'+name+'.json')).write_text(json.dumps({'path':path,'exit_code':p.returncode,'stderr':p.stderr.decode(errors='replace')},indent=2));return None
 return p.stdout
endpoints={'artifact':'repos/YehorBabenko88/meta_analyse/actions/artifacts/13247288810','old-job':'repos/YehorBabenko88/meta_analyse/actions/jobs/126034506020','current-job':'repos/YehorBabenko88/meta_analyse/actions/jobs/127988651137','stratt-system-job':'repos/YehorBabenko88/strattester/actions/jobs/128014993689','old-job-log':'repos/YehorBabenko88/meta_analyse/actions/jobs/126034506020/logs','current-job-log':'repos/YehorBabenko88/meta_analyse/actions/jobs/127988651137/logs'}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:responses=dict(zip(endpoints,executor.map(api,endpoints.values())))
fallback=[]
for name,raw in responses.items():
 if raw is None and name.endswith('job-log'):
  job=126034506020 if name=='old-job-log' else 127988651137
  raw=(a7/('original-meta-job-'+str(job)+'.log')).read_bytes();diagnosis=json.loads((a7/'meta-final-junit-source-diagnosis.json').read_text());expected=next(v['sha256'] for v in diagnosis['original_log_hashes'] if v['job']==job);assert hashlib.sha256(raw).hexdigest()==expected;responses[name]=raw;fallback.append(name)
 elif raw is None and name=='stratt-system-job':responses[name]=json.dumps({'status':'NOT_AVAILABLE_AT_READ_ONLY_LOOKUP','qualification':'NOT_ADOPTED'}).encode()
 elif raw is None:raise AssertionError('REQUIRED_PRIMARY_METADATA_UNAVAILABLE '+name)
for name,raw in responses.items():(out/(name+('.log' if name.endswith('log') else '.json'))).write_bytes(raw)
artifact=json.loads(responses['artifact']);zipraw=(a7/'original-meta-windows-test-evidence-41669712005.zip').read_bytes();assert len(zipraw)==artifact['size_in_bytes']==156375 and 'sha256:'+hashlib.sha256(zipraw).hexdigest()==artifact['digest']=='sha256:f64d9fccd4a8491ab49329f61a7bd47b65a20ca2daba315882ad1904d598bcbc'
with zipfile.ZipFile(__import__('io').BytesIO(zipraw)) as z:
 manifest=json.loads(z.read('manifest.json'))
 for name,sha in manifest['files'].items():assert hashlib.sha256(z.read(name)).hexdigest()==sha
 source=json.loads(z.read('source-sha.json'));assert source['sha']==source['expected_sha']==historic and source['tree_sha']=='b8651c3ac6d5149dd91b97b6070f22895a2cb996'
 xml=ET.fromstring(z.read('junit-001.xml'));cases=list(xml.iter('testcase'));skips=[c for c in cases if c.find('skipped') is not None];assert len(cases)==3019 and len(skips)==1
 pair=['tests.test_headless_service','test_untracked_index_record_spoof_cannot_replace_removed_index_entry'];opaque='case_'+hashlib.sha256((json.dumps(pair,sort_keys=True,separators=(',',':'))+'\n').encode()).hexdigest();assert skips[0].get('name')==opaque
 (out/'historical-public-junit.xml').write_bytes(z.read('junit-001.xml'));(out/'historical-artifact-source.json').write_text(json.dumps(source,indent=2))
for p in ['scripts/check_final_integration_junit.py','scripts/project_public_ci_evidence.py']:assert git(meta,'show',historic+':'+p)==git(meta,'show',metasha+':'+p)
for ref in ['9be00e56922d1fba0583df6a32083ffcc29900c2','4963ccdbe34de7eb798d06ccb64a91bf64f77178']:subprocess.run(['git','-C',str(meta),'merge-base','--is-ancestor',ref,'2c4db055e56e36384a2661d443f9abc7b2331e90'],check=True)
oldlog=responses['old-job-log'].decode(errors='replace');newlog=responses['current-job-log'].decode(errors='replace');assert '3018 passed, 1 skipped' in oldlog and 'FINAL_INTEGRATION_JUNIT_REJECTED' in oldlog;assert '3122 passed, 1 skipped' in newlog and 'exact synthetic JUnit identities=3123' in newlog
oldjob=json.loads(responses['old-job']);newjob=json.loads(responses['current-job']);assert oldjob['head_sha']==historic and oldjob['conclusion']=='failure';assert newjob['head_sha']==metasha and newjob['conclusion']=='success'
# Reproduce actual collection hook once, with fake single collected item and Git facts.
sys.path.insert(0,str(meta));from unittest.mock import patch
from scripts.check_final_integration_junit import check
class Item:nodeid='tests/test_headless_service.py::test_untracked_index_record_spoof_cannot_replace_removed_index_entry';name=pair[1]
class Session:items=[Item()]
causal=[]
for label,ref in [('historical',historic),('current',metasha)]:
 namespace={'__name__':'a8_hook_'+label,'__file__':str(meta/'scripts/integration_synthetic_boundary.py')};exec(compile(git(meta,'show',ref+':scripts/integration_synthetic_boundary.py'),namespace['__file__'],'exec'),namespace)
 target=out/(label+'-one-case-manifest.json')
 with patch.dict(os.environ,{'META_ANALYSE_SYNTHETIC_IDENTITIES':str(target),'META_ANALYSE_CI_IDENTITY_SCOPE':'full'}),patch('subprocess.check_output',side_effect=lambda cmd,**kw:((metasha if cmd[-1]=='HEAD' else '83304074f9cc3f90c09615c7f6920e1a07eab0c6')+'\n')):
  namespace['pytest_collection_finish'](Session())
 m=json.loads(target.read_text());raw=('<testsuite><testcase classname="'+pair[0]+'" name="'+pair[1]+'"><skipped message="Windows forbids TAB in filenames"/></testcase></testsuite>').encode()
 try:count=check(raw,m,metasha,'83304074f9cc3f90c09615c7f6920e1a07eab0c6');outcome='ACCEPTED'
 except ValueError:count=None;outcome='REJECTED'
 assert outcome==('REJECTED' if label=='historical' else 'ACCEPTED');causal.append({'producer':label,'outcome':outcome,'count':count,'allowed_skips':m['allowed_skips']})
# Independently validate current pure parser/platform guards, no full suite or native code.
boot="import sys,socket;sys.path[:0]="+repr([str(meta),str(meta/'src')])+";socket.socket.connect=lambda *a,**k:(_ for _ in ()).throw(RuntimeError('AUDITOR_NETWORK_DENIED'));import pytest;raise SystemExit(pytest.main("+repr(['--noconftest','-q','--import-mode=importlib','-p','no:cacheprovider','--basetemp='+str(root/'work/meta-gate-a8-cases'),'--junitxml='+str(out/'meta-guards.xml'),'tests/test_final_integration_junit.py','tests/test_platform_coverage.py'])+"))"
env=os.environ.copy();env.update(PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTHONDONTWRITEBYTECODE='1')
p=subprocess.run([str(root/'work/audit-venv/Scripts/python.exe'),'-I','-B','-c',boot],cwd=meta,env=env,capture_output=True,timeout=60);(out/'meta-guards.stdout.log').write_bytes(p.stdout);(out/'meta-guards.stderr.log').write_bytes(p.stderr);assert p.returncode==0
tests=ET.parse(out/'meta-guards.xml');assert len(tests.findall('.//testcase'))==48 and not tests.findall('.//skipped') and not tests.findall('.//failure') and not tests.findall('.//error')
# Forged all-green engineering/external claims must not clear Stratt system gate.
sys.path.insert(0,str(strat));from strattester.research.financial_acceptance import aggregate,MANDATORY_EXTERNAL
specs=json.loads((strat/'scripts/financial-gate-manifest.json').read_text());reports={name:dict(schema=1,sha=stratsha,gate=name,status='PASS',exit_code=0,passed=len(spec['nodeids']),failed=0,errors=0,skipped=0,xfailed=0,xpassed=0,deselected=0,collected=len(spec['nodeids']),nodeids=spec['nodeids']) for name,spec in specs.items()}
blocked=aggregate(reports,stratsha,set(specs),external={n:'PASS' for n in MANDATORY_EXTERNAL});assert blocked['status']=='BLOCKED' and not blocked['failed'] and set(blocked['external'].values())=={'BLOCKED'}
from strattester.research.grid_producer_readiness import require_native_grid_export,NativeGridExportBlocked
try:require_native_grid_export()
except NativeGridExportBlocked:export='BLOCKED_BEFORE_IO'
else:raise AssertionError('NATIVE_EXPORT_ADMITTED')
(out/'stratt-forged-all-pass.json').write_text(json.dumps(blocked,indent=2))
after={name:identity(repo,sha) for name,repo,sha in [('Meta',meta,metasha),('Stratt',strat,stratsha)]};assert before==after
report={'Meta_head':metasha,'Stratt_head':stratsha,'raw_git_source_pre_post':[before,after],'artifact_sha256_matches_primary_API':True,'artifact_members_hash_verified':len(manifest['files']),'historical_JUnit_cases':3019,'historical_skipped_identity':opaque,'historical_failure':'COLLECTION_PRODUCER_OMITS_EXISTING_PLATFORM_SKIP_NOT_PARSER_FAILURE','parser_projector_unchanged':True,'fix_ancestors_of_approved_base':True,'causal_single_case':causal,'current_meta_guard_tests':48,'guard_skips':0,'current_windows_job_success_verified':127988651137,'current_windows_source':metasha,'current_job_JUnit_accounting':'3122PASS_1EXISTING_PLATFORM_SKIP_3123IDENTITIES','log_api_fallbacks_to_hash_verified_retained_original':fallback,'full_meta_workflow_acceptance':'NOT_QUALIFIED','Stratt_all_pass_claims':'BLOCKED_7EXTERNAL_FACTS_UNIMPLEMENTED','Stratt_native_export':export,'Stratt_system_acceptance':'BLOCKED','A7_P0_labels':'NOT_ADOPTED_AS_NEW_A8_CONFIRMED_DEFECTS','scope':'SELECTED_ORIGINAL_EVIDENCE_PURE_GUARDS_AND_SOURCE_ONLY','physical':'BLOCKED','overall':'NO_GO'}
(out/'gate-diagnosis-review.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
