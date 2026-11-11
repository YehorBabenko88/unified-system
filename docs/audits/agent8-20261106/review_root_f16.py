"""Independent Root final-integration F16 controls in disposable own-Git clones."""
import ast,hashlib,json,os,pathlib,re,subprocess,textwrap,uuid
root=pathlib.Path(__file__).resolve().parents[1];repo=root/'work/review-integration75';out=root/'outputs/phase30';out.mkdir(exist_ok=True)
head='18085568df01bdbc4df74404e3c650ec30bb7d6b';old='c9f3735c1efa2d5ae0e2dfbe52987a49c520bdf5';parent='dd8b4ff9ace0a75dd81d0ab654e97a1e2319259a';path='scheduler_components/durable.py'
def git(at,*args):return subprocess.check_output(['git','--no-replace-objects','-C',str(at),*args])
assert git(repo,'rev-parse',head+'^{tree}').decode().strip()=='ebdd08b00d78c0c130d78747fed717bc636793bf'
assert set(git(repo,'diff','--name-only',parent,head).decode().splitlines())=={'.github/workflows/final-integration.yml','docs/ci/raw-git-object-binding.md'}
inventory=json.loads(git(repo,'show',head+':release/component-test-inventory.json'));assert inventory['expected_count']==75
unchanged=git(repo,'diff','--name-only',old,head,'--','tests','scheduler_components','operator_control','integration_registry','release/component-test-inventory.json','scripts/network_readonly_probe.ps1').decode();assert not unchanged,unchanged
def code(ref):return textwrap.dedent(git(repo,'show',ref+':.github/workflows/final-integration.yml').decode().split('        shell: python\n        run: |\n',1)[1].split('      - uses:',1)[0])
newcode=code(head);assert "source_git = ['git', '--no-replace-objects']" in newcode
calls=[n for n in ast.walk(ast.parse(newcode)) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='check_output'];assert len(calls)==2
assert all(isinstance(n.args[0],ast.List) and isinstance(n.args[0].elts[0],ast.Starred) and n.args[0].elts[0].value.id=='source_git' for n in calls)
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
cases={'old_blob_RED':(old,'blob',None),'old_tree_RED':(old,'tree',None),'clean':(head,None,None),'blob':(head,'blob',None),'tree':(head,'tree',None),'post_hidden':(head,None,"items[0].addCleanup(lambda:(pathlib.Path('scheduler_components/durable.py').write_bytes(pathlib.Path('scheduler_components/durable.py').read_bytes()+b'\\n# A8 post mutation\\n'),subprocess.check_call(['git','update-index','--assume-unchanged','scheduler_components/durable.py'])))"),'wrong_id':(head,None,"items[0].id=lambda:'A8_WRONG_ID'"),'skip':(head,None,"getattr(items[0],items[0]._testMethodName).__func__.__unittest_skip__=True")}
results={}
for name,(ref,replace,inject) in cases.items():
 source=root/'work'/('root-f16-'+name+'-'+uuid.uuid4().hex[:8]);subprocess.run(['git','clone','--no-hardlinks','--no-checkout',str(repo),str(source)],check=True,capture_output=True);subprocess.run(['git','-C',str(source),'-c','core.autocrlf=false','-c','core.eol=lf','checkout','--detach',ref],check=True,capture_output=True)
 assert (source/'.git').is_dir() and not (source/'.git/objects/info/alternates').exists();assert (source/git(source,'rev-parse','--git-common-dir').decode().strip()).resolve()==(source/'.git').resolve()
 target=source/path
 if replace:
  target.write_bytes(target.read_bytes()+b'\n# A8 harmless replacement mutation\n')
  if replace=='blob':
   original=git(source,'rev-parse',ref+':'+path).decode().strip();replacement=git(source,'hash-object','-w','--no-filters',path).decode().strip();subprocess.run(['git','-C',str(source),'update-index','--assume-unchanged',path],check=True)
  else:
   original=git(source,'rev-parse',ref+'^{tree}').decode().strip();subprocess.run(['git','-C',str(source),'-c','core.autocrlf=false','add','--',path],check=True);replacement=git(source,'write-tree').decode().strip()
  subprocess.run(['git','-C',str(source),'replace',original,replacement],check=True)
 folder=out/name;folder.mkdir(exist_ok=True);scratch=root/'work'/('root-f16-temp-'+name);scratch.mkdir(exist_ok=True)
 env={k:v for k,v in os.environ.items() if not k.startswith('GITHUB_') and not k.startswith('GIT_')};env.update(EXPECTED_HEAD=ref,GITHUB_RUN_ID='LOCAL_A8_NOT_HOSTED',GITHUB_RUN_ATTEMPT='LOCAL_ONLY',PYTHONDONTWRITEBYTECODE='1',TEMP=str(scratch),TMP=str(scratch))
 boot='import sys,os;sys.path[:0]=[os.getcwd(),'+repr(str(root/'work/integration-review-deps'))+'];\n'
 p=subprocess.run([str(root/'work/audit-venv/Scripts/python.exe'),'-I','-B','-c',boot+(prelude.replace('__INJECT__',inject) if inject else '')+code(ref)],cwd=source,env=env,capture_output=True,timeout=120)
 (folder/'stdout.log').write_bytes(p.stdout);(folder/'stderr.log').write_bytes(p.stderr)
 receipt=source/'partial-integration-ci-evidence.json';r=json.loads(receipt.read_text()) if receipt.exists() else None;log=source/'partial-integration-ci-tests.log';ran=0
 if log.exists():
  raw=log.read_bytes();(folder/'tests.log').write_bytes(raw);ran=int(re.findall(rb'Ran ([0-9]+) tests?',raw)[-1])
 if r:(folder/'receipt.json').write_text(json.dumps(r,indent=2));assert hashlib.sha256(log.read_bytes()).hexdigest()==r['test_log_sha256']
 if name.startswith('old_') or name=='clean':assert p.returncode==0 and r['tests']==75 and r['skipped']==r['failures']==r['errors']==0 and r['source_before']==r['source_after']
 else:assert p.returncode!=0,(name,p.stdout,p.stderr)
 if name in ('blob','tree'):assert not r and ran==0
 if name=='clean':
  assert r['source_before']['object_resolution']=='PRIMARY_GIT_OBJECTS_NO_REPLACE'
  for namepath,entry in r['source_before']['files'].items():
   raw=(source/namepath).read_bytes();oid=git(source,'rev-parse',ref+':'+namepath).decode().strip();assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==oid==entry['git_blob'];assert hashlib.sha256(raw).hexdigest()==entry['raw_sha256']
 results[name]=dict(head=ref,exit_code=p.returncode,tests=ran,receipt_emitted=bool(r),source_binding_passed=r.get('source_binding_passed') if r else None,skips=r.get('skipped') if r else None,protected_inputs=len(r['source_before']['files']) if r else None,independent_common_git=True)
assert not git(repo,'for-each-ref','refs/replace').strip()
report=dict(head=head,tree='ebdd08b00d78c0c130d78747fed717bc636793bf',parent=parent,previous=old,fix_delta='WORKFLOW_PLUS_DOC_ONLY',prior75_inventory_tests_and_selected_product_paths_unchanged=True,source_git_subprocess_sites=2,cases=results,F16_root='FIX_VERIFIED_OFFLINE_EXACT_SOURCE',F16_global='OPEN',hosted='NOT_QUALIFIED',physical='BLOCKED',tailscale_removal='BLOCKED',overall='NO_GO')
(out/'root-f16-review.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
