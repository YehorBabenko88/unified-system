"""Exact Root137 import/source controls only; no full suite or native bridge."""
import hashlib,importlib.util,json,os,pathlib,re,subprocess,textwrap,uuid
r=pathlib.Path(__file__).resolve().parents[1];seed=r/'work/review-integration75';out=r/'outputs/phase42';out.mkdir(exist_ok=True);head='e238558a1d5bc44128b4541531a2cb9e194155e9';tree='0ab27ebdc4da8e2a3fa8613b4bac4add1c9c949c';previous='237722bb1d5c8bc671a498609729261bdd3c9fce'
def git(at,*args):return subprocess.check_output(['git','--no-replace-objects','-C',str(at),*args])
def read(ref,name):return git(seed,'show',ref+':'+name)
assert git(seed,'rev-parse',head+'^{tree}').decode().strip()==tree
inventory=json.loads(read(head,'release/component-test-inventory.json'));prior=json.loads(read(previous,'release/component-test-inventory.json'));assert inventory['expected_count']==137 and inventory['preserved_prior_ids']==prior['expected_test_ids'] and len(prior['expected_test_ids'])==129
workflow=read(head,'.github/workflows/final-integration.yml').decode();assert 'shell: python -I -B {0}' in workflow;code=textwrap.dedent(workflow.split('        shell: python -I -B {0}\n        run: |\n',1)[1].split('      - uses:',1)[0]);assert 'source_paths = tuple(source_objects)' in code
prelude='''import unittest,pathlib
_load=unittest.defaultTestLoader.loadTestsFromName
_used=False
def flat(value):
 for item in value:
  if isinstance(item,unittest.TestSuite):yield from flat(item)
  else:yield item
def wrapped(*a,**k):
 global _used
 suite=_load(*a,**k);items=list(flat(suite))
 if not _used:
  _used=True
  __INJECT__
 return suite
unittest.defaultTestLoader.loadTestsFromName=wrapped
'''
cases=('clean','repo_cache','root_shadow','unknown_native','stale_receipt','redirected_cache','blob_replace','post_cache');results={}
for name in cases:
 source=r/'work'/('root-source137-'+name+'-'+uuid.uuid4().hex[:8]);subprocess.run(['git','clone','--no-hardlinks','--no-checkout',str(seed),str(source)],check=True,capture_output=True);subprocess.run(['git','-C',str(source),'-c','core.autocrlf=false','-c','core.eol=lf','checkout','--detach',head],check=True,capture_output=True)
 assert (source/'.git').is_dir() and not (source/'.git/objects/info/alternates').exists();folder=out/name;folder.mkdir(exist_ok=True);marker=folder/'inert-executed.txt';path='unified_system/security_identity_records.py';target=source/path
 if name=='repo_cache':
  import importlib._bootstrap_external as external
  body=target.read_bytes();compiled=compile(body+b'\nopen('+repr(str(marker)).encode()+b',"w").write("A8_ROOT_BYTECODE_WITNESS")\n',str(target),'exec');cache=pathlib.Path(importlib.util.cache_from_source(str(target)));cache.parent.mkdir(exist_ok=True);cache.write_bytes(external._code_to_timestamp_pyc(compiled,int(target.stat().st_mtime),len(body)))
 if name=='root_shadow':(source/'typing.py').write_text('open('+repr(str(marker))+',"w").write("A8_ROOT_SHADOW_WITNESS")\n')
 if name=='unknown_native':(source/'inert_extra.pyd').write_bytes(b'NOT_A_NATIVE_BINARY')
 if name=='stale_receipt':(source/'partial-integration-ci-evidence.json').write_text('{}')
 if name=='blob_replace':
  target.write_bytes(target.read_bytes()+b'\n# A8 primary object negative\n');original=git(source,'rev-parse',head+':'+path).decode().strip();replacement=git(source,'hash-object','-w','--no-filters',path).decode().strip();subprocess.run(['git','-C',str(source),'update-index','--assume-unchanged',path],check=True);subprocess.run(['git','-C',str(source),'replace',original,replacement],check=True)
 scratch=r/'work'/('root-source137-temp-'+uuid.uuid4().hex[:8]);scratch.mkdir();env={k:v for k,v in os.environ.items() if not k.startswith('GIT_') and not k.startswith('GITHUB_')};env.update(EXPECTED_HEAD=head,GITHUB_RUN_ID='A8_LOCAL_NOT_HOSTED',GITHUB_RUN_ATTEMPT='LOCAL_ONLY',PYTHONDONTWRITEBYTECODE='1',GIT_CONFIG_COUNT='2',GIT_CONFIG_KEY_0='core.autocrlf',GIT_CONFIG_VALUE_0='false',GIT_CONFIG_KEY_1='core.eol',GIT_CONFIG_VALUE_1='lf',TEMP=str(scratch),TMP=str(scratch))
 boot="import sys,ipaddress\nsys.path.insert(0,"+repr(str(r/'work/integration-review-deps'))+")\ndef guard(event,args):\n if event in ('socket.connect','socket.bind') and (not isinstance(args[1],tuple) or not ipaddress.ip_address(args[1][0]).is_loopback):raise RuntimeError('A8_NONLOOPBACK_DENIED')\nsys.addaudithook(guard)\n"
 if name=='post_cache':boot+=prelude.replace('__INJECT__',"items[0].addCleanup(lambda:(pathlib.Path('unified_system/__pycache__').mkdir(exist_ok=True),pathlib.Path('unified_system/__pycache__/a8.pyc').write_bytes(b'A8_POST_CACHE')))")
 args=[str(r/'work/audit-venv/Scripts/python.exe'),'-I','-B']+(['-X','pycache_prefix='+str(scratch/'redirect')] if name=='redirected_cache' else [])+['-c',boot+code]
 p=subprocess.run(args,cwd=source,env=env,capture_output=True,timeout=240);(folder/'stdout.log').write_bytes(p.stdout);(folder/'stderr.log').write_bytes(p.stderr);receiptpath=source/'partial-integration-ci-evidence.json';receipt=json.loads(receiptpath.read_text()) if receiptpath.exists() and name!='stale_receipt' else None;testlog=source/'partial-integration-ci-tests.log';ran=0
 if testlog.exists():
  body=testlog.read_bytes();(folder/'tests.log').write_bytes(body);count=re.findall(rb'Ran ([0-9]+) tests?',body);ran=int(count[-1]) if count else 0
 if name=='clean':
  assert p.returncode==0 and receipt['tests']==137 and receipt['skipped']==receipt['failures']==receipt['errors']==0 and receipt['source_before']==receipt['source_after'];assert sorted(receipt['mandatory_test_ids'])==inventory['expected_test_ids'];assert hashlib.sha256(testlog.read_bytes()).hexdigest()==receipt['test_log_sha256']
  for path,entry in receipt['source_before']['files'].items():
   body=(source/path).read_bytes();oid=git(source,'rev-parse',head+':'+path).decode().strip();assert hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()==oid and hashlib.sha256(body).hexdigest()==entry['raw_sha256']
 else:assert p.returncode!=0 and not receipt
 if name in ('repo_cache','root_shadow'):assert not marker.exists()
 if receipt:(folder/'receipt.json').write_text(json.dumps(receipt,indent=2))
 results[name]=dict(exit_code=p.returncode,tests=ran,receipt_emitted=receipt is not None,marker_executed=marker.exists(),tracked_inputs=len(receipt['source_before']['files']) if receipt else None,all_source_files_bound=(len(receipt['source_before']['files'])==len(git(source,'ls-tree','-rz',head).split(b'\0'))-1) if receipt else None)
report=dict(head=head,tree=tree,source_workflow_sha256=hashlib.sha256(read(head,'.github/workflows/final-integration.yml')).hexdigest(),cases=results,preserved_prior129=True,F17_Root='FIX_VERIFIED_OFFLINE_EXACT_SOURCE',F17_global='PENDING_OTHER_APPLICABLE_GUARDS',F16_global='OPEN',qualification='SOURCE_ONLY_COMPONENT_WORKFLOW_NOT_HOSTED_NATIVE_OR_PHYSICAL',overall='NO_GO');(out/'root-source-import-review.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
