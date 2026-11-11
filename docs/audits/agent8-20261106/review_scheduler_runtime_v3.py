"""Independent A5 v3 runtime/F16 controls, synthetic ports and private storage only."""
import ast,hashlib,importlib.util,json,os,pathlib,subprocess,textwrap,uuid
r=pathlib.Path(__file__).resolve().parents[1];repo=r/'work/review5-f16-fixed';out=r/'outputs/phase37';out.mkdir(exist_ok=True);head='462935b53ef25d4d9be2371bad1cd7230c65f2e7';old='db455c4926ddd50d0be7c3c615a8e4c073d12775'
def git(at,*args):return subprocess.check_output(['git','--no-replace-objects','-C',str(at),*args])
def read(ref,path):return git(repo,'show',ref+':'+path)
metadata=subprocess.check_output(['gh','pr','view','24','--repo','YehorBabenko88/unified-system','--json','headRefOid,baseRefOid,isDraft,files,url']);(out/'primary-pr24.json').write_bytes(metadata);assert json.loads(metadata)['headRefOid']==head
assert git(repo,'rev-parse',head+'^{tree}').decode().strip()=='8c7f7d8d3cd5a6b77817d9e7a1761672484e921c'
for path in ['scheduler_components/durable.py','scheduler_components/authority_boundary.py','scheduler_components/placement.py','scheduler_components/schedules.py','tests/test_agent5_scheduler_components.py','docs/scheduler/component-test-inventory-v2.json']:assert read(old,path)==read(head,path)
v2=json.loads(read(head,'docs/scheduler/component-test-inventory-v2.json'));v3=json.loads(read(head,'docs/scheduler/component-test-inventory-v3.json'));assert v3['expected_count']==len(v3['expected_ids'])==len(set(v3['expected_ids']))==52 and set(v2['expected_ids'])<=set(v3['expected_ids']) and len(v2['expected_ids'])==30
code=textwrap.dedent(read(head,'.github/workflows/agent5-components.yml').decode().split("          python - <<'PY'\n",1)[1].split('          PY',1)[0]);calls=[]
for n in ast.walk(ast.parse(code)):
 if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='check_output' and n.args and isinstance(n.args[0],ast.List) and isinstance(n.args[0].elts[0],ast.Constant) and n.args[0].elts[0].value=='git':
  assert n.args[0].elts[1].value=='--no-replace-objects';calls.append(n.lineno)
