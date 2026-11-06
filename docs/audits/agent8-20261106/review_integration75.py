"""Independent new75 exact workflow and guarded-input negative controls."""
import ast,concurrent.futures,hashlib,json,os,pathlib,re,subprocess,textwrap,uuid
root=pathlib.Path(__file__).resolve().parents[1];repo=root/'work/review-integration75';out=root/'outputs/phase26';out.mkdir(exist_ok=True);head='c9f3735c1efa2d5ae0e2dfbe52987a49c520bdf5';old='56f4215506f3a6efb7404591753facd69204a1ee'
def git(*args):return subprocess.check_output(['git','-C',str(repo),*args])
inventory=json.loads(git('show',head+':release/component-test-inventory.json'));prior=json.loads(git('show',old+':release/component-test-inventory.json'))['expected_test_ids'];assert len(prior)==59 and inventory['preserved_prior_ids']==prior and set(prior)<=set(inventory['expected_test_ids']) and len(inventory['expected_test_ids'])==len(set(inventory['expected_test_ids']))==75
def methods(ref,path):
 tree=ast.parse(git('show',ref+':'+path));return {(c.name,m.name):ast.dump(m,include_attributes=False) for c in tree.body if isinstance(c,ast.ClassDef) for m in c.body if isinstance(m,ast.FunctionDef) and m.name.startswith('test_')}
for path in ['tests/test_integration_registry.py','tests/test_agent5_scheduler_components.py','tests/test_control_api_readonly.py','tests/test_operator_control_plane.py']:
 before,after=methods(old,path),methods(head,path);assert all(after[k]==v for k,v in before.items())
assert git('show',head+':scripts/network_readonly_probe.ps1')==git('show','15dd9e8340cc332204ebbe6c13744f797ceca2f4:scripts/network_readonly_probe.ps1')
assert git('show',head+':scheduler_components/durable.py')==git('show','6bcf5475023a8f6a9733d02ad899064d0d83be95:scheduler_components/durable.py')
old_provider=ast.parse(git('show','15dd9e8340cc332204ebbe6c13744f797ceca2f4:tests/test_network_probe_provider_closed.py'));new_provider=ast.parse(git('show',head+':tests/test_network_probe_provider_closed.py'))
for node in ast.walk(new_provider):
 if isinstance(node,ast.ImportFrom) and node.module=='tests.test_network_deployment_guard':node.module='test_network_deployment_guard'
