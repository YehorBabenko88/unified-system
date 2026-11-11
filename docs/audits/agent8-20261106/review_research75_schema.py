import pathlib,subprocess,json,os
r=pathlib.Path.cwd();repo=r/'work/review-research75-aed8';o=r/'outputs/phase88';py=r/'work/mux-independent-env/Scripts/python.exe'
for label,folder in [('generated',r/'work/research75-a8-temp/gateway-research-computation'),('original',repo/'docs/gateway/research/evidence/btc-v1')]:
 p=subprocess.run([str(py),'-I','-B',str(repo/'tests/gateway_adapter/validate_artifacts.py'),'--artifacts',str(folder)],cwd=repo,capture_output=True,timeout=30);(o/('schema78-'+label+'.stdout.json')).write_bytes(p.stdout);(o/('schema78-'+label+'.stderr.log')).write_bytes(p.stderr);assert p.returncode==0,p.stderr;d=json.loads(p.stdout);assert d['schema_checks']==78 and d['skips']==0;print(label,d['schema_checks'],d['jsonschema_version'])
