"""Exact A5 local journal/source guard review with auditor-owned clones only."""
import ast,hashlib,json,os,pathlib,subprocess,sys,textwrap,uuid
root=pathlib.Path(__file__).resolve().parents[1];repo=root/'work/review5-durable';out=root/'outputs/phase24';out.mkdir(exist_ok=True);head='175b48a2a0d2882669172abc5774bd71b42e2215';base='942e5f1d1efb28f97fb5eaae7a216424938dd738'
def git(*args):return subprocess.check_output(['git','-C',str(repo),*args])
assert set(git('diff','--name-only',base,head).decode().splitlines())=={'scheduler_components/durable.py','tests/test_agent5_scheduler_components.py','docs/scheduler/durable.md','docs/scheduler/components.md','docs/scheduler/component-test-inventory-v2.json','.github/workflows/agent5-components.yml'}
def methods(ref):
 tree=ast.parse(git('show',ref+':tests/test_agent5_scheduler_components.py'));return {(c.name,m.name):ast.dump(m,include_attributes=False) for c in tree.body if isinstance(c,ast.ClassDef) for m in c.body if isinstance(m,ast.FunctionDef) and m.name.startswith('test_')}
old,new=methods(base),methods(head);assert len(old)==15 and len(new)==30 and all(new[k]==v for k,v in old.items())
for path in ['scheduler_components/placement.py','scheduler_components/schedules.py','scheduler_components/authority_boundary.py']:assert git('show',base+':'+path)==git('show',head+':'+path)
workflow=(repo/'.github/workflows/agent5-components.yml').read_text();code=textwrap.dedent(workflow.split("          python - <<'PY'\n",1)[1].split('          PY',1)[0])
def identity():
 rows=[]
 for row in git('ls-tree','-rz',head).split(b'\0'):
  if not row:continue
  metadata,name=row.split(b'\t',1);mode,kind,oid=metadata.split();raw=(repo/name.decode()).read_bytes();assert kind==b'blob' and hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==oid.decode();rows.append([name.decode(),hashlib.sha256(raw).hexdigest()])
 return hashlib.sha256(json.dumps(rows).encode()).hexdigest()
before=identity()
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
cases={'clean':{},'visible_comment':{'comment':True},'hidden_comment':{'comment':True,'hidden':True},'wrong_head':{'expected':'0'*40},'missing_id':{'inject':'return unittest.TestSuite(items[:-1])'},'duplicate_id':{'inject':'return unittest.TestSuite(items[:-1]+[items[0]])'},'same_count_wrong_id':{'inject':"items[0].id=lambda:'auditor.SUBSTITUTED_ID'"},'skip':{'inject':"getattr(items[0],items[0]._testMethodName).__func__.__unittest_skip__=True"}}
results={}
for name,options in cases.items():
 source=root/'work'/('a5-durable-guard-'+name+'-'+uuid.uuid4().hex[:8]);subprocess.run(['git','clone','--local','--no-checkout',str(repo),str(source)],check=True,capture_output=True);subprocess.run(['git','-C',str(source),'-c','core.autocrlf=false','-c','core.eol=lf','checkout','--detach',head],check=True,capture_output=True)
 target=source/'scheduler_components/durable.py';committed=target.read_bytes()
 if options.get('comment'):target.write_bytes(committed+b'\n# A8 harmless source-binding probe\n')
 if options.get('hidden'):subprocess.run(['git','-C',str(source),'update-index','--assume-unchanged','scheduler_components/durable.py'],check=True)
 folder=out/name;folder.mkdir(exist_ok=True)
 env={k:v for k,v in os.environ.items() if not k.startswith('GITHUB_')};env.update(EXPECTED_SOURCE_SHA=options.get('expected',head),EVIDENCE_DIR=str(folder),PYTHONDONTWRITEBYTECODE='1')
 boot='import sys,os;sys.path[:0]=[os.getcwd(),'+repr(str(root/'work/integration-review-deps'))+'];\n'
 injected=prelude.replace('__INJECT__',options['inject']) if 'inject' in options else ''
 p=subprocess.run([str(root/'work/audit-venv/Scripts/python.exe'),'-I','-B','-c',boot+injected+code],cwd=source,env=env,capture_output=True,timeout=60)
 (folder/'stdout.log').write_bytes(p.stdout);(folder/'stderr.log').write_bytes(p.stderr);receipt=json.loads((folder/'receipt.json').read_text())
 if name in ('clean','hidden_comment'):assert p.returncode==0 and receipt['passed'] and receipt['tests_run']==30 and receipt['skips']==receipt['failures']==receipt['errors']==0
 else:assert p.returncode!=0 and receipt['passed'] is False
 assert hashlib.sha256((folder/'component-tests.log').read_bytes()).hexdigest()==receipt['test_log_sha256']
 results[name]={'exit_code':p.returncode,'receipt_passed':receipt['passed'],'tests':receipt['tests_run'],'skips':receipt['skips'],'source_before':receipt['source_before'],'source_after':receipt['source_after']}
 if options.get('comment'):results[name].update(committed_raw_sha256=hashlib.sha256(committed).hexdigest(),executed_raw_sha256=hashlib.sha256(target.read_bytes()).hexdigest())
assert results['hidden_comment']['source_before']==results['hidden_comment']['source_after'] and results['hidden_comment']['committed_raw_sha256']!=results['hidden_comment']['executed_raw_sha256']
after=identity();assert before==after
report={'head':head,'tree':git('rev-parse','HEAD^{tree}').decode().strip(),'base':base,'old15test_method_ASTs_and_placement_schedule_boundary_bytes_unchanged':True,'new_test_method_count':15,'source_raw_pre_post':[before,after],'clean_CI_exact_block_tests':30,'clean_skips':0,'CI_gate_cases':results,'F15':'P2_OPEN_SOURCE_GUARD_ACCEPTS_HIDDEN_TRACKED_COMMENT','scope':'LOCAL_SQLITE_PREPARATION_ONLY_NOT_AUTHORITY_OR_DISPATCH','journal_native_tests':'INCLUDES_ACTUAL_OWNED_CHILD_CRASH_ROLLBACK_TWO_CONNECTION_RACE_UNKNOWN_RESTART_CPU_SCALE_NEGATIVE','actual_cluster_reservation_fencing_identity':'NOT_IMPLEMENTED_NOT_QUALIFIED','hosted':'NOT_QUALIFIED','physical':'BLOCKED','overall':'NO_GO'}
(out/'scheduler-durable-review.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