assert ast.dump(old_provider,include_attributes=False)==ast.dump(new_provider,include_attributes=False)
workflow=(repo/'.github/workflows/final-integration.yml').read_text();code=textwrap.dedent(workflow.split('        shell: python\n        run: |\n',1)[1].split('      - uses:',1)[0]);assert "'.ps1'" in code
prelude='''import unittest,pathlib,subprocess
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
cases={'clean':{},'hidden_PS_comment':{'path':'scripts/network_readonly_probe.ps1','comment':True},'hidden_A5_comment':{'path':'scheduler_components/durable.py','comment':True},'hidden_inventory_whitespace':{'path':'release/component-test-inventory.json','comment':True},'CRLF_PS':{'path':'scripts/network_readonly_probe.ps1','crlf':True},'missing_PS':{'path':'scripts/network_readonly_probe.ps1','missing':True},'hidden_post_PS':{'inject':"items[0].addCleanup(lambda:(pathlib.Path('scripts/network_readonly_probe.ps1').write_bytes(pathlib.Path('scripts/network_readonly_probe.ps1').read_bytes()+b'\\n# hidden post-test tamper\\n'),subprocess.check_call(['git','update-index','--assume-unchanged','scripts/network_readonly_probe.ps1'])))"},'missing_prior_ID':{'inject':'return unittest.TestSuite(items[:-1])'},'duplicate_prior_ID':{'inject':'return unittest.TestSuite(items[:-1]+[items[0]])'},'same75_substituted_prior_ID':{'inject':"items[0].id=lambda:'A8_SUBSTITUTED_ID'"},'skip':{'inject':"getattr(items[0],items[0]._testMethodName).__func__.__unittest_skip__=True"}}
def execute(item):
 name,options=item;source=root/'work'/('integration75-'+name+'-'+uuid.uuid4().hex[:8]);subprocess.run(['git','clone','--local','--no-checkout',str(repo),str(source)],check=True,capture_output=True);subprocess.run(['git','-C',str(source),'-c','core.autocrlf=false','-c','core.eol=lf','checkout','--detach',head],check=True,capture_output=True)
 path=options.get('path');target=source/path if path else None
 if options.get('comment'):target.write_bytes(target.read_bytes()+(b'\n ' if path.endswith('.json') else b'\n# A8 hidden comment\n'))
 if options.get('crlf'):target.write_bytes(target.read_bytes().replace(b'\n',b'\r\n'))
 if options.get('missing'):target.unlink()
 if path:subprocess.run(['git','-C',str(source),'update-index','--assume-unchanged',path],check=True)
 scratch=root/'work'/('integration75-temp-'+name);scratch.mkdir(exist_ok=True)
 env={k:v for k,v in os.environ.items() if not k.startswith('GITHUB_')};env.update(EXPECTED_HEAD=head,GITHUB_RUN_ID='LOCAL_A8_NOT_HOSTED',GITHUB_RUN_ATTEMPT='LOCAL_ONLY',PYTHONDONTWRITEBYTECODE='1',TEMP=str(scratch),TMP=str(scratch))
 boot='import sys,os;sys.path[:0]=[os.getcwd(),'+repr(str(root/'work/integration-review-deps'))+'];\n';injected=prelude.replace('__INJECT__',options['inject']) if 'inject' in options else ''
 run=subprocess.run([str(root/'work/audit-venv/Scripts/python.exe'),'-I','-B','-c',boot+injected+code],cwd=source,env=env,capture_output=True,timeout=120)
 folder=out/name;folder.mkdir(exist_ok=True);(folder/'stdout.log').write_bytes(run.stdout);(folder/'stderr.log').write_bytes(run.stderr)
 receiptpath=source/'partial-integration-ci-evidence.json';receipt=json.loads(receiptpath.read_text()) if receiptpath.exists() else None
 testlog=source/'partial-integration-ci-tests.log';ran=None
 if testlog.exists():
  raw=testlog.read_bytes();(folder/'tests.log').write_bytes(raw);counts=re.findall(rb'Ran ([0-9]+) tests?',raw);ran=int(counts[-1]) if counts else None
 if name=='clean':
  assert run.returncode==0 and receipt['tests']==75 and receipt['skipped']==receipt['failures']==receipt['errors']==0 and len(set(receipt['mandatory_test_ids']))==75
  assert receipt['source_before']==receipt['source_after'] and len(receipt['source_before']['files'])==377 and 'scripts/network_readonly_probe.ps1' in receipt['source_before']['files']
  assert set(prior)<=set(receipt['mandatory_test_ids']);log=(source/'partial-integration-ci-tests.log').read_bytes();assert hashlib.sha256(log).hexdigest()==receipt['test_log_sha256'];(folder/'tests.log').write_bytes(log)
 else:assert run.returncode!=0,('NEGATIVE_ACCEPTED',name)
 if receipt:(folder/'receipt.json').write_text(json.dumps(receipt,indent=2))
 return name,{'exit_code':run.returncode,'receipt_emitted':receipt is not None,'tests':receipt['tests'] if receipt else None,'tests_from_log':ran,'skipped':receipt['skipped'] if receipt else None,'reason':[line for line in run.stderr.decode(errors='replace').splitlines() if 'AssertionError' in line][-1:]}
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:results=dict(executor.map(execute,cases.items()))
report={'head':head,'tree':git('rev-parse','HEAD^{tree}').decode().strip(),'prior_source':old,'all_prior59_IDs_and_test_method_ASTs_preserved':True,'new_inventory':75,'new_cases':'15_A5_DURABLE_PLUS1_PROVIDER_AST','A5_product_and_PS_match_independently_reviewed_pins':True,'workflow_code_sha256':hashlib.sha256(code.encode()).hexdigest(),'raw_protected_inputs':377,'cases':results,'scope':'EXACT_EMBEDDED_WORKFLOW_LOCAL_WINDOWS_75_NOT_59_INHERITANCE','hosted':'NOT_QUALIFIED','runtime':'NOT_QUALIFIED','physical':'BLOCKED','overall':'NO_GO'}
(out/'integration75-review.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
