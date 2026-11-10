import hashlib,json,os,pathlib,subprocess,sys,time,uuid
root=pathlib.Path(r'C:/Users/LS-5/.codex/mission-continuation-evidence-20261110/fresh-8160')
out=root.parent
git=r'C:/Program Files/Git/cmd/git.exe'
head='8160f6c581640089e5db68516edfc43a0a88a993'
def g(*args):return subprocess.check_output([git,'--no-replace-objects','-C',str(root),*args],timeout=10)
def inventory():
    assert g('rev-parse','HEAD').decode().strip()==head
    result={}
    for row in g('ls-tree','-rz','--full-tree',head).split(b'\0'):
        if not row:continue
        meta,name=row.split(b'\t');name=name.decode();data=(root/name).read_bytes()
        assert data==g('cat-file','blob',meta.split()[2].decode()),name
        result[name]=hashlib.sha256(data).hexdigest()
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and '.git' not in p.relative_to(root).parts}
    assert actual==set(result),(actual-set(result))
    return result
before=inventory()
(out/'exact-source-before.json').write_text(json.dumps(before,sort_keys=True))
cmd=[sys.executable,'-I','-S','-B','-c',"import sys,unittest;sys.path.insert(0,"+repr(str(root))+");s=unittest.defaultTestLoader.loadTestsFromName('tests.test_mission_controller');ids=[];walk=lambda x:[walk(y) for y in x] if isinstance(x,unittest.TestSuite) else ids.append(x.id());walk(s);assert len(ids)==len(set(ids))==50;print('UNIQUE_IDS',len(ids),flush=True);r=unittest.TextTestRunner(verbosity=2).run(s);assert r.testsRun==50 and not r.skipped;sys.exit(not r.wasSuccessful())"]
r=subprocess.run(cmd,capture_output=True,timeout=55);(out/'exact-50.log').write_bytes(r.stdout+r.stderr);assert r.returncode==0
fixture=out/('restart-fixture-'+uuid.uuid4().hex);fixture.mkdir();db=fixture/'mission.db'
common="import sys,os,json,uuid,hashlib;from pathlib import Path;sys.path.insert(0,"+repr(str(root))+");from unified_system.mission_controller import MissionController;from unified_system.contracts import ContractError;from tests.test_mission_controller import task,continuation_metadata;path=Path("+repr(str(db))+ ");nonce=uuid.uuid4().hex;"
phase1=common+"c=MissionController.create(path);parent=task('fixture-parent');c.put(parent,expected_sequence=1);t=task('fixture-child',['fixture-parent']);c.put(t,expected_sequence=2);m=continuation_metadata();m['retry_budget']['retries_used']=1;m['last_verified_result']=dict(status='PASS',scope='SYNTHETIC_FIXTURE_ONLY',summary='Fixture observation',source_head='d'*40,source_tree='e'*40);m['evidence']=[dict(reference='synthetic-fixture-evidence',sha256='f'*64)];c.checkpoint_continuation('fixture-child',m,expected_sequence=3);print(json.dumps(dict(pid=os.getpid(),nonce=nonce,state=c.continuation_projection(),task=c.projection(),label='PYTHON_PROCESS_RESTART_ONLY'),sort_keys=True))"
phase2=common+'''c=MissionController.open(path);before=c.continuation_projection();entry=before['continuations']['fixture-child'];m=entry['metadata'];assert before['sequence']==4 and not entry['stale'];assert m['retry_budget']==dict(max_retries=2,retries_used=1);assert m['evidence']==[dict(reference='synthetic-fixture-evidence',sha256='f'*64)];assert m['last_verified_result']['scope']=='SYNTHETIC_FIXTURE_ONLY';assert c.projection()['tasks']['fixture-child']['dependencies']==['fixture-parent'];assert before['public_submit']=='DENY';assert all(before[k] is False for k in ('native_authority','runtime_admission','physical_execution_authorization','trading_authority','grants_node_operations'));t=task('fixture-child',['fixture-parent']);t['blockers']=['fixture drift'];c.put(t,expected_sequence=4);c=MissionController.open(path);assert c.continuation_projection()['continuations']['fixture-child']['stale'];lower=continuation_metadata()
try:c.checkpoint_continuation('fixture-child',lower,expected_sequence=5)
except ContractError:pass
else:raise AssertionError('retry reset accepted')
c.checkpoint_continuation('fixture-child',m,expected_sequence=5);assert not c.continuation_projection()['continuations']['fixture-child']['stale'];print(json.dumps(dict(pid=os.getpid(),nonce=nonce,before=before,after=c.continuation_projection(),label='PYTHON_PROCESS_RESTART_ONLY',codex_app_restart='NOT_TESTED',autonomous_dispatch='NOT_IMPLEMENTED'),sort_keys=True))'''
receipts=[]
for number,code in enumerate((phase1,phase2),1):
    start=time.time();p=subprocess.Popen([sys.executable,'-I','-S','-B','-c',code],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    stdout,stderr=p.communicate(timeout=10);(fixture/f'phase{number}.stdout.json').write_bytes(stdout);(fixture/f'phase{number}.stderr.txt').write_bytes(stderr)
    assert p.returncode==0,stderr.decode();data=json.loads(stdout);assert data['pid']==p.pid
    receipts.append(dict(pid=p.pid,nonce=data['nonce'],started_unix=start,returncode=p.returncode,stdout_sha256=hashlib.sha256(stdout).hexdigest()))
assert receipts[0]['pid']!=receipts[1]['pid'] and receipts[0]['nonce']!=receipts[1]['nonce']
after=inventory();assert before==after
(out/'exact-source-after.json').write_text(json.dumps(after,sort_keys=True))
receipt=dict(result='PASS',head=head,tree=g('rev-parse','HEAD^{tree}').decode().strip(),raw_files=len(after),module_sha256=after['unified_system/mission_controller.py'],tests=50,skips=0,processes=receipts,fixture=str(fixture),journal_sha256=hashlib.sha256(db.read_bytes()).hexdigest(),label='PYTHON_PROCESS_RESTART_ONLY',codex_app_restart='NOT_TESTED',autonomous_dispatch='NOT_IMPLEMENTED')
(out/'restart-receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2));print(json.dumps(receipt))
