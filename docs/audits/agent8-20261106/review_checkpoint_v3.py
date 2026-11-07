"""Independent additive UNTRUSTED codec and exact CI snippet review."""
import base64,hashlib,importlib.util,json,os,pathlib,re,subprocess,sys,textwrap,uuid
root=pathlib.Path(__file__).resolve().parents[1];repo=root/'work/review-grid265';out=root/'outputs/phase27';out.mkdir(exist_ok=True);head='10adcff532b6e31c2531c4afcfd0fec1328d6b21';base='ec967b3ebb67bb9f04d0d82c78bba5b4245a3333'
def git(*args):return subprocess.check_output(['git','-C',str(repo),*args])
changes=git('diff','--name-status',base,head).decode().splitlines();assert len(changes)==11 and all(row.startswith('A\t') for row in changes)
for path in ['grid/market_backfill.py','grid/observer_checkpoint.py','grid/segment_wal.py']:
 try:assert git('show',base+':'+path)==git('show',head+':'+path)
 except subprocess.CalledProcessError:
  if path!='grid/segment_wal.py':raise
images=json.loads((repo/'tests/fixtures/agent3-checkpoint-v3/approved-text-images.json').read_bytes())['images'];decoded={k:base64.b64decode(v,validate=True) for k,v in images.items()}
pins={'schema.json':'4de720d9391e5a89c0577b5298c283e742fbfe490c4454c184e31c2348589ea4','golden-vectors.json':'69ef7786400030ae1bb9dbf4bd1fb30c6b6e50ac9690437536aa669a7c18b0d4'}
for name,sha in pins.items():assert hashlib.sha256(decoded[name]).hexdigest()==sha
approved=root.parent/'codex-agent-3-bybit-historical-live/outputs/historical-checkpoint-v3-review1';protocol=(approved/'PROTOCOL.md').read_bytes();assert hashlib.sha256(protocol).hexdigest()=='79efbcb70d1ed9204fbd8295a4990650d99582196712097280d2483298ad4f8e'
for name in decoded:assert decoded[name]==(approved/name).read_bytes()
for item in json.loads(decoded['golden-vectors.json'])['files']:
 raw=decoded[item['path']] if item['path'] in decoded else (repo/'tests/fixtures/agent3-checkpoint-v3'/item['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==item['sha256']
decision=subprocess.check_output(['git','-C',str(root/'work/review-integration75'),'show','381b18bab7f1162db4eef7f348b6e1c921e76403:release/contracts/checkpoint-v3-time/DECISION.json']);assert hashlib.sha256(decision).hexdigest()=='aa84f7acbe7632f8d534c96f529c7a39b9b1b26c1a49cf7a69a9366e5c04670e'
spec=importlib.util.spec_from_file_location('a8_checkpoint_codec',repo/'grid/checkpoint_v3_codec.py');module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module);assert module._SCHEMA_BYTES==decoded['schema.json']
fixtures=repo/'tests/fixtures/agent3-checkpoint-v3';claims=[]
for name in ['confirmed-unknown-time.canonical.json','confirmed-observed.canonical.json','unconfirmed.canonical.json']:
 claim=module.parse_claim((fixtures/name).read_bytes());assert module.encode_claim(claim.as_dict())==claim.canonical_bytes
 try:module.require_authoritative_checkpoint(claim)
 except module.AuthorityIntegrationUnavailable:claims.append({'fixture':name,'claimed_status':claim.commit_status,'actual_promotion':'DENIED'})
 else:raise AssertionError('CLAIM_PROMOTED')
for fake in [None,True,{'verified':True},module.ParsedCheckpointClaim(b'{"commit_status":"COMMITTED"}')]:
 try:module.require_authoritative_checkpoint(fake)
 except module.AuthorityIntegrationUnavailable:pass
 else:raise AssertionError('FORGED_PROMOTION')
workflow=(repo/'.github/workflows/agent3-checkpoint-v3.yml').read_text();snippets=[textwrap.dedent(m.group(1)) for m in re.finditer(r'        run: \|\n((?:          .*\n|\s*\n)+)',workflow)];assert len(snippets)==3 and snippets[0]==snippets[2]
results={}
for name in ['clean','hidden_codec','hidden_inventory','CRLF_codec','hidden_post','git_blob_replace']:
 source=root/'work'/('a3codec-'+name+'-'+uuid.uuid4().hex[:8]);subprocess.run(['git','clone','--local','--no-checkout',str(repo),str(source)],check=True,capture_output=True);subprocess.run(['git','-C',str(source),'-c','core.autocrlf=false','-c','core.eol=lf','checkout','--detach',head],check=True,capture_output=True)
 path='tests/fixtures/agent3-checkpoint-v3/test-inventory.json' if name=='hidden_inventory' else 'grid/checkpoint_v3_codec.py';target=source/path;original=target.read_bytes()
 if name in ('hidden_codec','hidden_inventory','git_blob_replace'):target.write_bytes(original+(b'\n ' if name=='hidden_inventory' else b'\n# A8 source guard negative\n'))
 if name=='CRLF_codec':target.write_bytes(original.replace(b'\n',b'\r\n'))
 if name.startswith('hidden_') and name!='hidden_post' or name=='CRLF_codec':subprocess.run(['git','-C',str(source),'update-index','--assume-unchanged',path],check=True)
 if name=='git_blob_replace':
  original_oid=subprocess.check_output(['git','-C',str(source),'rev-parse',head+':'+path]).decode().strip();new_oid=subprocess.check_output(['git','-C',str(source),'hash-object','-w',path]).decode().strip();subprocess.run(['git','-C',str(source),'replace',original_oid,new_oid],check=True)
 folder=out/name;folder.mkdir(exist_ok=True);temp=root/'work'/('a3codec-temp-'+name);temp.mkdir(exist_ok=True)
 env=os.environ.copy();env.pop('GIT_NO_REPLACE_OBJECTS',None);env.update(A3_EXPECTED_HEAD=head,A3_GUARD_PHASE='before',RUNNER_TEMP=str(temp),PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=os.pathsep.join([str(root/'work/codec-pytest835'),str(source)]),TEMP=str(temp),TMP=str(temp))
 before=subprocess.run([str(root/'work/audit-venv/Scripts/python.exe'),'-B','-c',snippets[0]],cwd=source,env=env,capture_output=True,timeout=30);(folder/'before.stdout.log').write_bytes(before.stdout);(folder/'before.stderr.log').write_bytes(before.stderr)
 if name in ('hidden_codec','hidden_inventory','CRLF_codec'):assert before.returncode!=0;results[name]={'before_exit':before.returncode,'tests_executed':0,'expected':'REJECT'};continue
 assert before.returncode==0
 tests=subprocess.run([str(root/'work/audit-venv/Scripts/python.exe'),'-B','-c',snippets[1]],cwd=source,env=env,capture_output=True,timeout=60);(folder/'tests.stdout.log').write_bytes(tests.stdout);(folder/'tests.stderr.log').write_bytes(tests.stderr);assert tests.returncode==0
 if name=='hidden_post':target.write_bytes(original+b'\n# A8 hidden after test\n');subprocess.run(['git','-C',str(source),'update-index','--assume-unchanged',path],check=True)
 env['A3_GUARD_PHASE']='after';after=subprocess.run([str(root/'work/audit-venv/Scripts/python.exe'),'-B','-c',snippets[2]],cwd=source,env=env,capture_output=True,timeout=30);(folder/'after.stdout.log').write_bytes(after.stdout);(folder/'after.stderr.log').write_bytes(after.stderr)
 if name=='hidden_post':assert after.returncode!=0
 else:assert after.returncode==0
 evidence=temp/'agent3-checkpoint-v3'
 for p in evidence.iterdir():
  if p.is_file():(folder/p.name).write_bytes(p.read_bytes())
 result=json.loads((evidence/'result.json').read_text());assert result['cases']==43 and result['skips']==0
 if name=='git_blob_replace':assert subprocess.check_output(['git','-C',str(source),'--no-replace-objects','cat-file','blob',head+':'+path])==original and target.read_bytes()!=original
 results[name]={'before_exit':before.returncode,'tests_exit':tests.returncode,'after_exit':after.returncode,'cases':43,'skips':0,'expected':'REJECT' if name=='hidden_post' else ('SOURCE_BINDING_NEGATIVE_SHOULD_REJECT' if name=='git_blob_replace' else 'ACCEPT_LOCAL43')}
report={'head':head,'tree':git('rev-parse','HEAD^{tree}').decode().strip(),'base':base,'eleven_new_paths_only':True,'schema_protocol_goldens_pins_verified':True,'owner_decision_raw_sha256_verified':True,'parsed_claims':claims,'forged_promotion_always_denied':True,'legacy_existing_readers_unchanged':True,'cases':results,'scope':'PURE_CODEC_MODEL_STRUCTURE_NOT_ACTUAL_PUBLICATION_PROOF','raw_guard_git_replace_control':'ACCEPTED_CHANGED_BYTES_UNDER_ORIGINAL_HEAD','F16':'P2_OPEN_GIT_REPLACEMENT_SOURCE_BINDING','hosted':'NOT_QUALIFIED','physical':'BLOCKED','overall':'NO_GO'}
(out/'checkpoint-v3-review.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
