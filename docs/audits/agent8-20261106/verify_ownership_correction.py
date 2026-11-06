import hashlib,json,pathlib,subprocess
root=pathlib.Path(__file__).resolve().parents[1];repo=root/'work/review-integration-56f';out=root/'outputs';head='084ef2ec3b42131b12af44103f2d21845bf1c0f7';previous='ca9e390203305c8662ddf98fb771ac0bd268ec49'
def git(*args):return subprocess.check_output(['git','-C',str(repo),*args])
def obj(ref,path):return json.loads(git('show',ref+':'+path))
assert set(git('diff','--name-only',previous,head).decode().splitlines())=={'MASTER-MISSION-FINAL-AUDIT.md','release/integration-manifest.json','release/ownership-registry.json'}
path='release/ownership-registry.json';raw=git('show',head+':'+path);sha=hashlib.sha256(raw).hexdigest();assert sha=='0ef0dde1f6b238e87b60e2e21eeb13466f6b5e39c3815d91b39890134c982bdd'
old=obj(previous,path);new=json.loads(raw);assert new['revision']==5
oldagents={a['agent_id']:a for a in old['agents']};agents={a['agent_id']:a for a in new['agents']}
for aid,a in agents.items():
 assert a['ack']=='PENDING'
 for field in ['allowed_files','allowed_new_path_prefixes']:assert a[field]==oldagents[aid][field]
assert agents['A8']['base_head']=='b9b03a1ce9f887dbe113fd22d0bda8932f46ef80'
assert agents['A8']['historical_audit_head_not_base']==oldagents['A8']['base_head']
manifest=obj(head,'release/integration-manifest.json');module=manifest['modules']['unified-system']
assert module['pr']==26 and module['pr_url'].endswith('/26') and module['head']==previous
assert module['tree']==git('rev-parse',previous+'^{tree}').decode().strip()
assert manifest['ownership_registry_sha256']==sha and manifest['historical_component_provenance']['pr']==13
assert manifest['go']=='NO-GO' and manifest['runtime_admission']=='BLOCKED' and manifest['status']=='PROVISIONAL_NOT_INSTALLABLE'
result={'head':head,'tree':git('rev-parse',head+'^{tree}').decode().strip(),'previous':previous,'changed_paths':'THREE_DOCUMENTARY_ONLY','ownership_revision':5,'ownership_sha256':sha,'all_top_level_allowed_paths_unchanged':True,'A8_ACK':'FRESH_OWN_PATH_SCOPE_ONLY_NOT_GLOBAL_NO_PRIOR_TRANSFER','F12':'FIX_VERIFIED_DOCUMENTARY_EXACT_SOURCE','tests_rerun':'NONE','runtime_or_hosted':'NOT_QUALIFIED','physical':'BLOCKED','overall':'NO_GO'}
(out/'phase13/ownership-correction-review.json').write_text(json.dumps(result,indent=2))
p=out/'findings.json';findings=json.loads(p.read_text())
for f in findings:
 if f['id']=='A8-F12':f.update(status='FIX_VERIFIED_DOCUMENTARY_EXACT_SOURCE',verified_fix_head=head,fix_evidence='phase13/ownership-correction-review.json')
p.write_text(json.dumps(findings,indent=2))
p=out/'current-acceptance-status.json';status=json.loads(p.read_text());status['P0_P1_P2']['P2_open']=1;status['P0_P1_P2']['F12']='FIX_VERIFIED_DOCUMENTARY_EXACT_SOURCE';status['CONTRACT_STATUS']['documentary_correction']=result;status['EVIDENCE'].append('phase13/ownership-correction-review.json');p.write_text(json.dumps(status,indent=2))
for report in ['phase13/documentary-review.md','phase14/retired-history-review.md']:
 with (out/report).open('a') as f:f.write('\nLater bounded correction: F12 independently resolved at084ef2ec3b42131b12af44103f2d21845bf1c0f7, revision5 SHA0ef0dde1f6b238e87b60e2e21eeb13466f6b5e39c3815d91b39890134c982bdd. A8base and PR26 linkage corrected, historical pins separately labeled; all allocation paths unchanged. Fresh ACK only A8 own prefix, no global or prior ACK transfer. No tests rerun for three documentary-only paths. F13 remains OPEN pending exact fix. Current total7P1/1P2; overall NO-GO.\n')
print(json.dumps(result))
