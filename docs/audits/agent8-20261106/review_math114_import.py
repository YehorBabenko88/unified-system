"""Math114 preparation-only argv/import review; no native Main/backend/activation."""
import concurrent.futures,hashlib,json,os,pathlib,re,subprocess,uuid
r=pathlib.Path(__file__).resolve().parents[1];seed=r/'work/review-math113-label';out=r/'outputs/phase36';out.mkdir(exist_ok=True);old='dbb9bb1da9b180a8bb9f1d5401f1117894256941';head='9f08b237b9d0a47abfb03ee4741c7f1688081fbd';tree='94e3a3fc112b18e8ca633cb3aeadbb9837213af5'
def git(repo,*args):return subprocess.check_output(['git','--no-replace-objects','-C',str(repo),*args])
def read(sha,path):return git(seed,'show',sha+':'+path)
metadata=subprocess.check_output(['gh','pr','view','114','--repo','YehorBabenko88/math','--json','headRefOid,baseRefOid,isDraft,files,url']);(out/'primary-pr114.json').write_bytes(metadata);pr=json.loads(metadata);assert pr['headRefOid']==head and pr['baseRefOid']==old and pr['isDraft']
assert git(seed,'rev-parse',head+'^{tree}').decode().strip()==tree
assert set(git(seed,'diff','--name-only',old,head).decode().splitlines())=={'docs/audits/agent7-verifier-import-evidence.json','scripts/agent7-loader-init/build.ps1','tests/agent7-replay-research.test.mjs'}
for path in ['scripts/verify-source-identity.mjs','scripts/adminit-containment/build-hosted.ps1','.github/workflows/agent7-loader-init-diagnostic.yml','scripts/platform-source-proof.json','scripts/platform-test-inventory.json']:
 # The workflow's exact basename is discovered below if not this name.
 if path=='.github/workflows/agent7-loader-init-diagnostic.yml':continue
 assert read(old,path)==read(head,path),path
changed=git(seed,'diff','--name-only',old,head,'--','.github','*.cs','*.cpp','*.h','*.c').strip();assert not changed
proof=json.loads(read(head,'scripts/platform-source-proof.json'));assert len(proof['testFiles'])==188
for item in proof['testFiles']:
 raw=b''.join(read(head,x['path'])[x['start']:x['end']] for x in proof['recipes'][item['path']]);assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256'];assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==item['blob']
repo=r/'work'/('review-math114-'+uuid.uuid4().hex[:8]);subprocess.run(['git','clone','--no-hardlinks','--no-checkout',str(seed),str(repo)],check=True,capture_output=True);subprocess.run(['git','-C',str(repo),'-c','core.autocrlf=false','-c','core.eol=lf','checkout','--detach',head],check=True,capture_output=True);assert (repo/'.git').is_dir() and not (repo/'.git/objects/info/alternates').exists()
def identity():
 rows={}
 for item in filter(None,git(repo,'ls-tree','-rz',head).split(b'\0')):
  meta,name=item.split(b'\t',1);raw=(repo/name.decode()).read_bytes();assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==meta.split()[2].decode();rows[name.decode()]=hashlib.sha256(raw).hexdigest()
 return dict(files=len(rows),sha256=hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest())
before=identity();temp=r/'work'/('math114-temp-'+uuid.uuid4().hex[:8]);temp.mkdir();env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')};env.update(TEMP=str(temp),TMP=str(temp))
def ps(label,reference):
 builder=read(reference,'scripts/agent7-loader-init/build.ps1').decode();verify=re.search(r"^\$verify='.*'$",builder,re.M).group();beforeline=re.search(r'^\$before=& node .*$',builder,re.M).group();afterline=re.search(r'^\$after=& node .*$',builder,re.M).group()
 script="$ProgressPreference='SilentlyContinue';$ErrorActionPreference='Stop';$ExpectedHead=$env:A8_MATH_HEAD;$validator=$env:A8_MATH_VALIDATOR;"+verify+'\n'+beforeline+"\nif($LASTEXITCODE -ne 0){exit $LASTEXITCODE};\n"+afterline+"\nif($LASTEXITCODE -ne 0){exit $LASTEXITCODE};if($before -cnotmatch '^[a-f0-9]{64}$' -or $after -cne $before){throw 'SOURCE_IMPORT_HASH_MISMATCH'};Write-Output ('SOURCE_IMPORT_ONLY '+$before)"
 import base64
 e=dict(env,A8_MATH_HEAD=head,A8_MATH_VALIDATOR=str(repo/'scripts/verify-source-identity.mjs'));p=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-EncodedCommand',base64.b64encode(script.encode('utf-16le')).decode()],cwd=repo,env=e,capture_output=True,timeout=45,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));(out/(label+'.stdout.log')).write_bytes(p.stdout);(out/(label+'.stderr.log')).write_bytes(p.stderr);return p
