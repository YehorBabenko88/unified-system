"""Actual local shared-store tests; no provider or distributed authority."""
import tempfile
import multiprocessing
import sqlite3
import contextlib
import queue
import threading
import unittest
from unittest.mock import patch
from pathlib import Path
from unified_system.network_budget import BandwidthPolicy, NodeBudget, EgressProjection, BudgetError

NODES = ('LS5','PC1','PC2','PC3','PC4','LS7')


def _compete(path,output):
    policy=BandwidthPolicy({n:{'rate':1000,'burst':1000} for n in NODES},cluster_rate=6000,cluster_burst=6000,classes={'control':20,'live':50,'bulk':30})
    budget=NodeBudget.isolated(path,'LS5',policy,clock=lambda:0,clock_id='boot')
    output.put(budget.try_take('tx','PC1','control',50,now_ms=1000))


class BudgetTests(unittest.TestCase):
    def policy(self):
        return BandwidthPolicy({n: {'rate': 1000, 'burst': 1000} for n in NODES},
                               cluster_rate=6000, cluster_burst=6000,
                               classes={'control':20,'live':50,'bulk':30})

    def test_cluster_allocations_cannot_expand(self):
        with self.assertRaises(BudgetError):
            BandwidthPolicy({n:{'rate':1000,'burst':1000} for n in NODES},
                            cluster_rate=5000,cluster_burst=6000,
                            classes={'control':20,'live':50,'bulk':30})

    def test_two_instances_share_atomic_debit_and_restart_not_fresh_burst(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'budget.sqlite'
            a=NodeBudget.isolated(path,'LS5',self.policy(),clock=lambda:0,clock_id='boot')
            b=NodeBudget.isolated(path,'LS5',self.policy(),clock=lambda:0,clock_id='boot')
            self.assertFalse(a.try_take('tx','PC1','control',1,now_ms=0))
            self.assertTrue(a.try_take('tx','PC1','control',200,now_ms=1000))
            self.assertFalse(b.try_take('tx','PC1','control',1,now_ms=1000))
            self.assertFalse(a.try_take('tx','PC1','bulk',301,now_ms=1000))
            self.assertTrue(b.try_take('tx','PC1','live',500,now_ms=1000))
            reopened=NodeBudget.isolated(path,'LS5',self.policy(),clock=lambda:0,clock_id='boot')
            self.assertFalse(reopened.try_take('tx','PC1','control',1,now_ms=1000))

    def test_backward_clock_or_changed_policy_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'budget.sqlite'
            a=NodeBudget.isolated(path,'LS5',self.policy(),clock=lambda:0,clock_id='boot')
            a.try_take('tx','PC1','live',1,now_ms=1000)
            with self.assertRaises(BudgetError):
                a.try_take('tx','PC1','live',1,now_ms=999)
            with self.assertRaises(BudgetError):
                NodeBudget.runtime(path,'LS5',self.policy())

    def test_egress_unknown_and_cooldown_survive_restart_no_dispatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'egress.sqlite'
            e=EgressProjection.isolated(path)
            e.apply_verified({'event_id':'e1','attempt_id':'a1','scope':'scope1','state':'CHARGED','cooldown_until_ms':1000,'cost':7,'policy_digest':'1'*64}, verifier=lambda event: True)
            e.apply_verified({'event_id':'e2','attempt_id':'a1','scope':'scope1','state':'UNKNOWN','cooldown_until_ms':2000,'cost':7,'policy_digest':'1'*64}, verifier=lambda event: True)
            e=EgressProjection.isolated(path)
            self.assertEqual(e.snapshot()['scopes']['scope1']['cooldown_until_ms'],2000)
            self.assertTrue(e.snapshot()['scopes']['scope1']['frozen'])
            self.assertEqual(e.snapshot()['scopes']['scope1']['usage_cost'],7)
            self.assertEqual(e.acquire(), 'SAFETY_GATE_CLOSED')
            self.assertEqual(e.prepare_dispatch('a1'),'SAFETY_GATE_CLOSED')
            with self.assertRaises(BudgetError):
                e.apply_verified({'event_id':'e3','attempt_id':'a1','scope':'scope1','state':'CANCELLED','cooldown_until_ms':0,'cost':7,'policy_digest':'1'*64}, verifier=lambda event: True)

    def test_real_processes_cannot_each_receive_a_fresh_full_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'shared.sqlite'
            a=NodeBudget.isolated(path,'LS5',self.policy(),clock=lambda:0,clock_id='boot')
            self.assertTrue(a.try_take('tx','PC1','control',1,now_ms=1000))
            ctx=multiprocessing.get_context('spawn');out=ctx.Queue()
            workers=[ctx.Process(target=_compete,args=(str(path),out)) for _ in range(4)]
            started=[]
            try:
                for p in workers:
                    p.start();started.append(p)
                for p in started:
                    p.join(10)
                    if p.is_alive():self.fail('budget child deadline')
                    self.assertEqual(p.exitcode,0,'budget child failed')
                self.assertEqual(sum(out.get(timeout=1) for _ in started),3)
            finally:
                # Failure of one child must not leave siblings holding SQLite
                # while TemporaryDirectory cleanup runs (notably on Windows).
                for p in started:
                    if p.is_alive():p.terminate()
                for p in started:
                    p.join(3)
                    if p.is_alive():p.kill();p.join(3)
                    self.assertFalse(p.is_alive(),'owned budget child cleanup deadline')
                out.close();out.join_thread()

    def test_foreign_or_incomplete_database_not_adopted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'foreign.sqlite'
            with contextlib.closing(sqlite3.connect(path)) as con:
                con.execute('CREATE TABLE foreign_data(x)');con.commit()
            with self.assertRaises(BudgetError):NodeBudget.isolated(path,'LS5',self.policy(),clock=lambda:0)
            with self.assertRaises(BudgetError):EgressProjection.isolated(path)

    def test_egress_replay_conflict_and_unverified_receipt_no_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            e=EgressProjection.isolated(Path(tmp)/'projection.sqlite')
            event={'event_id':'e1','attempt_id':'a1','scope':'scope1','state':'CHARGED','cooldown_until_ms':1000,'cost':7,'policy_digest':'1'*64}
            with self.assertRaises(BudgetError):e.apply_verified(event,verifier=lambda _:False)
            self.assertEqual(e.snapshot()['attempts'],{})
            e.apply_verified(event,verifier=lambda _:True);e.apply_verified(event,verifier=lambda _:True)
            with self.assertRaises(BudgetError):e.apply_verified(dict(event,cooldown_until_ms=0),verifier=lambda _:True)
            self.assertEqual(e.snapshot()['scopes']['scope1']['cooldown_until_ms'],1000)

    def test_clock_sample_is_inside_store_transaction_not_before_lock_wait(self):
        with tempfile.TemporaryDirectory() as tmp:
            ticks=[0];sampled=threading.Event();main=threading.get_ident();results=queue.Queue()
            def clock():
                value=ticks[0]
                if threading.get_ident()!=main:sampled.set()
                return value
            path=Path(tmp)/'shared.sqlite'
            a=NodeBudget.isolated(path,'LS5',self.policy(),clock=clock,clock_id='boot')
            b=NodeBudget.isolated(path,'LS5',self.policy(),clock=lambda:0,clock_id='boot')
            def contend():
                try:results.put(a.try_take('tx','PC1','live',1))
                except Exception as exc:results.put(exc)
            ticks[0]=1
            with a.lock:
                t=threading.Thread(target=contend);t.start()
                sampled.wait(.1)
                ticks[0]=2
                self.assertTrue(b.try_take('tx','PC1','live',1,now_ms=2000))
            t.join(2)
            self.assertIs(results.get(timeout=1),True)




def _faulting_budget_fixture(path, ready, index):
    if index==0:
        if not ready.wait(5):raise RuntimeError('fixture readiness deadline')
        raise SystemExit(7)
    with contextlib.closing(sqlite3.connect(path)) as con:
        con.execute('SELECT * FROM meta').fetchone()
        ready.set()
        threading.Event().wait(30)


class BudgetCleanupTests(unittest.TestCase):
    def test_failed_child_cleans_all_owned_siblings_before_directory_cleanup(self):
        ctx=multiprocessing.get_context('spawn');ready=ctx.Event();created=[]
        class Context:
            Queue=staticmethod(ctx.Queue)
            def Process(self,*,target,args):
                process=ctx.Process(target=_faulting_budget_fixture,args=(args[0],ready,len(created)))
                created.append(process);return process
        result=unittest.TestResult()
        try:
            with patch.object(multiprocessing,'get_context',return_value=Context()):
                BudgetTests('test_real_processes_cannot_each_receive_a_fresh_full_budget').run(result)
            self.assertEqual(result.errors,[],'cleanup must not replace the child assertion')
            self.assertEqual(len(result.failures),1)
            self.assertIn('7 != 0 : budget child failed',result.failures[0][1])
            self.assertFalse(any(p.is_alive() for p in created),'owned sibling survived failed fixture')
            self.assertFalse(any('PermissionError' in detail for _,detail in result.errors),'SQLite cleanup ran before child exit')
        finally:
            for process in created:
                if process.is_alive():process.terminate()
            for process in created:
                process.join(3)
                if process.is_alive():process.kill();process.join(3)


if __name__=='__main__': unittest.main()
