"""Separate fresh52legacy and18MODEL runs, exact Git source guard before imports."""
import hashlib,json,os,pathlib,subprocess,textwrap
r=pathlib.Path(__file__).resolve().parents[1];repo=r/'work/review-a5-single7a418';out=r/'outputs/phase59';out.mkdir(exist_ok=True);head='7a4185924d4702ade53f518644e45d6ee4f6f451';old='d563e96c06f187f19d3384e2afb544726c51a759';py=r/'work/audit-venv/Scripts/python.exe';temp=r/'work/a5-single-a8-temp';temp.mkdir(exist_ok=False)
def git(*a):return subprocess.check_output(['git','--no-replace-objects','-C',str(repo),*a])
pins={'scheduler_components/single_node.py':'c3306cd018be6da0e3f919a0d8353382364aa1ecb3e6e7e5a22ab29e9b6766c9','tests/test_agent5_single_node.py':'84de4e457aba3da95c17a1daf91a29ba60f2a4b793e8d06b16f0b4829bf129bf','docs/scheduler/runtime-single-node.md':'95835c2a0c52e96f483923be19ebff273fc4a4322c4b97c9a06d0df912ff9de4'}
assert set(git('diff','--name-only',old,head).decode().splitlines())==set(pins)
for name,digest in pins.items():assert hashlib.sha256(git('show',head+':'+name)).hexdigest()==digest
workflow=git('show',head+':.github/workflows/agent5-components.yml');assert workflow==git('show',old+':.github/workflows/agent5-components.yml');code=textwrap.dedent(workflow.decode().split("          python -I -B - <<'PY'\n",1)[1].split('          PY',1)[0]);guard=code.split("expected = os.environ['EXPECTED_SOURCE_SHA']",1)[0]
boot='import sys\nsys.path.insert(0,'+repr(str(r/'work/integration-review-deps'))+')\n';env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')};env.update(EXPECTED_SOURCE_SHA=head,TEMP=str(temp),TMP=str(temp),PYTHONDONTWRITEBYTECODE='1',GIT_CONFIG_COUNT='2',GIT_CONFIG_KEY_0='core.autocrlf',GIT_CONFIG_VALUE_0='false',GIT_CONFIG_KEY_1='core.eol',GIT_CONFIG_VALUE_1='lf')
model=guard+'''
assert before['head']==os.environ['EXPECTED_SOURCE_SHA'] and before['protected_inputs_valid'] and not before['tracked_status']
sys.path.insert(0,str(Path.cwd()))
suite=unittest.defaultTestLoader.discover('tests',pattern='test_agent5_single_node.py')
def flat(s):
 for t in s:
  if isinstance(t,unittest.TestSuite):yield from flat(t)
  else:yield t.id()
ids=list(flat(suite));assert len(ids)==len(set(ids))==18 and all('.SingleNodeModelTests.' in x for x in ids)
with (out/'models.log').open('w',encoding='utf-8') as log:result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
after=source();assert after==before and after['protected_inputs_valid'] and result.wasSuccessful() and result.testsRun==18 and not result.skipped
(out/'models.json').write_text(json.dumps(dict(head=before['head'],tree=before['tree'],cases=ids,tests=18,skips=0,model_worker_starts=0,scope='MODEL_ONLY_UNSUPPORTED_PROPOSED_API_NOT_RUNTIME',all_raw_inputs=len(before['protected_files']),source_before=before,source_after=after),indent=2),encoding='utf-8')
'''
for label,body in [('legacy52',code),('models18',model)]:
 folder=out/label;folder.mkdir();e=dict(env,EVIDENCE_DIR=str(folder));p=subprocess.run([str(py),'-I','-B','-c',boot+body],cwd=repo,env=e,capture_output=True,timeout=120);(out/(label+'.stdout.log')).write_bytes(p.stdout);(out/(label+'.stderr.log')).write_bytes(p.stderr);assert p.returncode==0,(label,p.stderr.decode(errors='replace')[-2000:])
a=json.loads((out/'legacy52/receipt.json').read_bytes());b=json.loads((out/'models18/models.json').read_bytes());assert a['passed'] and a['tests_run']==52 and len(a['source_before']['protected_files'])==b['all_raw_inputs']==339
report=dict(head=head,tree=git('rev-parse',head+'^{tree}').decode().strip(),base=old,new_paths_raw_sha256=pins,legacy_workflow_and_52inventory_raw_unchanged=True,separate_legacy_cases=52,separate_MODEL_cases=18,skips=0,model_worker_starts=0,all_raw_files_before_after=339,scope='LOCAL_PY312_SEPARATE_SOURCE_BOUND_MODEL_ONLY',hosted18='NOT_EXECUTED_BY_UNCHANGED52_WORKFLOW',actual_A2_A4_ROOT_adapters='ABSENT_UNSUPPORTED_PROPOSALS_NOT_COMPATIBILITY_ACK',native_runtime_physical_admission=False,overall='NO_GO_BROADER_ADMISSION')
(out/'exact-review.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
