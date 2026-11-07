import pathlib,subprocess,os,textwrap,json,hashlib
r=pathlib.Path.cwd();repo=r/'work/review-installer-fe0f';out=r/'outputs/phase67';out.mkdir(exist_ok=True);tmp=r/'work/installer-fe0f-a8-temp';tmp.mkdir(exist_ok=True);head='fe0f5234a1c5eeeca02b2dad3ddfa948ef6c51cf';py=r/'work/audit-venv/Scripts/python.exe'
def git(*args):return subprocess.check_output(['git','--no-replace-objects','-C',str(repo),*args])
assert git('rev-parse','HEAD').decode().strip()==head
tree=git('rev-parse','HEAD^{tree}').decode().strip()
changes=git('diff','--name-only','HEAD^',head).decode().splitlines();assert len(changes)==7
raw=git('show','HEAD:.github/workflows/installer-archive-namespace.yml');(out/'workflow.original.yml').write_bytes(raw)
block=textwrap.dedent(raw.decode().split('        run: |\n',1)[1].split('      - uses:',1)[0])
env={k:v for k,v in os.environ.items() if not k.upper().startswith('GIT_')};env.update(EXPECTED_HEAD=head,RUNNER_TEMP=str(tmp),PYTHONDONTWRITEBYTECODE='1',GRID_REFERENCE=str(r/'work/review-bootstrap7a83'))
def run(name,code):
 p=subprocess.run([str(py),'-I','-B','-c',code],cwd=repo,env=env,capture_output=True,timeout=120)
 (out/(name+'.stdout.log')).write_bytes(p.stdout);(out/(name+'.stderr.log')).write_bytes(p.stderr)
 assert p.returncode==0,p.stderr.decode(errors='replace')[-2500:]
run('workflow10',block)
receipt=(tmp/'installer-archive-namespace-evidence.json').read_bytes();a=json.loads(receipt);assert len(a['tests'])==4 and a['skips']==0;(out/'workflow10.original.json').write_bytes(receipt)
for name,digest in a['source_sha256'].items():assert hashlib.sha256((repo/name).read_bytes()).hexdigest()==digest
(out/'local-review.json').write_text(json.dumps(dict(head=head,tree=tree,changed_paths=changes,workflow_tests=4,broader_tests="NOT_RUN",skips=0,source_files_prepost=len(a['source_sha256']),scope='LOCAL_WINDOWS_ARCHIVE_NAMESPACE_COMPONENT_ONLY',hosted='NOT_QUALIFIED',physical='BLOCKED'),indent=2),encoding='utf-8')
print((out/'local-review.json').read_text())