red=ps('actual-old-import-RED',old);assert red.returncode!=0 and b'CLI_ARGUMENTS_REJECTED' in red.stderr
green=ps('actual-fixed-import-GREEN',head);assert green.returncode==0 and b'SOURCE_IMPORT_ONLY' in green.stdout and not green.stderr
path=repo/'scripts/agent7-loader-init/build.ps1';original=path.read_bytes();path.write_bytes(original+b'\n# A8 hidden source negative\n');subprocess.run(['git','-C',str(repo),'update-index','--assume-unchanged','scripts/agent7-loader-init/build.ps1'],check=True)
try:dirty=ps('actual-fixed-hidden-dirty',head);assert dirty.returncode!=0 and b'SOURCE_IMPORT_ONLY' not in dirty.stdout
finally:path.write_bytes(original);subprocess.run(['git','-C',str(repo),'update-index','--no-assume-unchanged','scripts/agent7-loader-init/build.ps1'],check=True)
tests=subprocess.run(['node','--test','--test-reporter=tap','tests/agent7-replay-research.test.mjs','tests/math-module-diagnostics.cross.mjs'],cwd=repo,env=env,capture_output=True,timeout=120);(out/'node-pure-tests.stdout.log').write_bytes(tests.stdout);(out/'node-pure-tests.stderr.log').write_bytes(tests.stderr);assert tests.returncode==0 and b'# tests 13' in tests.stdout and b'# pass 13' in tests.stdout and b'# fail 0' in tests.stdout and b'# skipped 0' in tests.stdout
after=identity();assert before==after
endpoints={'run':'actions/runs/42274233717','jobs':'actions/runs/42274233717/jobs','artifacts':'actions/runs/42274233717/artifacts','original-job-log':'actions/jobs/128086308505/logs'}
def api(item):
 name,path=item;p=subprocess.run(['gh','api','repos/YehorBabenko88/math/'+path]+(['--allow-escape-sequences'] if name.endswith('log') else []),capture_output=True);assert p.returncode==0;(out/('primary-'+name+('.log' if name.endswith('log') else '.json'))).write_bytes(p.stdout);return name,p.stdout
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:responses=dict(pool.map(api,endpoints.items()))
run=json.loads(responses['run']);jobs=json.loads(responses['jobs']);artifacts=json.loads(responses['artifacts']);assert run['run_attempt']==1 and run['head_sha']==old and run['conclusion']=='failure' and artifacts['total_count']==0
log=responses['original-job-log'];assert hashlib.sha256(log).hexdigest()=='b9adfb67c712b3fa9394c2b786d1b2951301755541cba0bf4462e0aeb4547b29' and b'CLI_ARGUMENTS_REJECTED' in log
steps=jobs['jobs'][0]['steps'];assert any(step['conclusion']=='skipped' and 'owned-child observation' in step['name'].lower() for step in steps)
report=dict(head=head,tree=tree,base=old,changed_paths=3,source_verifier_original_builder_workflows_and_native_sources_unchanged=True,original188reconstructed_files_verified=True,inventory_bytes_unchanged=True,raw_before=before,raw_after=after,powershell_actual_unchanged_verifier=dict(old_red=red.returncode,fixed_green=green.returncode,hidden_dirty_rejected=dirty.returncode,scope='IMPORT_BEFORE_AFTER_ONLY_NO_BUILDER_EXECUTION'),node_model_pure_cases=13,skips=0,node_version=subprocess.check_output(['node','--version']).decode().strip(),original_run=dict(id=42274233717,attempt=1,conclusion='failure',original_raw_log_hash_verified=True,artifacts=0,native_observation_skipped=True),activation='NONE_BY_A8_NO_RERUN_RELABEL_CANCEL_OR_NEW_AUTHORIZATION',native_Main_backend='NOT_RUN',new_authorization_required=True,qualification='PREPARATION_CODE_AND_MODEL_ONLY',overall='NO_GO')
(out/'math114-import-review.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
