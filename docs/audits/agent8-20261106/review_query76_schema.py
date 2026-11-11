import pathlib,subprocess,json
r=pathlib.Path.cwd();repo=r/'work/review-query76-6e58';o=r/'outputs/phase90'
for label,folder in [('original',repo/'docs/gateway/research/evidence/query-v2-onebar'),('generated',r/'work/query76-a8-temp/gateway-query-v2-computation')]:
 p=subprocess.run([str(r/'work/mux-independent-env/Scripts/python.exe'),'-I','-B',str(repo/'tests/gateway_adapter/validate_query_v2_artifacts.py'),'--artifacts',str(folder)],cwd=repo,capture_output=True,timeout=30);(o/('schema30-'+label+'.stdout.json')).write_bytes(p.stdout);(o/('schema30-'+label+'.stderr.log')).write_bytes(p.stderr);assert p.returncode==0,p.stderr;d=json.loads(p.stdout);assert d['checks']==30 and d['skips']==0;print(label,d['checks'])
