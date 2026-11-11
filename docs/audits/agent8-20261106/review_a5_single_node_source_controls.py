import json,os,pathlib,subprocess,textwrap,uuid
r=pathlib.Path(__file__).resolve().parents[1];seed=r/'work/review-a5-single7a418';out=r/'outputs/phase59';head='7a4185924d4702ade53f518644e45d6ee4f6f451';workflow=(seed/'.github/workflows/agent5-components.yml').read_text(encoding='utf-8');code=textwrap.dedent(workflow.split("          python -I -B - <<'PY'\n",1)[1].split('          PY',1)[0]);guard=code.split("expected = os.environ['EXPECTED_SOURCE_SHA']",1)[0];cases=[]
for name in ['new_single_node_cache','root_typing_shadow']:
 repo=r/'work'/('a5-single-negative-'+name+'-'+uuid.uuid4().hex[:6]);subprocess.run(['git','clone','--no-hardlinks','--no-checkout',str(seed),str(repo)],check=True,capture_output=True);subprocess.run(['git','-C',str(repo),'-c','core.autocrlf=false','-c','core.eol=lf','checkout','--detach',head],check=True,capture_output=True)
 if name=='new_single_node_cache':
  folder=repo/'scheduler_components/__pycache__';folder.mkdir();(folder/'single_node.cpython-312.pyc').write_bytes(b'INERT_CACHE_NOT_EXECUTED')
 else:(repo/'typing.py').write_text("raise AssertionError('INERT_UNEXPECTED_SHADOW')\n",encoding='utf-8')
 folder=out/name;folder.mkdir();env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')};env.update(EVIDENCE_DIR=str(folder),EXPECTED_SOURCE_SHA=head)
 extra="\nassert not before['protected_inputs_valid']\nprint(json.dumps(dict(rejected=True,tests_executed=0,cache_paths=before['repository_bytecode_paths'],unexpected=before['unexpected_protected_files'])))\n"
 p=subprocess.run([str(r/'work/audit-venv/Scripts/python.exe'),'-I','-B','-c',guard+extra],cwd=repo,env=env,capture_output=True,timeout=30);(folder/'stdout.json').write_bytes(p.stdout);(folder/'stderr.log').write_bytes(p.stderr);assert p.returncode==0,p.stderr;cases.append(dict(case=name,guard_rejected=True,MODEL_or_legacy_tests_executed=0))
(out/'source-controls.json').write_text(json.dumps(cases,indent=2),encoding='utf-8');print(json.dumps(cases))
