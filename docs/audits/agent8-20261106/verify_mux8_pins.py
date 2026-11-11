import hashlib,json,pathlib,subprocess
r=pathlib.Path(__file__).resolve().parents[1];repo=r/'work/unified-audit';out=r/'outputs/phase49';out.mkdir(exist_ok=True);old='5fd0ccbd28c79fb5ff040ecb1030462ac4baef35';new='08d6f01d94feb44a17338be8ef3f8871995c284a'
def git(*a):return subprocess.check_output(['git','--no-replace-objects','-C',str(repo),*a])
raw=(r.parent/'codex-agent-2-high-availability-distributed/outputs/CONTROL-MUX-08D6F01-UNCHANGED-PRODUCT-PINS.json').read_bytes();claim=json.loads(raw);changed=git('diff','--name-only',old,new).decode().splitlines();assert changed==claim['changed_paths'] and len(changed)==4
rows=[]
for name,expected in claim['unchanged_raw_sha256'].items():
 a=git('show',old+':'+name);b=git('show',new+':'+name);assert a==b and hashlib.sha256(b).hexdigest()==expected;rows.append(dict(path=name,raw_sha256=expected,primary_blob=git('rev-parse',new+':'+name).decode().strip()))
assert len(rows)==10
owner=(r.parent/'codex-agent-2-high-availability-distributed/outputs/CONTROL-MUX-RUNTIME-08D6F01-EVIDENCE.json').read_bytes();assert hashlib.sha256(owner).hexdigest()=='bf47e5e8f0ed3fb74ee90fcaea461c248f6c8aa0e4f2bdb938040109239d7bca'
ci=[]
for run in [42350749074,42350745758]:
 p=subprocess.run(['gh','api','repos/YehorBabenko88/unified-system/actions/runs/'+str(run)],capture_output=True,check=True);(out/('ci-'+str(run)+'.original.json')).write_bytes(p.stdout);d=json.loads(p.stdout);assert d['head_sha']==new;ci.append({k:d.get(k) for k in ['id','head_sha','run_attempt','status','conclusion','event','html_url']})
report=dict(old_head=old,new_head=new,tree=git('rev-parse',new+'^{tree}').decode().strip(),changed_paths=changed,primary_raw_equal_paths=rows,owner_receipt_sha256=hashlib.sha256(owner).hexdigest(),owner_receipt_role='CORRELATION_ONLY_NOT_OUR_EXECUTION',ci_snapshot=ci,ack_transfer=False)
(out/'primary-pin-review.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(dict(paths_verified=len(rows),ci=ci)))
