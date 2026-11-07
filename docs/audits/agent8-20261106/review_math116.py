import pathlib,subprocess,os,textwrap,json,hashlib
r=pathlib.Path.cwd();repo=r/'work/review-math116-ff1c';out=r/'outputs/phase66';out.mkdir(exist_ok=True);tmp=r/'work/math116-a8-temp';tmp.mkdir(exist_ok=True);head='ff1c42cad883f54c06293884ef29a290dd74e306';py=r/'work/audit-venv/Scripts/python.exe'
def git(*args):return subprocess.check_output(['git','--no-replace-objects','-C',str(repo),*args])
assert git('rev-parse','HEAD').decode().strip()==head
assert git('rev-parse','HEAD^{tree}').decode().strip()=='68623befcb4de563e1d284569fea56b3d9c8de45'
changes=git('diff','--name-only','917d99672e37db59835a8ab23b03c99826b12d78',head).decode().splitlines();assert len(changes)==4
raw=git('show','HEAD:.github/workflows/agent7-history-statistics.yml');(out/'workflow.original.yml').write_bytes(raw)
block=textwrap.dedent(raw.decode().split('        run: |\n',1)[1].split('      - uses:',1)[0])
env={k:v for k,v in os.environ.items() if not k.upper().startswith('GIT_')};env.update(EXPECTED_HEAD=head,RUNNER_TEMP=str(tmp),PYTHONDONTWRITEBYTECODE='1',GRID_REFERENCE=str(r/'work/review-bootstrap7a83'))
def run(name,code):
 p=subprocess.run([str(py),'-I','-S','-B','-c',code],cwd=repo,env=env,capture_output=True,timeout=120)
 (out/(name+'.stdout.log')).write_bytes(p.stdout);(out/(name+'.stderr.log')).write_bytes(p.stderr)
 assert p.returncode==0,p.stderr.decode(errors='replace')[-2500:]
run('workflow10',block)
receipt=(tmp/'history-statistics-finite-evidence.json').read_bytes();a=json.loads(receipt);assert len(a['tests'])==10 and a['skips']==0;(out/'workflow10.original.json').write_bytes(receipt)
run('stdlib25',"""import unittest,pathlib,sys
root=pathlib.Path.cwd();sys.path.insert(0,str(root));suite=unittest.TestSuite()
for pattern in ['test_history_kernels.py','test_history_timed.py','test_history_ci_guard.py','test_history_scientific.py','test_history_statistics_overflow.py']:
 suite.addTests(unittest.defaultTestLoader.discover(str(root/'tests'),pattern=pattern))
result=unittest.TextTestRunner(verbosity=2).run(suite)
assert result.wasSuccessful() and result.testsRun==25 and not result.skipped
""")
for name,digest in a['source_sha256'].items():assert hashlib.sha256((repo/name).read_bytes()).hexdigest()==digest
(out/'local-review.json').write_text(json.dumps(dict(head=head,tree=a['tree'],changed_paths=changes,workflow_tests=10,broader_tests=25,overlap_tests=10,skips=0,source_files_prepost=len(a['source_sha256']),scope='LOCAL_WINDOWS_NUMERICAL_COMPONENT_ONLY',hosted='NOT_QUALIFIED',physical='BLOCKED'),indent=2),encoding='utf-8')
print((out/'local-review.json').read_text())
