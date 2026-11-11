import sqlite3,pathlib,types,sys,json,hashlib
rows=[];retained=[]
for head,source,folder in json.loads(sys.stdin.read()):
 raw=bytes.fromhex(source);m=types.ModuleType('A8_primary_store');exec(compile(raw,'primary-result-store','exec'),m.__dict__);db=pathlib.Path(folder)/'own.sqlite';db.parent.mkdir();con=sqlite3.connect(db);con.execute('CREATE TABLE research_results(run_id TEXT)');con.commit();con.close()
 try:m.ResultStore.open(db)
 except sqlite3.OperationalError as exc:retained.append(exc)
 else:raise AssertionError('EXPECTED_ORIGINAL_ERROR')
 assert str(retained[-1])=='no such column: symbol' and retained[-1].__traceback__ is not None
 writer=sqlite3.connect(db,timeout=0);locked=False
 try:
  writer.execute('BEGIN IMMEDIATE');assert [r[1] for r in writer.execute('PRAGMA table_info(research_results)')]==['run_id']
 except sqlite3.OperationalError as error:
  assert str(error)=='database is locked';locked=True
 finally:writer.rollback();writer.close()
 rows.append(dict(head=head,module_sha256=hashlib.sha256(raw).hexdigest(),original_error=str(retained[-1]),traceback_retained=True,second_writer_locked=locked))
assert rows[0]['second_writer_locked'] and not rows[1]['second_writer_locked'];print(json.dumps(dict(cases=rows,GC_or_schema_repair=False,scope='OWN_SYNTHETIC_SQLITE_ONLY'),indent=2))
