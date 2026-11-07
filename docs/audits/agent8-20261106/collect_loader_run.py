"""Read-only single-run evidence collector. Never activate, rerun or cancel."""
import datetime,hashlib,json,pathlib,subprocess
root=pathlib.Path(__file__).resolve().parents[1];out=root/'outputs/phase19';out.mkdir(exist_ok=True);runid=42274233717
def gh(path,*args):
 p=subprocess.run(['gh','api',path,*args],capture_output=True);assert p.returncode==0,(path,p.stderr.decode());return json.loads(p.stdout)
def blob(repo,ref,path):return subprocess.check_output(['git','-C',str(repo),'show',ref+':'+path])
ref='f3bde56c889ebd5e15665a05e113213f511f2b2a';authraw=blob(root/'work/review-integration-56f',ref,'release/diagnostic-authorizations/math113-dbb9bb1.json');auth=json.loads(authraw);digest=hashlib.sha256(authraw).hexdigest();assert digest=='3df3720c7efbf0ad71ea0ac84e7001e37ea8c2deaf105076ff473f6919ac48a2'
ack=(root/'outputs/phase18/source-review-ack.json').read_bytes();assert hashlib.sha256(ack).hexdigest()==auth['a8_source_ack']['sha256']
repo=root/'work/review-math113-label';workflow=blob(repo,auth['source_head'],auth['workflow']);eventworkflow=blob(repo,auth['event_merge_head_reviewed'],auth['workflow']);assert workflow==eventworkflow
assert hashlib.sha256(workflow).hexdigest()==auth['workflow_sha256'] and hashlib.sha1(b'blob '+str(len(workflow)).encode()+b'\0'+workflow).hexdigest()==auth['workflow_blob_sha1']==auth['event_workflow_blob_sha1']
run=gh('repos/YehorBabenko88/math/actions/runs/'+str(runid));jobs=gh('repos/YehorBabenko88/math/actions/runs/'+str(runid)+'/jobs');artifacts=gh('repos/YehorBabenko88/math/actions/runs/'+str(runid)+'/artifacts')
assert run['head_sha']==auth['source_head'] and run['path']==auth['workflow'] and run['event']=='pull_request' and run['run_attempt']==1
assert run['actor']['login']==run['triggering_actor']['login']=='YehorBabenko88'
events=gh('repos/YehorBabenko88/math/issues/113/events','--paginate','--slurp');matching=[e for page in events for e in page if e['event']=='labeled' and e['label']['name']==auth['allowed_activation']['label']]
assert len(matching)==1 and matching[0]['actor']['login']=='YehorBabenko88'
label=gh('repos/YehorBabenko88/math/labels/'+auth['allowed_activation']['label']);assert label['description']=='review-sha256:'+digest
for name,value in [('authorization',auth),('run',run),('jobs',jobs),('artifacts',artifacts),('matching-label-events',matching)]:
 (out/(name+'.json')).write_text(json.dumps(value,indent=2))
report={'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'authorization_commit':ref,'authorization_sha256':digest,'source_head':auth['source_head'],'source_tree':auth['source_tree'],'source_and_reviewed_merge_workflow_blobs_match':True,'a8_ack_sha256_verified':True,'matching_label_activations_observed':len(matching),'matching_run':runid,'attempt':run['run_attempt'],'status':run['status'],'conclusion':run['conclusion'],'jobs':[{'id':j['id'],'name':j['name'],'status':j['status'],'conclusion':j['conclusion'],'runner_name':j['runner_name']} for j in jobs['jobs']],'artifacts':artifacts['total_count'],'runtime_event_source_receipt':'PENDING_LOGS_NOT_VERIFIED','native_trace':'NOT_RUN_OR_NOT_AVAILABLE','cleanup':'NOT_VERIFIED','qualification':'NONE','native_acceptance':'BLOCKED','physical':'BLOCKED','second_activation_by_A8':False,'overall':'NO_GO'}
(out/'run-review.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
