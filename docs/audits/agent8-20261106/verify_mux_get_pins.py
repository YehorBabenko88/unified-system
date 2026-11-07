import ast,hashlib,json,pathlib,subprocess
r=pathlib.Path(__file__).resolve().parents[1];repo=r/'work/review-mux-get-be5cb94';owner=r.parent/'codex-agent-2-high-availability-distributed/outputs';out=r/'outputs/phase61';head='be5cb942436f82f374375eabb255768bb139797f';base='0c21256e30aeb3a4184dda97a2bebf24c047acd0'
def git(*a):return subprocess.check_output(['git','--no-replace-objects','-C',str(repo),*a])
raw=(owner/'CONTROL-MUX-GET-BE5CB94-EVIDENCE.json').read_bytes();assert hashlib.sha256(raw).hexdigest()=='5f144af1aa8230d10dc49f039c65c490b722900eaa9099626d5e2c6c4e86ae5f';a=json.loads(raw);assert set(git('diff','--name-only',base,head).decode().splitlines())==set(a['changed_paths']) and len(a['changed_paths'])==13
abi=(owner/'CONTROL-MUX-GET-BE5CB94-NATIVE-ABI-PINS.json').read_bytes();assert hashlib.sha256(abi).hexdigest()=='9a910e6f337e765cc281f364e901948f4e7017d25e319779ab436e0a15d2518a';b=json.loads(abi)
for field in ['source_raw_sha256','frozen_review2_raw_sha256']:
 for path,digest in b[field].items():assert hashlib.sha256(git('show',head+':'+path)).hexdigest()==digest
assert not git('diff','--name-only',base,head,'--','release/contracts/control-mux-closed-review4','docs/control-mux/contracts/reconciliation-v3-review2.schema.json','docs/control-mux/contracts/reconciliation-v3-review2.vectors.json','docs/control-mux/contracts/reconciliation-v3-review2.md','tests/control_mux/reconciliation_proposal_review2.py')
def inventory(ref,name):
 tree=ast.parse(git('show',ref+':tests/control_mux/source_runner.py'));return next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets))
old=inventory(base,'EVENTS');new=inventory(head,'EVENTS');assert len(old)==42 and len(new)==len(set(new))==72 and set(old)<=set(new);ou=inventory(base,'UNITS');nu=inventory(head,'UNITS');assert len(ou)==18 and len(nu)==33 and ou<=nu
bound=(owner/'CONTROL-MUX-GET-BE5CB94-SOURCE-BOUND.json').read_bytes();assert hashlib.sha256(bound).hexdigest()=='10770e72e2ed2be87f59afd8fe19109682b16b71180ea1de29732a82d26875b0'
reds=[]
for path,digest in a['evidence_raw_sha256'].items():
 if '-RED.log' in path:
  body=(owner/path).read_bytes();assert hashlib.sha256(body).hexdigest()==digest;(out/('owner-'+path)).write_bytes(body);reds.append(dict(file=path,sha256=digest,scope='ORIGINAL_OWNER_RED_NOT_INDEPENDENTLY_REEXECUTED'))
ci=[]
for run in [42361292167,42361289232]:
 p=subprocess.run(['gh','api','repos/YehorBabenko88/unified-system/actions/runs/'+str(run)],capture_output=True,check=True);(out/('ci-'+str(run)+'.original.json')).write_bytes(p.stdout);d=json.loads(p.stdout);assert d['head_sha']==head;ci.append({k:d.get(k) for k in ['id','head_sha','run_attempt','status','conclusion','event']})
report=dict(head=head,tree=git('rev-parse','HEAD^{tree}').decode().strip(),base=base,changed_paths=a['changed_paths'],frozen_review4_and_GETreview2_raw_unchanged=True,retained_real=42,new_real_GET=30,retained_units=18,new_units=15,native_ABI_pin_sha256=hashlib.sha256(abi).hexdigest(),native_ABI='EXACT_TYPED_FOUR_KIND_SOURCE_PROPOSAL_ONLY_NO_NATIVE_PROVIDER',owner_sourcebound_verified_as_correlation_only=True,original_owner_RED_logs=reds,ci_snapshot=ci)
(out/'primary-pin-review.json').write_text(json.dumps(report,indent=2),encoding='utf-8');(out/'owner-native-ABI.original.json').write_bytes(abi);print(json.dumps(dict(changes=13,real=72,units=33,ownerREDs=len(reds),ci=ci),indent=2))
