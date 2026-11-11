"""F16 A5 conformance in independent no-hardlink clones, never worktrees."""
import ast,hashlib,json,os,pathlib,subprocess,textwrap,uuid
root=pathlib.Path(__file__).resolve().parents[1];repo=root/'work/review5-f16-fixed';out=root/'outputs/phase28';out.mkdir(exist_ok=True);head='db455c4926ddd50d0be7c3c615a8e4c073d12775';old='6bcf5475023a8f6a9733d02ad899064d0d83be95'
def git(*args):return subprocess.check_output(['git','-C',str(repo),'--no-replace-objects',*args])
assert set(git('diff','--name-only',old,head).decode().splitlines())=={'.github/workflows/agent5-components.yml','docs/scheduler/components.md','docs/scheduler/f16-no-replacement-object-binding.md'}
for path in ['scheduler_components/durable.py','tests/test_agent5_scheduler_components.py','docs/scheduler/component-test-inventory-v2.json']:assert git('show',old+':'+path)==git('show',head+':'+path)
def code(ref):return textwrap.dedent(git('show',ref+':.github/workflows/agent5-components.yml').decode().split("          python - <<'PY'\n",1)[1].split('          PY',1)[0])
newcode=code(head)
tree=ast.parse(newcode);source_git_calls=[]
for n in ast.walk(tree):
 if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='check_output' and n.args and isinstance(n.args[0],ast.List):
  parts=n.args[0].elts
  if parts and isinstance(parts[0],ast.Constant) and parts[0].value=='git':assert isinstance(parts[1],ast.Constant) and parts[1].value=='--no-replace-objects';source_git_calls.append(n.lineno)
