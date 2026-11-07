import pathlib,subprocess
r=pathlib.Path.cwd();o=r/'outputs/phase77';repo=r/'work/review-supervisora226';scratch=r/'work/supervisora226-a8-held';scratch.mkdir(exist_ok=False)
s='''import pathlib,sys,sqlite3,json,hashlib
from unittest.mock import patch
sys.path[:0]=[str(pathlib.Path.cwd()),str(pathlib.Path.cwd()/'tests')]
from test_node_task_journal import operation,scoped_journal
from unified_system.node_task_journal import NodeJournalError
root=pathlib.Path(sys.argv[1]);path=root/'node.db';journal=scoped_journal(path,max_bytes=65536);journal.create(operation());keeper=sqlite3.connect(path)
def image():return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in root.iterdir()}
refused=0
try:
 assert keeper.execute('PRAGMA journal_mode=WAL').fetchone()[0]=='wal';keeper.execute('PRAGMA wal_autocheckpoint=0');keeper.execute('BEGIN');keeper.execute('SELECT COUNT(*) FROM transitions').fetchone()
 before=image()
 with patch('sqlite3.connect',side_effect=AssertionError('SQLITE_OPENED_BEFORE_WAL_REFUSAL')):
  for call in [lambda:journal.create(operation(task_id='task2',idempotency_key='key2')),journal.snapshot,journal.reconcile,lambda:journal.get('task1'),lambda:journal.transition('task1','INTERRUPTED'),lambda:scoped_journal(path)]:
   try:call();raise AssertionError('WAL_ACCEPTED')
   except NodeJournalError:refused+=1
 assert image()==before
finally:keeper.close()
# WAL format remains after SQLite's own close; helper must not change it to DELETE.
assert path.read_bytes()[18:20]==b'\\x02\\x02';before=image()
with patch('sqlite3.connect',side_effect=AssertionError('SQLITE_OPENED_BEFORE_HEADER_REFUSAL')):
 try:scoped_journal(path);raise AssertionError('WAL_HEADER_ADOPTED')
 except NodeJournalError:refused+=1
assert image()==before
# Separate own DELETE database refuses inert sidecars before SQLite opens, preserving sentinel.
for suffix in ['-wal','-shm','-journal']:
 q=root/('inert'+suffix.replace('-','')+'.db');j=scoped_journal(q);j.create(operation());side=pathlib.Path(str(q)+suffix);side.write_bytes(b'A8_INERT_SIDECAR');before=image()
 with patch('sqlite3.connect',side_effect=AssertionError('SIDECAR_OPENED')):
  try:j.snapshot();raise AssertionError('SIDECAR_ACCEPTED')
  except NodeJournalError:refused+=1
 assert image()==before
print(json.dumps(dict(held_reader_WAL_and_other_refusals_before_any_SQLite_open=refused,all_rejection_paths_preserve_bytes=True,no_checkpoint_mode_change_or_sidecar_deletion_by_helper=True,scope='OWN_SYNTHETIC_SQLITE_ONLY_NOT_NATIVE_AUTHORITY'),indent=2))
'''
(o/'held-reader-executed.py').write_text(s,encoding='utf-8');p=subprocess.run([str(r/'work/audit-venv/Scripts/python.exe'),'-I','-S','-B','-c',s,str(scratch)],cwd=repo,capture_output=True,timeout=30);(o/'held-reader.stdout.json').write_bytes(p.stdout);(o/'held-reader.stderr.log').write_bytes(p.stderr);assert p.returncode==0,p.stderr;print(p.stdout.decode())
