"""Independent F17 cache fix and untracked-import conformance in own clones."""
import ast,hashlib,importlib.util,json,os,pathlib,subprocess,sys,textwrap,uuid
r=pathlib.Path(__file__).resolve().parents[1];repo=r/'work/review5-f16-fixed';out=r/'outputs/phase41';out.mkdir(exist_ok=True);head='d4b7475be79331f9e2d739b51aebc9442223e298';old='0d6eb4386a721e2bbd6e5e9f6808573a4cfbe267';targetpath='scheduler_components/runtime.py'
def git(at,*args):return subprocess.check_output(['git','--no-replace-objects','-C',str(at),*args])
def read(ref,path):return git(repo,'show',ref+':'+path)
assert git(repo,'rev-parse',head+'^{tree}').decode().strip()=='4505a761949e2af1a03a7ae3bf487c68ec6a5769'
changed=git(repo,'diff','--name-only',old,head).decode().splitlines();assert set(changed)=={'.github/workflows/agent5-components.yml','docs/scheduler/runtime-f17-bytecode-binding.md'},changed
assert not git(repo,'diff','--name-only',old,head,'--','scheduler_components','tests','docs/scheduler/component-test-inventory-v3.json').strip()
workflow=read(head,'.github/workflows/agent5-components.yml').decode();assert "python -I -B - <<'PY'" in workflow
code=textwrap.dedent(workflow.split("          python -I -B - <<'PY'\n",1)[1].split('          PY',1)[0])
prelude='''import unittest,pathlib
_discover=unittest.defaultTestLoader.discover
_used=False
def flat(value):
 for item in value:
  if isinstance(item,unittest.TestSuite):yield from flat(item)
  else:yield item
def discover(*a,**k):
 global _used
 suite=_discover(*a,**k);items=list(flat(suite))
 if not _used:
  _used=True
  __INJECT__
 return suite
unittest.defaultTestLoader.discover=discover
'''
cases=('clean','repo_cache','ambient_cache','explicit_cache_prefix','preloaded_runtime','post_cache','untracked_test','root_shadow_typing','blob_replace','tree_replace','wrong_ID','skip');results={}
for name in cases:
 source=r/'work'/('a5-f17fix-'+name+'-'+uuid.uuid4().hex[:8]);subprocess.run(['git','clone','--no-hardlinks','--no-checkout',str(repo),str(source)],check=True,capture_output=True);subprocess.run(['git','-C',str(source),'-c','core.autocrlf=false','-c','core.eol=lf','checkout','--detach',head],check=True,capture_output=True)
 assert (source/'.git').is_dir() and not (source/'.git/objects/info/alternates').exists();assert (source/git(source,'rev-parse','--git-common-dir').decode().strip()).resolve()==(source/'.git').resolve()
 folder=out/name;folder.mkdir(exist_ok=True);marker=folder/'untracked-executed.txt';target=source/targetpath;temp=r/'work'/('a5-f17fix-temp-'+uuid.uuid4().hex[:8]);temp.mkdir();prefix=temp/'ambient-prefix';prefix.mkdir()
 if name in ('repo_cache','ambient_cache'):
  import importlib._bootstrap_external as external
  original=target.read_bytes();compiled=compile(original+b'\nopen('+repr(str(marker)).encode()+b',"w").write("A8_IMPORT_WITNESS")\n',str(target),'exec')
  previous=sys.pycache_prefix
  try:
   sys.pycache_prefix=str(prefix) if name=='ambient_cache' else None;cache=pathlib.Path(importlib.util.cache_from_source(str(target)))
  finally:sys.pycache_prefix=previous
  cache.parent.mkdir(parents=True,exist_ok=True);cache.write_bytes(external._code_to_timestamp_pyc(compiled,int(target.stat().st_mtime),len(original)))
 if name=='untracked_test':(source/'tests/a8_untracked_helper.py').write_text('A8_UNTRACKED=True\n')
 if name=='root_shadow_typing':
  import sysconfig
  typing=pathlib.Path(sysconfig.get_path('stdlib'))/'typing.py'
  (source/'typing.py').write_text('exec(compile(open('+repr(str(typing))+',"rb").read(),'+repr(str(typing))+',"exec"),globals())\nopen('+repr(str(marker))+',"w").write("A8_ROOT_SHADOW_TYPING_WITNESS")\n')
 if name in ('blob_replace','tree_replace'):
  target.write_bytes(target.read_bytes()+b'\n# A8 primary blob negative\n')
  if name=='blob_replace':
   original=git(source,'rev-parse',head+':'+targetpath).decode().strip();replacement=git(source,'hash-object','-w','--no-filters',targetpath).decode().strip();subprocess.run(['git','-C',str(source),'update-index','--assume-unchanged',targetpath],check=True)
  else:
   original=git(source,'rev-parse',head+'^{tree}').decode().strip();subprocess.run(['git','-C',str(source),'-c','core.autocrlf=false','add','--',targetpath],check=True);replacement=git(source,'write-tree').decode().strip()
  subprocess.run(['git','-C',str(source),'replace',original,replacement],check=True)
 env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')};env.update(EXPECTED_SOURCE_SHA=head,EVIDENCE_DIR=str(folder),TEMP=str(temp),TMP=str(temp))
 if name=='ambient_cache':env['PYTHONPYCACHEPREFIX']=str(prefix)
 boot="import sys,ipaddress\nsys.path.insert(0,"+repr(str(r/'work/integration-review-deps'))+")\ndef guard(event,args):\n if event in ('socket.connect','socket.bind') and (not isinstance(args[1],tuple) or not ipaddress.ip_address(args[1][0]).is_loopback):raise RuntimeError('A8_NONLOOPBACK_DENIED')\nsys.addaudithook(guard)\n"
 if name=='preloaded_runtime':boot+="import types;sys.modules['scheduler_components.runtime']=types.ModuleType('scheduler_components.runtime')\n"
 injection={'post_cache':"items[0].addCleanup(lambda:(pathlib.Path('scheduler_components/__pycache__').mkdir(exist_ok=True),pathlib.Path('scheduler_components/__pycache__/a8.pyc').write_bytes(b'A8 post cache'))) ",'wrong_ID':"items[0].id=lambda:'A8_WRONG_ID'",'skip':"getattr(items[0],items[0]._testMethodName).__func__.__unittest_skip__=True"}.get(name)
 if injection:boot+=prelude.replace('__INJECT__',injection)
 args=[str(r/'work/audit-venv/Scripts/python.exe'),'-I','-B']+(['-X','pycache_prefix='+str(prefix)] if name=='explicit_cache_prefix' else [])+['-c',boot+code]
 p=subprocess.run(args,cwd=source,env=env,capture_output=True,timeout=60);(folder/'stdout.log').write_bytes(p.stdout);(folder/'stderr.log').write_bytes(p.stderr);receipt=json.loads((folder/'receipt.json').read_text());assert hashlib.sha256((folder/'component-tests.log').read_bytes()).hexdigest()==receipt['test_log_sha256']
 if name in ('clean','ambient_cache'):assert p.returncode==0 and receipt['passed'] and receipt['tests_run']==52 and receipt['skips']==0
 else:assert p.returncode!=0 and receipt['passed'] is False
 if name in ('repo_cache','ambient_cache'):assert not marker.exists()
 if name=='root_shadow_typing':assert not marker.exists() and receipt['tests_run']==0
 results[name]=dict(exit_code=p.returncode,passed=receipt['passed'],tests=receipt['tests_run'],skips=receipt['skips'],source_valid_before=receipt['source_before']['protected_inputs_valid'],source_valid_after=receipt['source_after']['protected_inputs_valid'],marker_executed=marker.exists(),raw16_match=all(x['matches_committed_blob'] for x in receipt['source_before']['protected_files']),own_common_dot_git=True)
report=dict(head=head,tree='4505a761949e2af1a03a7ae3bf487c68ec6a5769',product_tests_inventory_unchanged=True,cases=results,bytecode_vector='FIX_VERIFIED_OFFLINE_EXACT_SOURCE',F17_A5='FIX_VERIFIED_OFFLINE_EXACT_SOURCE',F17_global='OPEN_PENDING_ROOT_AND_OTHER_APPLICABLE_GUARD_REVIEW',qualification='SOURCE_IMPORT_CONTROLS_VERIFIED_OFFLINE_NOT_NATIVE_OR_HOSTED',hosted='NOT_QUALIFIED',native_authority='ABSENT',physical='BLOCKED',overall='NO_GO');(out/'f17-recheck.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
