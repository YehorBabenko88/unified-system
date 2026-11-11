"""Read-only immutable authorization/event parity review; never dispatches."""
import hashlib,json,pathlib,subprocess
r=pathlib.Path(__file__).resolve().parents[1];out=r/'outputs/phase43';out.mkdir(exist_ok=True)
root=r/'work/unified-audit';math=r/'work/review-math113-label';pin='223c225bbf17cf6c8eaeb8d39d933620b9c1c098';prefix='release/diagnostic-authorizations/math115/'
def git(repo,*args):return subprocess.check_output(['git','--no-replace-objects','-C',str(repo),*args])
def capture(name,args):
 p=subprocess.run(args,capture_output=True,check=True);(out/name).write_bytes(p.stdout);return json.loads(p.stdout)
raw=git(root,'show',pin+':'+prefix+'authorization.json');(out/'authorization.original.json').write_bytes(raw);a=json.loads(raw)
assert hashlib.sha256(raw).hexdigest()=='355ca961ac39edb3c9a0f5505467610926a9abaaafc1bb54bc9275ce56e61442'
ledger=git(root,'show',pin+':'+prefix+'dispatch-ledger.json');(out/'ledger.original.json').write_bytes(ledger);l=json.loads(ledger)
assert l['authorization_sha256']==hashlib.sha256(raw).hexdigest() and l['state']=='RESERVED_NOT_DISPATCHED' and l['api_label_add_calls_attempted']==0
ack=git(root,'show',pin+':'+prefix+'a8-preparation-ack.json');assert ack==(r/'outputs/phase40/source-model-ack.json').read_bytes()
pr=capture('current-pr.json',['gh','pr','view','115','--repo','YehorBabenko88/math','--json','headRefOid,baseRefOid,headRefName,baseRefName,isDraft,labels'])
event=capture('current-api-pr.json',['gh','api','repos/YehorBabenko88/math/pulls/115'])
assert pr['isDraft'] and not pr['labels'] and pr['headRefOid']==a['source_head'] and pr['baseRefOid']=='9f08b237b9d0a47abfb03ee4741c7f1688081fbd'
assert pr['headRefName']=='agent7/math-loader-init-followup-20261107' and pr['baseRefName']=='agent7/math-verifier-import-20261107'
merge=event['merge_commit_sha'];assert merge==a['event_merge_head_reviewed']
assert git(math,'rev-parse',a['source_head']+'^{tree}').decode().strip()==a['source_tree']
workflow=a['workflow'];source=git(math,'show',a['source_head']+':'+workflow);merged=git(math,'show',merge+':'+workflow)
assert source==merged and hashlib.sha256(source).hexdigest()==a['workflow_sha256']
assert git(math,'rev-parse',merge+':'+workflow).decode().strip()==a['workflow_blob_sha1']==a['event_workflow_blob_sha1']
assert a['allowed_activation']['activations_max']==1 and a['allowed_activation']['attempt']==1 and not a['allowed_activation']['automatic_retry_remove_relabel_rerun_cancel']
assert a['budgets']==dict(event_seconds=10,cleanup_seconds=5,owner_watchdog_seconds=30,public_bytes=8192,events=256)
report=dict(root_pin=pin,authorization_sha256=hashlib.sha256(raw).hexdigest(),source_head=a['source_head'],source_tree=a['source_tree'],current_merge=merge,workflow_sha256=hashlib.sha256(source).hexdigest(),preparation_ack_raw_equal=True,ledger_snapshot=l,review='ACK_RECORD_AND_CURRENT_EVENT_PARITY_ONLY',authority='ROOT_RECORD_DECLARATION_NOT_INDEPENDENTLY_AUTHENTICATED_OWNER_DIRECTIVE',activation_performed=False,api_mutations=0,native_acceptance='BLOCKED',overall='NO_GO',dispatch_conditions='Root must independently validate owner authority, recheck refs, persist intent before one API call; UNKNOWN consumed; no retry')
(out/'record-parity-review.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
