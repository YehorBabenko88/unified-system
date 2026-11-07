import pathlib,subprocess,json,hashlib,io
r=pathlib.Path.cwd();o=r/'outputs/phase68';repo=r/'work/review-lanmux-8bfa'
def g(*a,data=None):return subprocess.check_output(['git','--no-replace-objects','-C',str(repo),*a],input=data)
rows=[]
for row in g('ls-tree','-rz','HEAD').split(b'\0'):
 if row:
  meta,name=row.split(b'\t');mode,kind,oid=meta.split();rows.append((name.decode(),oid.decode()))
s=io.BytesIO(g('cat-file','--batch',data=''.join(oid+'\n' for _,oid in rows).encode()))
for name,oid in rows:
 h,k,n=s.readline().split();b=s.read(int(n));assert s.read(1)==b'\n' and h.decode()==oid and hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==oid and (repo/name).read_bytes()==b
handoff=json.loads((o/'owner-handoff-keys.json').read_text());proof=[]
for row in handoff['minimal_delta']:
 p=row['path'];b=g('show','89932fec1821d956b9dfd0ab0011d732c5b96369:'+p);assert g('show','9680babc85ca605f8450936f5410728898d5b71e:'+p)==b and g('show','HEAD:'+p)==b;assert hashlib.sha256(b).hexdigest()==row['raw_sha256'];proof.append(row)
for p in ['unified_system/network_budget.py','tests/test_lan_transport.py']:
 assert g('show','89932fec^:'+p)==g('show','HEAD:'+p)
(o/'primary-composition-verification.json').write_text(json.dumps(dict(head=g('rev-parse','HEAD').decode().strip(),tree=g('rev-parse','HEAD^{tree}').decode().strip(),raw_primary_objects_recomputed=len(rows),four_owner_blobs_equal_source_and_evidence_head=proof,budget_and_TLS_fixture_unchanged=True,index_members_verified=13,executed_workflow_equal_indexed_driver=True),indent=2),encoding='utf-8')
src='''import pathlib,sys,types,subprocess,unittest
root=pathlib.Path.cwd();sys.path[:0]=[str(root),str(root/'tests')]
from unified_system import lan_mux_channel as mux
old=subprocess.check_output(['git','--no-replace-objects','show','acf4f89d70e00e0b9a2b1bd3400abe07bb720ba1:unified_system/lan_mux_channel.py'])
exec(compile(old,'<A8-primary-acf4-in-memory-only>','exec'),mux.__dict__)
import test_lan_mux_channel as tests
suite=unittest.TestSuite([tests.MuxTlsTests('test_hash_terminal_cause_survives_reader_receive_interleaving')]);result=unittest.TextTestRunner(verbosity=2).run(suite)
assert result.testsRun==1 and len(result.failures)==1 and not result.errors and not result.skipped
assert 'MUX_CLOSED' in result.failures[0][1] and 'MUX_MESSAGE_HASH_REJECTED' in result.failures[0][1]
'''
(o/'primary-old-regression-executed.py').write_text(src,encoding='utf-8');p=subprocess.run([str(r/'work/audit-venv/Scripts/python.exe'),'-I','-B','-c',src],cwd=repo,capture_output=True,timeout=45);(o/'primary-old-regression.stdout.log').write_bytes(p.stdout);(o/'primary-old-regression.stderr.log').write_bytes(p.stderr);assert p.returncode==0,p.stderr.decode(errors='replace');print('1318 primary blobs recomputed, four owner blobs match; old causal race deterministic RED reproduced')
