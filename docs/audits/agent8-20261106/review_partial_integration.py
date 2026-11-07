"""Independent bounded source/CI review; synthetic components only."""
import hashlib,json,os,pathlib,subprocess,sys,uuid,textwrap
ROOT=pathlib.Path(__file__).resolve().parents[1];repo=ROOT/'work/review-integration-56f';out=ROOT/'outputs/phase11';out.mkdir(exist_ok=True)
head='56f4215506f3a6efb7404591753facd69204a1ee'
def git(*args):return subprocess.check_output(['git','-C',str(repo),*args])
def files(ref):return dict(row.split('\t',1)[::-1] for row in git('ls-tree','-r',ref).decode().splitlines())
def same(path,left,right):assert git('rev-parse',left+':'+path)==git('rev-parse',right+':'+path),path
sources={'scheduler':'942e5f1d1efb28f97fb5eaae7a216424938dd738','control':'0b3af3e872b49ed1848815f7f9ffd42444f89b24','fixtures':'2626e939a7ed44bfb37aa354490329a7260cc24b'}
base='80c25306a7b0230a39cf1150172844ec94452529'
for ref in [base,*sources.values(),'8171eebd6bfbcc83fd82038c6d9f42d012ac822a','2df6f5c2f77f4d883bad1a8623dd8375db529be0']:
 subprocess.run(['git','-C',str(repo),'merge-base','--is-ancestor',ref,head],check=True)
base_files=files(base);head_files=files(head)
assert all(name in head_files and value==head_files[name] for name,value in base_files.items() if name!='.gitattributes')
assert git('show',head+':.gitattributes')==git('show',base+':.gitattributes')+b'release/** -text\n'
matches={}
for label,ref in sources.items():
 parent='8171eebd6bfbcc83fd82038c6d9f42d012ac822a^' if label=='fixtures' else '2df6f5c2f77f4d883bad1a8623dd8375db529be0'
 paths=git('diff','--name-only',parent,ref).decode().splitlines()
 for path in paths:same(path,ref,head)
 matches[label]=paths
workflow=(repo/'.github/workflows/final-integration.yml').read_text()
code=textwrap.dedent(workflow.split('        shell: python\n        run: |\n',1)[1].split('      - uses:',1)[0])
matrix={'os':['ubuntu-24.04','windows-latest'],'python':['3.11','3.12']}
assert "os: [ubuntu-24.04, windows-latest]" in workflow and "python: ['3.11', '3.12']" in workflow
prelude='''
import unittest,pathlib,subprocess
_load=unittest.defaultTestLoader.loadTestsFromName
_used=False
def _flat(value):
 for item in value:
  if isinstance(item,unittest.TestSuite):yield from _flat(item)
  else:yield item
def _wrapped(*args,**kwargs):
 global _used
 suite=_load(*args,**kwargs);items=list(_flat(suite))
 if not _used:
  _used=True
  __INJECTION__
 return suite
unittest.defaultTestLoader.loadTestsFromName=_wrapped
'''
cases={'clean':{},'tracked_comment':{'comment':True},'hidden_comment':{'comment':True,'assume':True},'wrong_head':{'expected':'0'*40},'missing_id':{'inject':'return unittest.TestSuite(items[:-1])'},'duplicate_id':{'inject':'return unittest.TestSuite(items[:-1]+[items[0]])'},'skip':{'inject':'getattr(items[0],items[0]._testMethodName).__func__.__unittest_skip__=True'},'hidden_post_tamper':{'inject':"items[0].addCleanup(lambda:(pathlib.Path('unified_system/control_api_readonly.py').write_bytes(pathlib.Path('unified_system/control_api_readonly.py').read_bytes()+b'\\n# hidden post-test tamper\\n'),subprocess.check_call(['git','update-index','--assume-unchanged','unified_system/control_api_readonly.py'])))"}}
results={}
for name,options in cases.items():
 source=ROOT/'work'/('integration-guard-'+name+'-'+uuid.uuid4().hex[:8])
 subprocess.run(['git','clone','--local','--no-checkout',str(repo),str(source)],check=True,capture_output=True)
 subprocess.run(['git','-C',str(source),'-c','core.autocrlf=false','-c','core.eol=lf','checkout','--detach',head],check=True,capture_output=True)
 target=source/'unified_system/control_api_readonly.py'
 if options.get('comment'):target.write_bytes(target.read_bytes()+b'\n# auditor pre-test tamper\n')
 if options.get('assume'):subprocess.run(['git','-C',str(source),'update-index','--assume-unchanged','unified_system/control_api_readonly.py'],check=True)
 injected=prelude.replace('__INJECTION__',options['inject']) if 'inject' in options else ''
 env={k:v for k,v in os.environ.items() if not k.startswith('GITHUB_')};env.update(EXPECTED_HEAD=options.get('expected',head),GITHUB_RUN_ID='LOCAL_A8_NOT_HOSTED',GITHUB_RUN_ATTEMPT='LOCAL_ONLY',PYTHONDONTWRITEBYTECODE='1')
 boot='import sys,os;sys.path[:0]=[os.getcwd(),'+repr(str(ROOT/'work/integration-review-deps'))+'];\n'
 run=subprocess.run([sys.executable,'-I','-B','-c',boot+injected+code],cwd=source,env=env,capture_output=True,timeout=60)
 folder=out/name;folder.mkdir(exist_ok=True);(folder/'stdout.log').write_bytes(run.stdout);(folder/'stderr.log').write_bytes(run.stderr)
 receipt=source/'partial-integration-ci-evidence.json'
 if name=='clean':
  report=json.loads(receipt.read_text());assert run.returncode==0 and report['tests']==59 and report['skipped']==report['errors']==report['failures']==0
  assert report['source_before']==report['source_after'];assert len(set(report['mandatory_test_ids']))==59
  log=(source/'partial-integration-ci-tests.log').read_bytes();assert hashlib.sha256(log).hexdigest()==report['test_log_sha256']
  (folder/'receipt.json').write_text(json.dumps(report,indent=2));(folder/'tests.log').write_bytes(log)
 else:assert run.returncode!=0,('NEGATIVE_ACCEPTED',name)
 results[name]={'exit_code':run.returncode,'expected':'ACCEPT_59' if name=='clean' else 'REJECT','receipt_emitted':receipt.exists(),'reason':[r for r in run.stderr.decode(errors='replace').splitlines() if 'AssertionError' in r][-1:]}
result={'head':head,'tree':git('rev-parse',head+'^{tree}').decode().strip(),'base':base,'registry_base_files_unchanged_except_attributes':True,'attributes_only_addition':'release/** -text','merged_source_blob_matches':matches,'source_heads':sources,'cases':results,'workflow_code_sha256':hashlib.sha256(code.encode()).hexdigest(),'mandatory_matrix_inspected':matrix,'scope':'LOCAL_WINDOWS_EXACT_CI_BLOCK_SOURCE_CHECKED_SYNTHETIC_COMPONENTS_ONLY','hosted':'NOT_QUALIFIED','runtime':'NOT_QUALIFIED','physical':'BLOCKED','overall':'NO_GO'}
(out/'integration-review.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
