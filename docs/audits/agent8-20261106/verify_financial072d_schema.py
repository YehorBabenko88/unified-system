import pathlib,subprocess,json,os,hashlib
r=pathlib.Path.cwd();repo=r/'work/review-financial-072d';o=r/'outputs/phase71'
p=subprocess.run([str(r/'work/mux-independent-env/Scripts/python.exe'),'-I','-B',str(repo/'contracts/agent7-financial-boundary/test_adapter.py'),'--validate-schema'],cwd=repo,capture_output=True,timeout=30);(o/'actual-validator46.stdout.json').write_bytes(p.stdout);(o/'actual-validator46.stderr.log').write_bytes(p.stderr);assert p.returncode==0 and json.loads(p.stdout)['schema_checks']==46
b=(repo/'contracts/agent7-financial-boundary/financial-calculation.schema.json').read_bytes();(o/'schema.raw-sha256.txt').write_text(hashlib.sha256(b).hexdigest()+'\n',encoding='ascii')
env={k:v for k,v in os.environ.items() if not k.upper().startswith('GIT_')};env.update(EXPECTED_HEAD='072d22214136148b47e82d21fec9e269bd7468ac',RUNNER_TEMP=str(r/'work/financial-072d-a8-evidence'))
p=subprocess.run([str(r/'work/audit-venv/Scripts/python.exe'),'-I','-S','-B',str(r/'work/financial-072d-a8-evidence/executed-workflow.py')],cwd=repo,env=env,capture_output=True,timeout=60);(o/'post-schema-workflow20.stdout.log').write_bytes(p.stdout);(o/'post-schema-workflow20.stderr.log').write_bytes(p.stderr);assert p.returncode==0,p.stderr
print('actual validator46 + own9LFnegatives + post-schema committedworkflow20 clean PASS')