assert len(source_git_calls)==3
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
cases={'old_blob_RED':{'ref':old,'replace':'blob'},'old_tree_RED':{'ref':old,'replace':'tree'},'clean':{},'blob_replacement':{'replace':'blob'},'tree_replacement':{'replace':'tree'},'hidden_source':{'comment':'scheduler_components/durable.py'},'hidden_test':{'comment':'tests/test_agent5_scheduler_components.py'},'hidden_inventory':{'comment':'docs/scheduler/component-test-inventory-v2.json'},'hidden_workflow':{'comment':'.github/workflows/agent5-components.yml'},'CRLF_source':{'crlf':True},'missing_source':{'missing':True},'hidden_post_source':{'inject':"items[0].addCleanup(lambda:(pathlib.Path('scheduler_components/durable.py').write_bytes(pathlib.Path('scheduler_components/durable.py').read_bytes()+b'\\n# A8 hidden post-source\\n'),subprocess.check_call(['git','update-index','--assume-unchanged','scheduler_components/durable.py'])))"},'wrong_ID_same30':{'inject':"items[0].id=lambda:'A8_WRONG_ID'"},'skip':{'inject':"getattr(items[0],items[0]._testMethodName).__func__.__unittest_skip__=True"}}
results={};path='scheduler_components/durable.py'
for name,options in cases.items():
 ref=options.get('ref',head);source=root/'work'/('a5-f16-'+name+'-'+uuid.uuid4().hex[:8]);subprocess.run(['git','clone','--no-hardlinks','--no-checkout',str(repo),str(source)],check=True,capture_output=True);subprocess.run(['git','-C',str(source),'-c','core.autocrlf=false','-c','core.eol=lf','checkout','--detach',ref],check=True,capture_output=True)
 assert (source/'.git').is_dir();common=subprocess.check_output(['git','-C',str(source),'--no-replace-objects','rev-parse','--git-common-dir']).decode().strip();assert (source/common).resolve()==(source/'.git').resolve()
 target=source/path
 if 'replace' in options:
  target.write_bytes(target.read_bytes()+b'\n# A8 replacement-only negative\n')
  if options['replace']=='blob':
   original=subprocess.check_output(['git','-C',str(source),'--no-replace-objects','rev-parse',ref+':'+path]).decode().strip();replacement=subprocess.check_output(['git','-C',str(source),'--no-replace-objects','hash-object','-w','--no-filters',path]).decode().strip();subprocess.run(['git','-C',str(source),'update-index','--assume-unchanged',path],check=True)
  else:
   original=subprocess.check_output(['git','-C',str(source),'--no-replace-objects','rev-parse',ref+'^{tree}']).decode().strip();subprocess.run(['git','-C',str(source),'-c','core.autocrlf=false','add','--',path],check=True);replacement=subprocess.check_output(['git','-C',str(source),'--no-replace-objects','write-tree']).decode().strip()
  subprocess.run(['git','-C',str(source),'replace',original,replacement],check=True)
 if 'comment' in options:
  p=source/options['comment'];p.write_bytes(p.read_bytes()+(b'\n ' if p.suffix=='.json' else b'\n# A8 hidden source\n'));subprocess.run(['git','-C',str(source),'update-index','--assume-unchanged',options['comment']],check=True)
 if options.get('crlf'):target.write_bytes(target.read_bytes().replace(b'\n',b'\r\n'));subprocess.run(['git','-C',str(source),'update-index','--assume-unchanged',path],check=True)
 if options.get('missing'):target.unlink();subprocess.run(['git','-C',str(source),'update-index','--assume-unchanged',path],check=True)
 folder=out/name;folder.mkdir(exist_ok=True);temp=root/'work'/('a5-f16-temp-'+name);temp.mkdir(exist_ok=True)
 env={k:v for k,v in os.environ.items() if not k.startswith('GITHUB_')};env.pop('GIT_NO_REPLACE_OBJECTS',None);env.update(EXPECTED_SOURCE_SHA=ref,EVIDENCE_DIR=str(folder),PYTHONDONTWRITEBYTECODE='1',TEMP=str(temp),TMP=str(temp))
 boot='import sys,os;sys.path[:0]=[os.getcwd(),'+repr(str(root/'work/integration-review-deps'))+'];\n';injected=prelude.replace('__INJECT__',options['inject']) if 'inject' in options else ''
 run=subprocess.run([str(root/'work/audit-venv/Scripts/python.exe'),'-I','-B','-c',boot+injected+code(ref)],cwd=source,env=env,capture_output=True,timeout=60);(folder/'stdout.log').write_bytes(run.stdout);(folder/'stderr.log').write_bytes(run.stderr);r=json.loads((folder/'receipt.json').read_text())
 assert hashlib.sha256((folder/'component-tests.log').read_bytes()).hexdigest()==r['test_log_sha256']
 if name.startswith('old_') or name=='clean':assert run.returncode==0 and r['passed'] and r['tests_run']==30 and r['skips']==r['failures']==r['errors']==0
 else:assert run.returncode!=0 and r['passed'] is False
 if name in ('blob_replacement','tree_replacement'):assert r['tests_run']==0 and not r['source_before']['protected_inputs_valid']
 results[name]={'head':ref,'exit_code':run.returncode,'passed':r['passed'],'tests':r['tests_run'],'skips':r['skips'],'source_valid_before':r['source_before']['protected_inputs_valid'],'source_valid_after':r['source_after']['protected_inputs_valid'],'own_dot_git_common_dir':True}
assert not git('for-each-ref','refs/replace').strip()
report={'head':head,'tree':git('rev-parse','HEAD^{tree}').decode().strip(),'previous':old,'delta':'WORKFLOW_TWO_DOCS_ONLY_PRODUCT_TEST_INVENTORY_IDENTICAL','all_three_source_git_subprocess_sites_force_no_replace':source_git_calls,'cases':results,'F16_A5_scope':'FIX_VERIFIED_OFFLINE_EXACT_SOURCE','F16_global':'OPEN_A3_ROOT_AND_OTHER_APPLICABLE_GUARDS_PENDING','prior_F15_regression':'NO_REGRESSION_IN_TESTED_CONTROLS','hosted':'NOT_QUALIFIED','runtime':'NOT_QUALIFIED','physical':'BLOCKED','overall':'NO_GO'}
(out/'scheduler-f16-review.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
