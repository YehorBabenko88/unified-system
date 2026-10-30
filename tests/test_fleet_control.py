import tempfile
import unittest
from pathlib import Path
from unified_system.fleet_control import FleetControl, FleetError

class FleetTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'fleet.db'
        self.f=FleetControl(self.path, ['a','b','c'])
    def ready(self,n=1):
        for i in range(n):
            self.f.approve_node(str(i),1,'zone'+str(i),'owner-ticket')
            self.f.heartbeat(str(i),1,1,10,{'cpu':8,'memory':16,'disk':100})
        self.f.elect(1,'a',['a','b'],10,100)
    def test_sizes(self):
        for n in [0,1,5,6,7,12]:
            with self.subTest(n=n):
                f=FleetControl(Path(self.tmp.name)/f'{n}.db',['a'])
                for i in range(n): f.approve_node(str(i),1,'office','approved')
                self.assertEqual(len(f.snapshot(0)['nodes']),n)
                self.assertFalse(f.snapshot(0)['execution_authorized'])
    def test_cumulative_capacity_idempotence_and_restart(self):
        self.ready(); self.f.submit('x',{'cpu':5,'memory':4,'disk':1})
        lease=self.f.place('x',10,1)
        self.assertEqual(lease,self.f.place('x',11,1))
        self.f.submit('y',{'cpu':5,'memory':4,'disk':1})
        with self.assertRaises(FleetError): self.f.place('y',11,1)
        f=FleetControl(self.path,['a','b','c']); self.assertTrue(f.validate_lease('x',lease['token'],12))
        with self.assertRaises(FleetError): f.submit('x',{'cpu':1,'memory':1,'disk':1})
    def test_epoch_sequence_stale_and_drain(self):
        self.ready(); self.f.submit('x',{'cpu':1,'memory':1,'disk':1})
        for epoch,seq in [(1,1),(0,2)]:
            with self.assertRaises(FleetError): self.f.heartbeat('0',epoch,seq,11,{'cpu':8,'memory':16,'disk':100})
        with self.assertRaises(FleetError): self.f.place('x',41,1)
        self.f.heartbeat('0',1,2,42,{'cpu':8,'memory':16,'disk':100})
        self.f.drain('0');
        with self.assertRaises(FleetError): self.f.place('x',42,1)
    def test_quorum_splitbrain_expiry_and_db_loss(self):
        self.ready(); self.f.submit('x',{'cpu':1,'memory':1,'disk':1}); lease=self.f.place('x',10,1)
        with self.assertRaises(FleetError): self.f.elect(2,'c',['c'],11,100)
        self.f.elect(2,'c',['b','c'],11,100)
        self.assertFalse(self.f.validate_lease('x',lease['token'],12))
        with self.assertRaises(FleetError): self.f.place('x',12,2)
        self.assertFalse(self.f.validate_lease('x',lease['token'],70))
        self.f.heartbeat('0',1,2,70,{'cpu':8,'memory':16,'disk':100})
        self.assertNotEqual(lease['token'],self.f.place('x',70,2)['token'])
        self.path.unlink()
        with self.assertRaises(FleetError): self.f.place('x',71,2)
    def test_failure_domain_restore_and_diskfull(self):
        self.ready(2); self.f.submit('x',{'cpu':1,'memory':1,'disk':1},avoid_domains=['zone0'])
        lease=self.f.place('x',10,1); self.assertEqual(lease['node'],'1')
        backup=Path(self.tmp.name)/'backup.db'; self.f.backup(backup)
        restored=FleetControl.restore(backup,Path(self.tmp.name)/'restored.db',['a','b','c'])
        self.assertFalse(restored.validate_lease('x',lease['token'],11))
        with self.assertRaises(FleetError): restored.place('x',11,1)
        # SQLite max_page_count forces a real disposable disk-full transaction failure.
        import sqlite3
        self.f.max_pages=2
        before=self.f.snapshot(10)
        with self.assertRaises(FleetError): self.f.approve_node('large',1,'z','x'*100000)
        self.assertEqual(before,self.f.snapshot(10))

    def test_clock_rollback_and_leader_loss(self):
        self.ready(); self.f.submit('x',{'cpu':1,'memory':1,'disk':1})
        with self.assertRaises(FleetError): self.f.place('x',9,1)
        with self.assertRaises(FleetError): self.f.place('x',110,1)
        with self.assertRaises(FleetError): self.f.elect(2,'a',['a','a'],110,100)
    def test_telemetry_pressure_and_unknown_nodes(self):
        self.ready(); self.f.submit('x',{'cpu':1,'memory':1,'disk':1})
        self.f.heartbeat('0',1,2,11,{'cpu':0,'memory':0,'disk':0})
        with self.assertRaises(FleetError): self.f.place('x',11,1)
        for bad in [float('nan'),float('inf'),-1,True]:
            with self.assertRaises(FleetError): self.f.heartbeat('0',1,3,12,{'cpu':bad,'memory':1,'disk':1})
        with self.assertRaises(FleetError): self.f.heartbeat('unknown',1,1,11,{'cpu':1,'memory':1,'disk':1})
    def test_identity_rotation_revokes_and_waits_expiry(self):
        self.ready(); self.f.submit('x',{'cpu':1,'memory':1,'disk':1}); lease=self.f.place('x',10,1)
        self.f.approve_node('0',2,'zone0','new-owner-ticket')
        self.f.heartbeat('0',2,1,11,{'cpu':8,'memory':16,'disk':100})
        self.assertFalse(self.f.validate_lease('x',lease['token'],11))
        with self.assertRaises(FleetError): self.f.place('x',11,1)
    def test_read_only_adapter_does_not_infer_observations(self):
        self.ready(); snap=self.f.status_snapshot(10000)
        self.assertEqual(snap['links'],[])
        self.assertIsNone(snap['nodes'][0]['cpu'])
        self.assertIsNone(snap['nodes'][0]['db_sizes'])
        self.assertFalse(snap['nodes'][0]['identity_verified'])
        self.assertEqual(self.f.snapshot(41)['nodes']['0']['state'],'SUSPECT')
        self.assertEqual(self.f.snapshot(71)['nodes']['0']['state'],'OFFLINE')
    def test_concurrent_duplicate_placements_share_one_token(self):
        from concurrent.futures import ThreadPoolExecutor
        self.ready(); self.f.submit('x',{'cpu':1,'memory':1,'disk':1})
        with ThreadPoolExecutor(max_workers=4) as pool:
            leases=list(pool.map(lambda _:self.f.place('x',10,1),range(8)))
        self.assertEqual(len({x['token'] for x in leases}),1)

    def test_persisted_authority_tamper_fails_closed(self):
        import sqlite3,json
        from contextlib import closing
        self.ready(); self.f.submit('x',{'cpu':1,'memory':1,'disk':1});self.f.place('x',10,1)
        with closing(sqlite3.connect(self.path)) as c,c:
            state=json.loads(c.execute('SELECT body FROM ledger').fetchone()[0])
            state['jobs']['x']['lease']['execution_authorized']=True
            c.execute('UPDATE ledger SET body=?',(json.dumps(state),))
        with self.assertRaises(FleetError):self.f.snapshot(11)
        with self.assertRaises(FleetError):self.f.place('x',11,1)