assert len(calls)==3
prelude='''import unittest,pathlib,subprocess
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
cases={'clean':{},'blob_replace':{'replace':'blob'},'tree_replace':{'replace':'tree'},'hidden_benchmark':{'path':'scheduler_components/benchmarks.py'},'hidden_inventory':{'path':'docs/scheduler/component-test-inventory-v3.json'},'missing_runtime':{'missing':True},'hidden_post_runtime':{'inject':"items[0].addCleanup(lambda:(pathlib.Path('scheduler_components/runtime.py').write_bytes(pathlib.Path('scheduler_components/runtime.py').read_bytes()+b'\\n# post-test change\\n'),subprocess.check_call(['git','update-index','--assume-unchanged','scheduler_components/runtime.py'])))"},'wrong_ID_same52':{'inject':"items[0].id=lambda:'A8_WRONG_ID'"},'skip':{'inject':"getattr(items[0],items[0]._testMethodName).__func__.__unittest_skip__=True"},'bytecode_only':{'bytecode':True}}
results={};clean=None;path='scheduler_components/runtime.py'
for name,options in cases.items():
 source=r/'work'/('a5-v3-'+name+'-'+uuid.uuid4().hex[:8]);subprocess.run(['git','clone','--no-hardlinks','--no-checkout',str(repo),str(source)],check=True,capture_output=True);subprocess.run(['git','-C',str(source),'-c','core.autocrlf=false','-c','core.eol=lf','checkout','--detach',head],check=True,capture_output=True)
 assert (source/'.git').is_dir() and not (source/'.git/objects/info/alternates').exists();assert (source/git(source,'rev-parse','--git-common-dir').decode().strip()).resolve()==(source/'.git').resolve()
 target=source/path;folder=out/name;folder.mkdir(exist_ok=True);marker=folder/'bytecode-executed.txt'
 if options.get('replace'):
  target.write_bytes(target.read_bytes()+b'\n# A8 replacement mutation\n')
  if options['replace']=='blob':
   original=git(source,'rev-parse',head+':'+path).decode().strip();replacement=git(source,'hash-object','-w','--no-filters',path).decode().strip();subprocess.run(['git','-C',str(source),'update-index','--assume-unchanged',path],check=True)
  else:
   original=git(source,'rev-parse',head+'^{tree}').decode().strip();subprocess.run(['git','-C',str(source),'-c','core.autocrlf=false','add','--',path],check=True);replacement=git(source,'write-tree').decode().strip()
  subprocess.run(['git','-C',str(source),'replace',original,replacement],check=True)
 if 'path' in options:
  changed=source/options['path'];changed.write_bytes(changed.read_bytes()+(b'\n ' if changed.suffix=='.json' else b'\n# A8 hidden mutation\n'));subprocess.run(['git','-C',str(source),'update-index','--assume-unchanged',options['path']],check=True)
 if options.get('missing'):target.unlink();subprocess.run(['git','-C',str(source),'update-index','--assume-unchanged',path],check=True)
 bytecode_hash=None
 if options.get('bytecode'):
  import importlib._bootstrap_external as external
  raw=target.read_bytes();compiled=compile(raw+b'\nopen('+repr(str(marker)).encode()+b',"w").write("A8_INERT_BYTECODE_ONLY_WITNESS")\n',str(target),'exec');cache=pathlib.Path(importlib.util.cache_from_source(str(target)));cache.parent.mkdir();payload=external._code_to_timestamp_pyc(compiled,int(target.stat().st_mtime),len(raw));cache.write_bytes(payload);bytecode_hash=hashlib.sha256(payload).hexdigest()
 temp=r/'work'/('a5-v3-temp-'+uuid.uuid4().hex[:8]);temp.mkdir();env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')};env.update(EXPECTED_SOURCE_SHA=head,EVIDENCE_DIR=str(folder),PYTHONDONTWRITEBYTECODE='1',TEMP=str(temp),TMP=str(temp))
 boot="import sys,os,ipaddress\nsys.path[:0]=[os.getcwd(),"+repr(str(r/'work/integration-review-deps'))+"]\ndef guard(event,args):\n if event in ('socket.connect','socket.bind') and (not isinstance(args[1],tuple) or not ipaddress.ip_address(args[1][0]).is_loopback):raise RuntimeError('A8_NONLOOPBACK_DENIED')\nsys.addaudithook(guard)\n"
 process=subprocess.run([str(r/'work/audit-venv/Scripts/python.exe'),'-I','-B','-c',boot+(prelude.replace('__INJECT__',options['inject']) if 'inject' in options else '')+code],cwd=source,env=env,capture_output=True,timeout=60);(folder/'stdout.log').write_bytes(process.stdout);(folder/'stderr.log').write_bytes(process.stderr);receipt=json.loads((folder/'receipt.json').read_text());assert hashlib.sha256((folder/'component-tests.log').read_bytes()).hexdigest()==receipt['test_log_sha256']
 if name=='clean':assert process.returncode==0 and receipt['passed'] and receipt['tests_run']==52 and receipt['skips']==0 and len(receipt['source_before']['protected_files'])==16;clean=source
 elif name=='bytecode_only':assert process.returncode==0 and receipt['passed'] and receipt['tests_run']==52 and marker.read_text()=='A8_INERT_BYTECODE_ONLY_WITNESS';assert receipt['source_before']==receipt['source_after']
 else:assert process.returncode!=0 and receipt['passed'] is False
 results[name]=dict(exit_code=process.returncode,passed=receipt['passed'],tests=receipt['tests_run'],skips=receipt['skips'],source_valid_before=receipt['source_before']['protected_inputs_valid'],source_valid_after=receipt['source_after']['protected_inputs_valid'],bytecode_marker_executed=marker.exists(),bytecode_sha256=bytecode_hash,own_common_dot_git=True)
assert clean and not git(repo,'for-each-ref','refs/replace').strip()
rows={}
for item in filter(None,git(clean,'ls-tree','-rz',head).split(b'\0')):
 meta,name=item.split(b'\t',1);raw=(clean/name.decode()).read_bytes();assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==meta.split()[2].decode();rows[name.decode()]=hashlib.sha256(raw).hexdigest()
report=dict(head=head,tree='8c7f7d8d3cd5a6b77817d9e7a1761672484e921c',old30module_and_product_bytes_unchanged=True,new_inventory=52,all_three_source_git_sites_no_replace=calls,raw_tracked_files=len(rows),raw_tracked_sha256=hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest(),cases=results,F16_A5='NO_REGRESSION_IN_TESTED_REPLACEMENT_CONTROLS',new_source_evidence_gap='UNTRACKED_CPYTHON_BYTECODE_EXECUTED_WITH_CLEAN_RAW_SOURCE_RECEIPT',native_authority='ABSENT_SYNTHETIC_PORTS_ONLY',hosted='NOT_QUALIFIED',physical='BLOCKED',overall='NO_GO')
(out/'scheduler-runtime-v3-review.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
