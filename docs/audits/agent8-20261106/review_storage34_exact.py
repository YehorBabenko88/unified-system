"""Fresh exact-source filesystem suite, only own scratch/temp roots."""
import hashlib,io,json,os,pathlib,subprocess
r=pathlib.Path(__file__).resolve().parents[1];repo=r/'work/review-storage34-cd0286d';out=r/'outputs/phase54';out.mkdir(exist_ok=True);head='cd0286dee5fc41cb7a35b0b6ac431a7ebfc25dfb';base='10157fed4d28606adf587be3494d2f6d42887ce9'
def git(*a):return subprocess.check_output(['git','--no-replace-objects','-C',str(repo),*a])
assert git('rev-parse','HEAD').decode().strip()==head and git('rev-parse','HEAD^{tree}').decode().strip()=='84b714253c3e10017046e1a7a5981738a05e06e6';changes=git('diff','--name-status',base,head).decode().splitlines();assert len(changes)==7 and all(x.startswith('A\t') for x in changes)
owner=(r.parent/'codex-agent-4-distributed-storage-integrity/outputs/STORAGE-ISOLATED-FS-HANDOFF-REVIEW2.json').read_bytes();assert hashlib.sha256(owner).hexdigest()=='5409817a0014173df3ddbe5cf1edfe1f68110c0b335c8c4329170950c4dde85d'
def identity():
 rows={};names=git('ls-tree','-r','--name-only',head).decode().splitlines();stream=io.BytesIO(subprocess.check_output(['git','--no-replace-objects','-C',str(repo),'cat-file','--batch'],input=''.join(head+':'+n+'\n' for n in names).encode()))
 for name in names:
  oid,kind,size=stream.readline().split();assert kind==b'blob';raw=stream.read(int(size));assert stream.read(1)==b'\n' and raw==(repo/name).read_bytes();rows[name]=hashlib.sha256(raw).hexdigest()
 assert not any(p.suffix.lower() in ('.pyc','.pyo') for p in repo.rglob('*') if p.is_file())
 return rows
before=identity();scratch=r/'work/storage34-a8-temp';scratch.mkdir(exist_ok=False);env=os.environ.copy();env.update(TEMP=str(scratch),TMP=str(scratch),PYTHONDONTWRITEBYTECODE='1',GIT_NO_REPLACE_OBJECTS='1')
p=subprocess.run([str(r/'work/audit-venv/Scripts/python.exe'),'-I','-B',str(repo/'tests/storage/runtime/run_isolated.py')],cwd=repo,env=env,capture_output=True,timeout=120);(out/'suite.stdout.json').write_bytes(p.stdout);(out/'suite.stderr.log').write_bytes(p.stderr);assert p.returncode==0,p.stderr.decode(errors='replace')[-2000:];a=json.loads(p.stdout);assert a['head']==head and a['tests_run']==43 and a['skips']==0 and a['passed'] and not a['dirty'];assert before==identity()
report=dict(requirement='STORAGE_ISOLATED_FILESYSTEM_EXACT_HEAD',repository='unified-system',pr=34,head=head,tree=a['tree'],base=base,added_paths=changes,Stage1_raw_unchanged=True,unit_fs_cases=43,stage1_cases=26,new_filesystem_cases=17,skips=0,all_primary_raw_inputs_before_after=len(before),raw_manifest_sha256=hashlib.sha256(json.dumps(before,sort_keys=True).encode()).hexdigest(),owner_handoff_sha256=hashlib.sha256(owner).hexdigest(),full751_precommit='NOT_TRANSFERRED_NOT_RUN_HERE',qualification='ISOLATED_FILESYSTEM_ONLY',media_durability=False,dataset_closure=False,Consul_publication=False,pilot_rollback_qualified=False,native_admission=False,overall='NO_GO_BROADER_ACCEPTANCE')
(out/'exact-review.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
