"""Independent execution of exact corrected CI block and owned negative fixtures."""
import hashlib,json,os,pathlib,subprocess,textwrap,uuid
root=pathlib.Path(__file__).resolve().parents[1];repo=root/'work/review5-f15-fixed';out=root/'outputs/phase25';out.mkdir(exist_ok=True);head='6bcf5475023a8f6a9733d02ad899064d0d83be95';previous='175b48a2a0d2882669172abc5774bd71b42e2215'
def git(*args):return subprocess.check_output(['git','-C',str(repo),*args])
assert set(git('diff','--name-only',previous,head).decode().splitlines())=={'.github/workflows/agent5-components.yml','docs/scheduler/components.md','docs/scheduler/f15-raw-source-binding.md'}
for path in ['scheduler_components/durable.py','tests/test_agent5_scheduler_components.py','docs/scheduler/component-test-inventory-v2.json']:assert git('show',previous+':'+path)==git('show',head+':'+path)
workflow=(repo/'.github/workflows/agent5-components.yml').read_text();code=textwrap.dedent(workflow.split("          python - <<'PY'\n",1)[1].split('          PY',1)[0]);assert workflow.index('GIT_CONFIG_VALUE_1: lf')<workflow.index('- uses: actions/checkout')
prelude='''import unittest,pathlib,subprocess
_discover=unittest.defaultTestLoader.discover
def flat(value):
 for item in value:
  if isinstance(item,unittest.TestSuite):yield from flat(item)
  else:yield item
def wrapped(*a,**k):
 suite=_discover(*a,**k);items=list(flat(suite))
 __INJECT__
 return suite
unittest.defaultTestLoader.discover=wrapped
'''
source_path='scheduler_components/durable.py';test_path='tests/test_agent5_scheduler_components.py';inventory='docs/scheduler/component-test-inventory-v2.json';wf='.github/workflows/agent5-components.yml'
cases={'clean':{},'original_hidden_comment':{'mutate':source_path},'hidden_test_comment':{'mutate':test_path},'hidden_inventory_whitespace':{'mutate':inventory},'hidden_workflow_comment':{'mutate':wf},'CRLF_source':{'crlf':True},'missing_source':{'missing':True},'nonregular_source':{'nonregular':True},'unexpected_protected_python':{'extra':True},'hidden_post_source':{'inject':"items[0].addCleanup(lambda:(pathlib.Path('scheduler_components/durable.py').write_bytes(pathlib.Path('scheduler_components/durable.py').read_bytes()+b'\\n# post-test A8 tamper\\n'),subprocess.check_call(['git','update-index','--assume-unchanged','scheduler_components/durable.py'])))"},'wrong_ID_same30':{'inject':"items[0].id=lambda:'A8_SUBSTITUTED_ID'"},'skip':{'inject':"getattr(items[0],items[0]._testMethodName).__func__.__unittest_skip__=True"}}
results={}
scratch=root/'work/a5-f15-case-temp';scratch.mkdir(exist_ok=True)
for name,options in cases.items():
 source=root/'work'/('a5-f15-'+name+'-'+uuid.uuid4().hex[:8]);subprocess.run(['git','clone','--local','--no-checkout',str(repo),str(source)],check=True,capture_output=True);subprocess.run(['git','-C',str(source),'-c','core.autocrlf=false','-c','core.eol=lf','checkout','--detach',head],check=True,capture_output=True)
 path=options.get('mutate',source_path);target=source/path
 if 'mutate' in options:
  target.write_bytes(target.read_bytes()+(b'\n ' if path==inventory else b'\n# auditor hidden input tamper\n'));subprocess.run(['git','-C',str(source),'update-index','--assume-unchanged',path],check=True)
 if options.get('crlf'):target.write_bytes(target.read_bytes().replace(b'\n',b'\r\n'));subprocess.run(['git','-C',str(source),'update-index','--assume-unchanged',path],check=True)
 if options.get('missing') or options.get('nonregular'):
  target.unlink()
  if options.get('nonregular'):target.mkdir()
  subprocess.run(['git','-C',str(source),'update-index','--assume-unchanged',path],check=True)
 if options.get('extra'):(source/'scheduler_components/a8_untracked.py').write_text('# extra protected source\n')
 folder=out/name;folder.mkdir(exist_ok=True)
 env={k:v for k,v in os.environ.items() if not k.startswith('GITHUB_')};env.update(EXPECTED_SOURCE_SHA=head,EVIDENCE_DIR=str(folder),PYTHONDONTWRITEBYTECODE='1',TEMP=str(scratch),TMP=str(scratch))
 boot='import sys,os;sys.path[:0]=[os.getcwd(),'+repr(str(root/'work/integration-review-deps'))+'];\n';injected=prelude.replace('__INJECT__',options['inject']) if 'inject' in options else ''
 run=subprocess.run([str(root/'work/audit-venv/Scripts/python.exe'),'-I','-B','-c',boot+injected+code],cwd=source,env=env,capture_output=True,timeout=60)
 (folder/'stdout.log').write_bytes(run.stdout);(folder/'stderr.log').write_bytes(run.stderr);receipt=json.loads((folder/'receipt.json').read_text());assert hashlib.sha256((folder/'component-tests.log').read_bytes()).hexdigest()==receipt['test_log_sha256']
 if name=='clean':
  assert run.returncode==0 and receipt['passed'] and receipt['tests_run']==30 and receipt['skips']==receipt['failures']==receipt['errors']==0
  assert receipt['source_before']==receipt['source_after'] and receipt['source_before']['protected_inputs_valid'];assert len(receipt['source_before']['protected_files'])==8
  assert all(f['actual_sha256']==f['committed_sha256'] and f['matches_committed_blob'] and f['regular_file'] for f in receipt['source_before']['protected_files'])
 else:assert run.returncode!=0 and receipt['passed'] is False
 if 'inject' not in options and name!='clean':assert receipt['tests_run']==0
 if name=='hidden_post_source':assert receipt['tests_run']==30 and not receipt['source_after']['protected_inputs_valid']
 results[name]={'exit_code':run.returncode,'passed':receipt['passed'],'tests_run':receipt['tests_run'],'skips':receipt['skips'],'source_before_valid':receipt['source_before']['protected_inputs_valid'],'source_after_valid':receipt['source_after']['protected_inputs_valid']}
report={'head':head,'tree':git('rev-parse','HEAD^{tree}').decode().strip(),'previous':previous,'delta':'WORKFLOW_AND_TWO_DOCUMENTS_ONLY_PRODUCT_TEST_INVENTORY_UNCHANGED','workflow_code_sha256':hashlib.sha256(code.encode()).hexdigest(),'clean_protected_files':8,'cases':results,'original_F15_repro':'REJECTED_BEFORE_TESTS_NO_NORMALIZATION','F15':'FIX_VERIFIED_OFFLINE_EXACT_SOURCE','source_proof_scope':'REGULAR_PROTECTED_RAW_GIT_BLOBS_BEFORE_AFTER_TRUSTED_EPHEMERAL_RUNNER_NOT_NATIVE_EXECUTION_ATTESTATION','hosted':'NOT_QUALIFIED','runtime_authority':'NOT_QUALIFIED','physical':'BLOCKED','overall':'NO_GO'}
(out/'f15-fix-review.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
