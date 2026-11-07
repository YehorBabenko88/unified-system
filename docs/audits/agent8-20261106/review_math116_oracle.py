import ast,pathlib,subprocess,os
r=pathlib.Path.cwd();tree=ast.parse((r/'outputs/review_bootstrap267.py').read_text())
s=next(ast.literal_eval(x.value) for x in tree.body if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='script' for t in x.targets))
s=s[:s.index('calls=[]')]+s[s.index('from grid import strategy_statistics as current'):]
s=s.replace('from grid import strategy_statistics as current',"sys.path.insert(0,str(repo/'python'));import history_statistics as current\ncalls=[];skips=[]").replace('7a19ab40c30efef431bb16f0ddc91960608bf597:grid/strategy_statistics.py','917d99672e37db59835a8ab23b03c99826b12d78:python/history_statistics.py')
p=subprocess.run([str(r/'work/audit-venv/Scripts/python.exe'),'-I','-B','-c',s,str(r/'work/review-math116-ff1c'),str(r/'outputs/phase66')],cwd=r/'work/review-math116-ff1c',capture_output=True,timeout=60)
(r/'outputs/phase66/oracle.stdout.log').write_bytes(p.stdout);(r/'outputs/phase66/oracle.stderr.log').write_bytes(p.stderr);assert p.returncode==0,p.stderr
(r/'outputs/phase66/oracle-executed.py').write_text(s,encoding='utf-8')
print((r/'outputs/phase66/numerical-oracle.json').read_text())
