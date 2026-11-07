import pathlib,subprocess
r=pathlib.Path.cwd();o=r/'outputs/phase76';repo=r/'work/review-supervisor840';scratch=r/'work/supervisor840-a8-wal-held-reader';scratch.mkdir(exist_ok=False)
s='''import pathlib,sys,sqlite3,json
sys.path[:0]=[str(pathlib.Path.cwd()),str(pathlib.Path.cwd()/'tests')]
from test_node_task_journal import operation,scoped_journal
root=pathlib.Path(sys.argv[1]);path=root/'node.db';limit=65536;journal=scoped_journal(path,max_bytes=limit);journal.create(operation())
keeper=sqlite3.connect(path)
try:
 assert keeper.execute('PRAGMA journal_mode=WAL').fetchone()[0]=='wal';keeper.execute('PRAGMA wal_autocheckpoint=0');keeper.execute('BEGIN');keeper.execute('SELECT COUNT(*) FROM transitions').fetchone()
 for n in range(1,20):journal.create(operation(task_id='task'+str(n+1),idempotency_key='key'+str(n+1)))
 sizes={p.name:p.stat().st_size for p in root.iterdir()};assert path.stat().st_size<=limit and sum(sizes.values())>limit
 assert len(journal.snapshot())==20
 print(json.dumps(dict(scope='OWN_SYNTHETIC_SQLITE_ONLY_NOT_NATIVE_AUTHORITY',max_bytes=limit,successful_created=20,sizes=sizes,total_bytes=sum(sizes.values()),byte_budget_exceeded_while_create_and_snapshot_accepted=True),indent=2))
finally:keeper.close()
'''
(o/'wal-budget-executed.py').write_text(s,encoding='utf-8');p=subprocess.run([str(r/'work/audit-venv/Scripts/python.exe'),'-I','-S','-B','-c',s,str(scratch)],cwd=repo,capture_output=True,timeout=30);(o/'wal-budget.stdout.json').write_bytes(p.stdout);(o/'wal-budget.stderr.log').write_bytes(p.stderr);assert p.returncode==0,p.stderr;print(p.stdout.decode())
