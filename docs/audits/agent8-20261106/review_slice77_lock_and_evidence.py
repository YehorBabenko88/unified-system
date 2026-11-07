import pathlib,subprocess,json,hashlib
r=pathlib.Path.cwd();repo=r/'work/review-slice77-887';o=r/'outputs/phase95';old='2f98f3501ea8274ebda8798a5c5b6e4f4910f2ee';new='887e3eeaf23ef8d9d1429435bc88bbac8099c6e6';root=r/'work/slice77-a8-lock-redgreen';root.mkdir(exist_ok=True)
def g(*a):return subprocess.check_output(['git','--no-replace-objects','-C',str(repo),*a])
s='''import sqlite3,pathlib,types,sys,json,hashlib
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
'''
items=[(head,g('show',head+':strattester/persistence/result_store.py').hex(),str(root/label)) for head,label in [(old,'red'),(new,'green')]];(o/'lock-redgreen-executed.py').write_text(s);p=subprocess.run([str(r/'work/audit-venv/Scripts/python.exe'),'-I','-S','-B','-c',s],input=json.dumps(items).encode(),capture_output=True,timeout=30);(o/'lock-redgreen.stdout.json').write_bytes(p.stdout);(o/'lock-redgreen.stderr.log').write_bytes(p.stderr);assert p.returncode==0,p.stderr;print(p.stdout.decode())
owner=r.parent/'codex-agent-7-distributed-research-math/outputs';b=(owner/'persistence-887e3ee-qualification.json').read_bytes();d=json.loads(b);primary=json.loads((o/'primary-verification.json').read_text());assert d['source_sha256']==primary['source_raw'];(o/'owner-qualification.original.json').write_bytes(b)
for name,facts in d['files'].items():
 path=pathlib.Path(name);raw=path.read_bytes();assert len(raw)==facts['bytes'] and hashlib.sha256(raw).hexdigest()==facts['sha256'];(o/('owner-'+path.name)).write_bytes(raw)
ack=r.parent/'codex-agent-4-distributed-storage-integrity/outputs/AGENT4-A7-887E-SOURCE-REVIEW2.json';raw=ack.read_bytes();assert hashlib.sha256(raw).hexdigest().startswith('c5876f92');(o/'a4-source-ack.original.json').write_bytes(raw)
copy=json.loads((repo/'docs/gateway/research/persistence/HARNESS-COPY-RECEIPT.json').read_bytes())
for path,pin in copy['files'].items():
 raw=g('show',copy['source_head']+':'+path);assert raw==(repo/path).read_bytes() and hashlib.sha256(raw).hexdigest()==pin['sha256'] and len(raw)==pin['bytes'];assert g('rev-parse',copy['source_head']+':'+path).decode().strip()==pin['source_blob']
(o/'harness-copy-verified.json').write_text(json.dumps(dict(files=3,source=copy['source_head'],byte_equal=True,v2_runtime_transfer=False),indent=2))
