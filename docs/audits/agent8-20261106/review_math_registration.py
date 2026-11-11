"""Bounded independent exact-source review of Math PR112 registration correction."""
import hashlib, io, json, pathlib, subprocess
root=pathlib.Path(__file__).resolve().parents[1]
repo=root/'work/review7-math-917'; out=root/'outputs/phase10';out.mkdir(exist_ok=True)
head='917d99672e37db59835a8ab23b03c99826b12d78'; old='5f93cf91acc04c6561da2e940cad87f9ac41baf2';base='5721987a15d20c3f9984d52eac4446704566d4b9'
def git(*args):return subprocess.check_output(['git','-C',str(repo),*args])
def blob(sha,path):return git('show',sha+':'+path)
def identity():
 rows=[]
 for row in git('ls-tree','-rz',head).split(b'\0'):
  if not row:continue
  meta,name=row.split(b'\t');mode,kind,oid=meta.split();data=(repo/name.decode()).read_bytes()
  assert kind==b'blob' and hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==oid.decode(),name
  rows.append([name.decode(),hashlib.sha256(data).hexdigest()])
 return hashlib.sha256(json.dumps(rows).encode()).hexdigest()
assert git('rev-parse','HEAD').decode().strip()==head
before=identity()
oldinv=json.loads(blob(old,'scripts/platform-test-inventory.json'));newinv=json.loads(blob(head,'scripts/platform-test-inventory.json'))
stripped=json.loads(json.dumps(newinv));extras=stripped['tests'][-8:]
for entry in extras:assert entry.pop('added') is True
assert stripped==oldinv
baseline=json.loads(blob(base,'scripts/platform-test-inventory.json'))
assert newinv['tests'][:len(baseline['tests'])]==baseline['tests']
proof=json.loads(blob(head,'scripts/platform-source-proof.json'))
assert blob(head,'scripts/platform-source-proof.json')==blob(old,'scripts/platform-source-proof.json')
for original in proof['testFiles']:
 data=b''.join(blob(head,p['path'])[p['start']:p['end']] for p in proof['recipes'][original['path']])
 assert len(data)==original['bytes'] and hashlib.sha256(data).hexdigest()==original['sha256']
 assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==original['blob']
assert blob(head,'tests/adminit-loader-facts.windows.mjs')==blob(old,'tests/adminit-loader-facts.windows.mjs')
p=subprocess.run(['node','--test','--test-reporter=tap','tests/platform-coverage.test.mjs','tests/agent7-replay-research.test.mjs'],cwd=repo,capture_output=True,timeout=60)
(out/'math-registration.tap.log').write_bytes(p.stdout);(out/'math-registration.stderr.log').write_bytes(p.stderr)
assert p.returncode==0 and b'# tests 13' in p.stdout and b'# pass 13' in p.stdout and b'# skipped 0' in p.stdout
after=identity();assert before==after
paths=git('diff','--name-only',base,head).decode().splitlines()
assert set(paths)=={'tests/agent7-replay-research.test.mjs','tests/adminit-loader-facts.windows.mjs','tests/platform-coverage.test.mjs','scripts/platform-source-proof.json','scripts/platform-test-inventory.json','docs/audits/agent7-research-regressions.json'}
result={'head':head,'tree':git('rev-parse','HEAD^{tree}').decode().strip(),'base':base,'previous_reviewed_head':old,'changed_paths':paths,'source_raw_git_pre_post':[before,after],'original_reconstructed_files':len(proof['testFiles']),'original_inventory_unchanged':True,'only_inventory_change':'added:true on exactly 8 added cases','tests':13,'pass':13,'skip':0,'log_sha256':hashlib.sha256(p.stdout).hexdigest(),'environment':'Windows Node '+subprocess.check_output(['node','--version']).decode().strip()+' exact LF isolated clone','linux_execution':'NOT_RUN_BY_A8','hosted_ci':'NOT_QUALIFIED','native_launch':'NOT_RUN_UNRESOLVED','physical':'BLOCKED','overall':'NO_GO'}
(out/'math-registration-review.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
