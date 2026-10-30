import copy
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from contextlib import closing
from unified_system.lifecycle import Lifecycle, STAGES
from unified_system.contracts import ContractError
from unified_system.lifecycle_api import ReadOnlyLifecycleApp

MODULES=['unified-system','terminan','strattester','grid','math']
def verifier(stage, value, **transition):
    return dict(verdict='VERIFIED_SYNTHETIC',stage=stage,**transition) if value == {'source_owned':stage} else {'verdict':'UNAVAILABLE'}

class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'lifecycle.db'
        self.life=Lifecycle(self.path,MODULES,verifier=verifier)
        self.life.initialize()
        self.counter=0
    def apply(self,stage,status='COMPLETE',**kwargs):
        s=self.life.snapshot(); self.counter+=1
        return self.life.apply('op-'+str(self.counter),s['epoch'],s['sequence'],stage,status,{'source_owned':stage},**kwargs)
    def infra(self):
        self.apply(STAGES[0]);self.apply(STAGES[1]);self.apply('terminan','RUNNING')
    def test_sequence_and_no_authority(self):
        with self.assertRaises(ContractError):self.apply('GRID_MARKET_READY')
        self.infra()
        for stage in STAGES[2:]:self.apply(stage)
        s=self.life.snapshot()
        self.assertEqual(s['stages'][-1]['status'],'COMPLETE')
        self.assertFalse(s['execution_authorized']);self.assertFalse(s['trading_authorized'])
        self.assertEqual(s['paper']['status'],'NOT_AUTHORIZED')
    def test_monitoring_barrier_and_math_independence(self):
        self.apply('math','RUNNING')
        self.apply(STAGES[0]);self.apply(STAGES[1])
        with self.assertRaises(ContractError):self.apply(STAGES[2])
        self.apply('terminan','RUNNING');self.apply(STAGES[2])
    def test_idempotency_collision_and_sequence(self):
        s=self.life.snapshot();args=('same',s['epoch'],0,STAGES[0],'COMPLETE',{'source_owned':STAGES[0]})
        first=self.life.apply(*args)
        self.assertEqual(self.life.apply(*args),first)
        with self.assertRaises(ContractError):self.life.apply(*args[:-2],'RUNNING',args[-1])
        with self.assertRaises(ContractError):self.life.apply('other',s['epoch'],0,STAGES[1],'COMPLETE',{'source_owned':STAGES[1]})
    def test_default_verifier_denies_self_assertion(self):
        life=Lifecycle(Path(self.tmp.name)/'deny.db',MODULES);life.initialize();s=life.snapshot()
        with self.assertRaises(ContractError):life.apply('fake',s['epoch'],0,STAGES[0],'COMPLETE',{'verified':True})
    def test_recovery_revalidates_and_invalidates_downstream(self):
        self.infra();self.apply(STAGES[2],'RUNNING')
        restart=Lifecycle(self.path,MODULES,verifier=verifier);restart.initialize()
        self.assertEqual(restart.snapshot()['recovery'],'REVALIDATION_REQUIRED')
        s=restart.snapshot()
        with self.assertRaises(ContractError):restart.apply('resume',s['epoch'],s['sequence'],STAGES[2],'COMPLETE',{'source_owned':STAGES[2]})
        restart.recover(s['epoch'],s['sequence'])
        self.assertTrue(all(x['status']=='NOT_STARTED' for x in restart.snapshot()['stages']))
        self.assertNotEqual(restart.snapshot()['epoch'],s['epoch'])
    def test_missing_modules_zero_to_five(self):
        for n in range(6):
            life=Lifecycle(Path(self.tmp.name)/('n'+str(n)+'.db'),MODULES[:n],verifier=verifier);life.initialize()
            self.assertEqual(len(life.snapshot()['available_modules']),n)
            if not n:
                s=life.snapshot()
                with self.assertRaises(ContractError):life.apply('x',s['epoch'],0,STAGES[0],'COMPLETE',{'source_owned':STAGES[0]})
    def test_cancel_retry_cannot_retain_handoff(self):
        self.infra()
        for stage in STAGES[2:]:self.apply(stage)
        self.apply('STRAT_HISTORY_SYNC','CANCELLED')
        states={x['stage']:x['status'] for x in self.life.snapshot()['stages']}
        self.assertEqual(states['HANDOFF_VERIFY'],'NOT_STARTED')
        self.assertEqual(states['GRID_MARKET_READY'],'NOT_STARTED')
        self.apply('STRAT_HISTORY_SYNC','RUNNING')
    def test_tampered_state_rejected(self):
        self.infra()
        with closing(sqlite3.connect(self.path)) as db, db:db.execute("UPDATE lifecycle_state SET snapshot='{}'")
        with self.assertRaises(ContractError):self.life.snapshot()
    def test_failed_commit_does_not_advance(self):
        before=self.life.snapshot()
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("CREATE TRIGGER deny_events BEFORE INSERT ON lifecycle_events BEGIN SELECT RAISE(ABORT,'simulated disk full'); END")
        with self.assertRaises(sqlite3.Error):self.apply(STAGES[0])
        self.assertEqual(self.life.snapshot(),before)
    def test_concurrent_writer_fenced(self):
        other=Lifecycle(self.path,MODULES,verifier=verifier);other.initialize()
        s=self.life.snapshot();self.life.recover(s['epoch'],s['sequence'])
        with self.assertRaises(ContractError):other.recover(s['epoch'],s['sequence'])
    def test_cached_response_tamper_rejected(self):
        s=self.life.snapshot();args=('same',s['epoch'],0,STAGES[0],'COMPLETE',{'source_owned':STAGES[0]})
        self.life.apply(*args)
        with closing(sqlite3.connect(self.path)) as db,db:db.execute("UPDATE lifecycle_operations SET response=?",('{"execution_authorized":true}',))
        with self.assertRaises(ContractError):self.life.apply(*args)
    def test_completed_initial_state_cannot_be_injected(self):
        with closing(sqlite3.connect(self.path)) as db,db:
            state=json.loads(db.execute('SELECT snapshot FROM lifecycle_state').fetchone()[0])
            for row in state['stages']:row['status']='COMPLETE'
            db.execute('UPDATE lifecycle_state SET snapshot=?',(json.dumps(state),))
        with self.assertRaises(ContractError):self.life.snapshot()
    def test_old_epoch_operation_cannot_replay_after_recovery(self):
        s=self.life.snapshot();args=('same',s['epoch'],0,STAGES[0],'COMPLETE',{'source_owned':STAGES[0]})
        self.life.apply(*args);current=self.life.snapshot();self.life.recover(current['epoch'],current['sequence'])
        with self.assertRaises(ContractError):self.life.apply(*args)
    def test_restart_cannot_replay_cached_completion_before_revalidation(self):
        s=self.life.snapshot();args=('same',s['epoch'],0,STAGES[0],'COMPLETE',{'source_owned':STAGES[0]})
        self.life.apply(*args)
        restart=Lifecycle(self.path,MODULES,verifier=verifier);restart.initialize()
        with self.assertRaises(ContractError):restart.apply(*args)
    def test_verifier_cannot_bless_different_status(self):
        self.life.verifier=lambda stage,value,**transition:dict(verdict='VERIFIED_SYNTHETIC',stage=stage,status='RUNNING',completed=0,total=0)
        with self.assertRaises(ContractError):self.apply(STAGES[0])
    def test_read_only_api_and_safe_provider_failure(self):
        def request(app,method='GET',path='/internal/v1/lifecycle',query=''):
            response=[]
            body=b''.join(app({'REQUEST_METHOD':method,'PATH_INFO':path,'QUERY_STRING':query},lambda s,h:response.append(s)))
            return int(response[0].split()[0]),json.loads(body)
        app=ReadOnlyLifecycleApp(self.life.snapshot)
        code,value=request(app)
        self.assertEqual(code,200);self.assertEqual(value['status'],'AVAILABLE')
        self.assertEqual(request(app,'POST')[0],405)
        self.assertEqual(request(app,query='secret=value')[0],400)
        def bad():raise RuntimeError('private diagnostic')
        code,value=request(ReadOnlyLifecycleApp(bad))
        self.assertEqual(code,503);self.assertNotIn('private diagnostic',json.dumps(value))
        value=self.life.snapshot();value['execution_authorized']=True
        self.assertEqual(request(ReadOnlyLifecycleApp(lambda:value))[0],503)

if __name__=='__main__':unittest.main()
