"""Bounded amended label guard audit; no labels, dispatches or native Main."""
import base64,hashlib,json,os,pathlib,re,subprocess
root=pathlib.Path(__file__).resolve().parents[1];repo=root/'work/review-math113-label';out=root/'outputs/phase18';out.mkdir(exist_ok=True)
head='dbb9bb1da9b180a8bb9f1d5401f1117894256941';previous='40c158797dd22581ae20dea03b2aa9f06dda8042'
def git(*args):return subprocess.check_output(['git','-C',str(repo),*args])
assert set(git('diff','--name-only',previous,head).decode().splitlines())=={'.github/workflows/agent7-loader-init-trace.yml','tests/agent7-replay-research.test.mjs'}
def identity():
 values=[]
 for row in git('ls-tree','-rz',head).split(b'\0'):
  if not row:continue
  meta,name=row.split(b'\t',1);mode,kind,oid=meta.split();raw=(repo/name.decode()).read_bytes();assert kind==b'blob' and hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==oid.decode();values.append([name.decode(),hashlib.sha256(raw).hexdigest()])
 return hashlib.sha256(json.dumps(values).encode()).hexdigest()
before=identity();workflow=(repo/'.github/workflows/agent7-loader-init-trace.yml').read_text();admission=re.search(r'# BEGIN_PURE_EVENT_ADMISSION\n([\s\S]*?)\s+# END_PURE_EVENT_ADMISSION',workflow)[1]
assert 'types: [labeled]' in workflow and not re.search(r'workflow_dispatch:|pull_request_target:|^  push:',workflow,re.M)
assert 'ref: ${{ env.SOURCE_HEAD }}' in workflow and 'persist-credentials: false' in workflow and 'cancel-in-progress: false' in workflow
good=dict(eventName='pull_request',action='labeled',actor='YehorBabenko88',triggeringActor='YehorBabenko88',attempt='1',repository='YehorBabenko88/math',pr=113,branch='agent7/math-loader-init-diagnostics-20261106',base='agent7/math-native-research-20261106',headRepo='YehorBabenko88/math',baseRepo='YehorBabenko88/math',head='b'*40,eventSha='a'*40,label='diag-'+'b'*40,description='review-sha256:'+'c'*64)
vectors=[dict(name='valid_distinct_source_event',value=good,accept=True)]
mutations=dict(eventName='workflow_dispatch',action='synchronize',actor='other',triggeringActor='other',attempt='2',repository='other/math',pr=112,branch='main',base='main',headRepo='other/math',baseRepo='other/math',head='B'*40,eventSha='nothex',label='diag-'+'d'*40,description='review-sha256:bad')
for key,value in mutations.items():vectors.append(dict(name='wrong_'+key,value={**good,key:value},accept=False))
for key in good:vectors.append(dict(name='missing_'+key,value={k:v for k,v in good.items() if k!=key},accept=False))
for key,value in [('description',good['description']+'\n'),('head',good['head']+'\n'),('eventSha',good['eventSha']+'\n'),('label',good['label']+'\n'),('actor','yehorbabenko88'),('action','opened'),('action','reopened'),('action','unlabeled')]:vectors.append(dict(name='extra_'+key+'_'+str(len(vectors)),value={**good,key:value},accept=False))
ps="$ErrorActionPreference='Stop';"+admission+"\n$v=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($env:A8_VECTORS))|ConvertFrom-Json;$n=0;foreach($x in $v){$ok=$false;try{$r=Admit-TraceEvent $x.value;$ok=$true}catch{};if($ok -ne $x.accept){throw ('A8_EVENT_FAIL '+$x.name)};if($ok -and ($r.SourceHead -cne $x.value.head -or $r.EventSha -cne $x.value.eventSha -or $r.ReviewRecordSha256 -cne ('c'*64))){throw 'A8_RECEIPT_FAIL'};$n++};Write-Output ('A8_PURE_EVENTS cases='+$n+' nativeInvocations=0')"
env=os.environ.copy();env['A8_VECTORS']=base64.b64encode(json.dumps(vectors).encode()).decode()
run=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-EncodedCommand',base64.b64encode(ps.encode('utf-16le')).decode()],env=env,capture_output=True,timeout=30)
(out/'events.stdout.log').write_bytes(run.stdout);(out/'events.stderr.log').write_bytes(run.stderr);assert run.returncode==0
(out/'event-vectors.json').write_text(json.dumps(vectors,indent=2))
run=subprocess.run(['node','--test','--test-reporter=tap','tests/platform-coverage.test.mjs','tests/agent7-replay-research.test.mjs'],cwd=repo,capture_output=True,timeout=60)
(out/'tests.tap.log').write_bytes(run.stdout);(out/'tests.stderr.log').write_bytes(run.stderr);assert run.returncode==0 and b'# pass 13' in run.stdout and b'# skipped 0' in run.stdout
after=identity();assert before==after
code="import {verifySourceIdentity} from './scripts/verify-source-identity.mjs';console.log(JSON.stringify(verifySourceIdentity(process.argv[1])));"
source=json.loads(subprocess.check_output(['node','--input-type=module','-e',code,head],cwd=repo));assert source['trackedSourceSha256']=='c85eb764dadd085833b6b4df98da52d3f9e474fc164cd0c149ce0b1e93c3643e'
report={'head':head,'tree':git('rev-parse','HEAD^{tree}').decode().strip(),'previous_reviewed_head':previous,'base':'917d99672e37db59835a8ab23b03c99826b12d78','delta':'TWO_APPROVED_WORKFLOW_TEST_PATHS_ONLY_NATIVE_CODE_UNCHANGED','raw_git_pre_post':[before,after],'source_identity':source,'tests':13,'pass':13,'skip':0,'independent_pure_event_vectors':len(vectors),'native_invocations':0,'activation':'NOT_RUN_NO_LABEL_CREATED_OR_APPLIED','A8_review':'FRESH_SOURCE_MODEL_ACK_ONE_NONQUALIFYING_HOSTED_OBSERVATION_ONLY','prior_ACK_transfer':False,'ROOT_concrete_activation_authorization':'REQUIRED_SEPARATE_PENDING','residual_controls':'Exact current head/tree and actual event workflow source must be verified by ROOT at activation; label digest is reference only; concurrency is not durable one-shot authorization; no automatic relabel/rerun after UNKNOWN.','native_acceptance':'BLOCKED','physical':'BLOCKED','overall':'NO_GO'}
(out/'label-amendment-review.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
