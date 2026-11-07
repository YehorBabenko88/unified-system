"""Independent pending-plan review only; never probes or changes office hosts."""
import copy,hashlib,io,json,pathlib,subprocess,sys,unittest,uuid
r=pathlib.Path(__file__).resolve().parents[1];seed=r/'work/unified-audit';out=r/'outputs/phase47';out.mkdir(exist_ok=True)
head='c5105298a856b8549953ee1cf815b5392cc3afc7';amend='69d3ae08659e031b5d0393a15f4cfa816bc42a42';repo=r/'work'/('review-home-'+uuid.uuid4().hex[:8])
def git(where,*args):return subprocess.check_output(['git','--no-replace-objects','-C',str(where),*args])
subprocess.run(['git','clone','--no-hardlinks','--no-checkout',str(seed),str(repo)],check=True,capture_output=True);subprocess.run(['git','-C',str(repo),'-c','core.autocrlf=false','-c','core.eol=lf','checkout','--detach',head],check=True,capture_output=True)
def identity():
 paths=[];oids={}
 for row in git(repo,'ls-tree','-rz',head).split(b'\0'):
  if row:
   meta,name=row.split(b'\t',1);mode,kind,oid=meta.split();assert mode==b'100644' and kind==b'blob';paths.append(name.decode());oids[name.decode()]=oid.decode()
 stream=io.BytesIO(subprocess.check_output(['git','--no-replace-objects','-C',str(repo),'cat-file','--batch'],input=''.join(oids[n]+'\n' for n in paths).encode()));result={}
 for name in paths:
  oid,kind,size=stream.readline().split();raw=stream.read(int(size));assert stream.read(1)==b'\n' and raw==(repo/name).read_bytes();result[name]=hashlib.sha256(raw).hexdigest()
 return result
before=identity();sys.path.insert(0,str(repo))
from unified_system.windows_qualification import review_matrix,QualificationError,CHECKS
matrix=json.loads((repo/'release/windows-edition-qualification.json').read_bytes());decision=(repo/'release/decisions/windows-home-20261107/OWNER-DECISION.json').read_bytes();d=json.loads(decision)
assert hashlib.sha256(decision).hexdigest()==matrix['decision_raw_sha256'];assert hashlib.sha256((repo/'release/decisions/windows-home-20261107/OWNER-DECISION.md').read_bytes()).hexdigest()==d['owner_text_raw_sha256']
assert d['allowed_roles']==['WORKER','TERMINAN'] and d['coordinators']==['LS5','PC4','PC3'] and not d['pro_required_for_all_workers']
assert d['os_upgrade']=='NOT_AUTHORIZED' and d['security_policy_firewall_eset_tailscale_changes']=='NOT_AUTHORIZED'
for track in matrix['tracks'].values():
 for node,row in track['nodes'].items():assert len(row['checks'])==14 and all(c['status']=='NOT_RUN' and c['evidence']==[] for c in row['checks'])
suite=unittest.defaultTestLoader.discover(str(repo/'tests'),pattern='test_windows_qualification.py');log=io.StringIO();res=unittest.TextTestRunner(stream=log,verbosity=2).run(suite);(out/'six-unit-tests.log').write_text(log.getvalue(),encoding='utf-8');assert res.wasSuccessful() and res.testsRun==6 and not res.skipped
cases=[]
def reject(name,v):
 try:review_matrix(v)
 except QualificationError:cases.append(name)
 else:raise AssertionError('UNEXPECTED_ACCEPT:'+name)
home='WINDOWS_HOME_QUALIFICATION'
for node in ['PC1','LS7']:
 for index,check in enumerate(matrix['tracks'][home]['nodes'][node]['checks']):
  v=copy.deepcopy(matrix);v['tracks'][home]['nodes'][node]['checks'][index].update(status='PASS',evidence=[dict(node='LS5',edition='Windows Server',ci='PASS')]);reject(node+'_'+check['id']+'_FOREIGN_PASS',v)
 for field,value in [('role','COORDINATOR'),('edition','Windows 11 Pro'),('physical_deployment','AUTHORIZED')]:
  v=copy.deepcopy(matrix);v['tracks'][home]['nodes'][node][field]=value;reject(node+'_'+field,v)
 for change in ['missing','duplicate']:
  v=copy.deepcopy(matrix);checks=v['tracks'][home]['nodes'][node]['checks']
  if change=='missing':checks.pop()
  else:checks[-1]=copy.deepcopy(checks[0])
  reject(node+'_'+change,v)
for track in matrix['tracks']:
 for field,value in [('status','PASS'),('pass_inheritance','ALLOWED')]:
  v=copy.deepcopy(matrix);v['tracks'][track][field]=value;reject(track+'_'+field,v)
v=copy.deepcopy(matrix);v['tracks']['WINDOWS_SERVER_QUALIFICATION']={};reject('EXTRA_SERVER_TRACK',v)
result=review_matrix(matrix);assert not result['runtime_qualified'] and not result['physical_deployment_authorized'] and result['pending_home_checks']==28
assert before==identity()
inventory=json.loads((repo/'release/component-test-inventory.json').read_bytes());ids=inventory['expected_test_ids'];prior=inventory['preserved_prior_ids'];assert inventory['expected_count']==143 and len(ids)==len(set(ids))==143 and len(prior)==len(set(prior))==137 and set(prior)<=set(ids)
assert len([n for n in ids if 'WindowsQualificationTests.' in n])==6
assert not git(seed,'diff','--name-only',head,amend,'--','unified_system/windows_qualification.py','tests/test_windows_qualification.py','release/windows-edition-qualification.json','release/decisions/windows-home-20261107')
amend_path='release/directives/20261107/SECTION8-WINDOWS-EDITION-AMENDMENT.md';raw=git(seed,'show',amend+':'+amend_path);(out/'amendment.original.md').write_bytes(raw)
for path in ['release/windows-edition-qualification.json','release/decisions/windows-home-20261107/OWNER-DECISION.json','release/decisions/windows-home-20261107/OWNER-DECISION.md']:(out/path.split('/')[-1]).write_bytes((repo/path).read_bytes())
report=dict(requirement='WINDOWS_EDITION_ROLE_CLAIM_GUARDS',repository='unified-system',pr='ROOT_INTEGRATION_BRANCH_NO_PR_ASSERTED',head=head,tree=git(repo,'rev-parse',head+'^{tree}').decode().strip(),amendment=amend,amendment_tree=git(seed,'rev-parse',amend+'^{tree}').decode().strip(),amendment_raw_sha256=hashlib.sha256(raw).hexdigest(),environment='ISOLATED_SOURCE_MODEL_NO_HOST_PROBES',unit_tests=6,independent_negative_cases=cases,skips=0,raw_files_before_after=len(before),raw_manifest_sha256=hashlib.sha256(json.dumps(before,sort_keys=True).encode()).hexdigest(),matrix= result,home_nodes_each_14='ALL_NOT_RUN_EMPTY_EVIDENCE',source_guard_result='PASS_SOURCE_MODEL_ONLY',owner_authority='TRANSCRIPTION_HASH_BOUND_NOT_INDEPENDENTLY_AUTHENTICATED_ORIGINAL_MESSAGE',windows_ci='NOT_EVALUATED_BY_THIS_REVIEW',home_runtime='NOT_RUN_NOT_QUALIFIED',physical='BLOCKED',tailscale_removal='BLOCKED',overall='NO_GO')
(out/'independent-review.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
