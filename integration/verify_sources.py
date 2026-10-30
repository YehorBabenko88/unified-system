"""Actual pinned APIs with disposable state; no physical or receipt admission."""
import argparse
import itertools
import inspect
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PINS = json.loads((ROOT/'integration/source-pins.json').read_text())
parser = argparse.ArgumentParser()
for name in ('terminan','math','grid','strattester'):
    parser.add_argument('--'+name, required=True, type=Path)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
sources = {name: getattr(args,name).resolve() for name in ('terminan','math','grid','strattester')}
observed = {}
for name, source in sources.items():
    head = subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
    if head != PINS[name]:
        raise SystemExit('SOURCE_PIN_MISMATCH:'+name)
    if subprocess.check_output(['git','-C',str(source),'status','--porcelain','--untracked-files=no'],text=True).strip():
        raise SystemExit('SOURCE_DIRTY:'+name)
    observed[name] = {'head':head, 'tree':subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD^{tree}'],text=True).strip()}
    sys.path.insert(0,str(source))

from unified_system.fleet_control import FleetControl, FleetError
from unified_system.lifecycle import Lifecycle, MODULES
from terminan.infrastructure import validate as consume
from grid.history_export_v11 import export_records_v11
from grid.research_handoff import accept_handoff
from strattester.research.runner import ResearchRunner
from strattester.marketdata.sqlite_store import SQLiteMarketStore
from strattester.strategies.base import StrategyDefinition, DataRequirement
from strattester.engine.executor import ResearchExecutionPermit
from strattester.persistence.result_store import ResultStore

NETWORK_ATTEMPTS = []
def deny_network(*args, **kwargs):
    NETWORK_ATTEMPTS.append(repr(args))
    raise AssertionError('external network forbidden in source integration')

class OfflineHistory:
    def __init__(self, gap=False):self.calls=0;self.gap=gap
    def fetch_klines(self,symbol,start,end,interval='1'):
        self.calls += 1
        return [[str(t),'1','2','1','2','1','2'] for t in (0,60000) if start<=t<=end and not (self.gap and t==60000)]

class Research:
    def run(self,candles,checkpoint=None):return {'sum':sum(row.close for row in candles)}

class FiveSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='five-source-')
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)
    def fleet(self):return FleetControl(self.path/'fleet.db',['v1','v2','v3'])
    def test_node_sizes_actual_consumer_unknown_observations(self):
        fleet=self.fleet()
        for target in (0,1,5,6,7,10):
            existing=len(fleet.snapshot(100)['nodes'])
            for i in range(existing,target):
                fleet.approve_node('node-'+str(i),1,'zone-'+str(i%2),'SOFTWARE_TEST_ONLY')
                fleet.heartbeat('node-'+str(i),1,1,100,{'cpu':8,'memory':32,'disk':100})
            life=Lifecycle(self.path/('life-'+str(target)+'.db'),sorted(MODULES),fleet_provider=lambda:fleet.status_snapshot(100000))
            raw=life.initialize()
            view=consume(raw)
            self.assertEqual(len(view['nodes']),target)
            self.assertEqual(view['links'],[])
            self.assertIs(view['trading_authorized'],False)
            for node in view['nodes']:
                for metric in ('cpu','memory','disk','db_sizes'):self.assertIsNone(node[metric])
            (args.output/f'snapshot-{target}.json').write_text(json.dumps(view),encoding='utf-8')
            (args.output/f'lifecycle-{target}.json').write_text(json.dumps(raw),encoding='utf-8')
    def test_every_module_availability_combination_remains_read_only(self):
        names=sorted(MODULES)
        for bits in itertools.product((False,True),repeat=len(names)):
            available=[name for name,present in zip(names,bits) if present]
            life=Lifecycle(self.path/('availability-'+''.join(map(lambda v:str(int(v)),bits))+'.db'),available)
            view=consume(life.initialize())
            self.assertEqual(view['state'],'AVAILABLE_UNVERIFIED')
            self.assertEqual(view['available_modules'],available)
            self.assertEqual(view['paper']['status'],'NOT_AUTHORIZED')
            self.assertFalse(view['execution_authorized'])
    def test_resource_pressure_rebalance_expiry_drain_and_restart(self):
        fleet=self.fleet()
        for i in range(2):
            fleet.approve_node(str(i),1,'domain-'+str(i),'SOFTWARE_TEST_ONLY')
            fleet.heartbeat(str(i),1,1,100,{'cpu':8,'memory':32,'disk':100})
        fleet.elect(1,'v1',['v1','v2'],100,100)
        for metric,amount in (('cpu',7),('memory',28),('disk',86)):
            requirements={'cpu':0,'memory':0,'disk':0};requirements[metric]=amount
            fleet.submit(metric,requirements)
            with self.assertRaises(FleetError):fleet.place(metric,100,1)
        fleet.submit('work',{'cpu':1,'memory':1,'disk':1})
        lease=fleet.place('work',100,1,ttl=5)
        fleet.drain(lease['node'])
        with self.assertRaises(FleetError):fleet.retire(lease['node'],101)
        fleet.retire(lease['node'],105)
        second=fleet.place('work',105,1)
        self.assertNotEqual(second['node'],lease['node'])
        self.assertFalse(fleet.validate_lease('work',lease['token'],105))
        restart=FleetControl(self.path/'fleet.db',['v1','v2','v3'])
        self.assertEqual(restart.place('work',105,1)['token'],second['token'])
        self.assertFalse(second['execution_authorized'])
    def test_quorum_leader_db_loss_and_stale_consumer(self):
        fleet=self.fleet()
        with self.assertRaises(FleetError):fleet.elect(1,'v1',['v1'],100,5)
        fleet.approve_node('one',1,'zone','SOFTWARE_TEST_ONLY')
        fleet.heartbeat('one',1,1,100,{'cpu':8,'memory':32,'disk':100})
        fleet.elect(1,'v1',['v1','v2'],100,5)
        fleet.submit('job',{'cpu':1,'memory':1,'disk':1})
        lease=fleet.place('job',100,1)
        self.assertFalse(fleet.validate_lease('job',lease['token'],105))
        stale=consume(Lifecycle(self.path/'stale.db',[],fleet_provider=lambda:fleet.status_snapshot(161000)).initialize())
        self.assertEqual(stale['nodes'][0]['state'],'OFFLINE')
        life=Lifecycle(self.path/'loss.db',[],fleet_provider=lambda:fleet.status_snapshot(161000))
        life.initialize();(self.path/'fleet.db').unlink()
        self.assertEqual(consume(life.snapshot())['nodes'],[])
    def test_actual_research_sync_and_incomplete_history_denial(self):
        definition=StrategyDefinition('source-test','1',(DataRequirement('candles',('1m',)),),Research)
        for gap in (False,True):
            store=SQLiteMarketStore.open(self.path/('history-'+str(gap)+'.db'))
            try:
                client=OfflineHistory(gap)
                runner=ResearchRunner(store,client,clock_ms=lambda:999999)
                permit=ResearchExecutionPermit.for_strategy(definition,reason='Disposable source regression, no exchange execution')
                kwargs=dict(start_ms=0,end_ms=60000,research_permission=permit)
                if gap:
                    with self.assertRaises(RuntimeError):runner.run(definition,{'symbol':'BTCUSDT','launchTime':'0'},**kwargs)
                else:
                    self.assertEqual(runner.run(definition,{'symbol':'BTCUSDT','launchTime':'0'},**kwargs).output,{'sum':4})
                self.assertGreater(client.calls,0)
            finally:store.close()
    def test_unattested_grid_export_and_handoff_denied(self):
        request={'schema':'grid.history.request.v1','venue':'bybit','market_type':'linear','symbol':'BTCUSDT','start_ms':0,'end_ms':60000,'as_of_ms':60000,'max_age_ms':60000,'units':{'price':'USDT/BTC','volume':'BTC'}}
        with self.assertRaises(ValueError):export_records_v11([],request,{})
        self.assertEqual(accept_handoff({},set())['status'],'UNAVAILABLE')
        self.assertEqual(accept_handoff({'execution_authority':True},set())['status'],'UNAVAILABLE')
    def test_latest_result_schema_cannot_substitute_for_sealed_receipt(self):
        signature=str(inspect.signature(ResearchRunner.run))
        self.assertNotIn('provenance',signature)
        self.assertNotIn('result_store',signature)
        store=ResultStore.open(self.path/'results.db')
        try:
            tables=[r[0] for r in store.con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            self.assertNotIn('owned_runs',tables)
            store.put('software-test','BTCUSDT','source-test','1',{'sum':4},created_at=1)
            persisted=json.loads(store.con.execute('SELECT metrics FROM research_results').fetchone()[0])
            denied=accept_handoff(persisted,set())
            self.assertEqual(denied['status'],'UNAVAILABLE')
            (args.output/'handoff-interface-gap.json').write_text(json.dumps({'signature':signature,'tables':tables,'grid_intake':denied,'positive_handoff':'BLOCKED_NO_SEALED_PRODUCER_INTERFACE'}),encoding='utf-8')
        finally:store.close()
    def test_consumer_version_negotiation_denies_bool_or_future(self):
        life=Lifecycle(self.path/'version.db',[]);view=life.initialize()
        for version in ({'major':True,'minor':0},{'major':2,'minor':0},{'major':1,'minor':1}):
            with self.assertRaises(ValueError):consume({**view,'api_version':version})

args.output.mkdir(parents=True,exist_ok=True)
with patch.object(socket.socket,'connect',deny_network),patch('socket.create_connection',deny_network):
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(FiveSourceTests))
if NETWORK_ATTEMPTS:raise SystemExit('NETWORK_DENIAL_ATTEMPTS:'+str(len(NETWORK_ATTEMPTS)))
math=subprocess.run(['node','--test',str(sources['math']/'tests/bounded-experiment.test.mjs')],capture_output=True,text=True,timeout=40)
(args.output/'math-tests.log').write_text(math.stdout+math.stderr,encoding='utf-8')
head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
evidence={'schema':'unified.five-source.v1','head':head,'tree':subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD^{tree}'],text=True).strip(),'sources':observed,'python_tests':result.testsRun,'python_failures':len(result.failures),'python_errors':len(result.errors),'python_skips':len(result.skipped),'math_exit':math.returncode,'network_attempts':len(NETWORK_ATTEMPTS),'source_provenance':'BLOCKED','physical':'NOT_RUN','production':'NO_GO','run':os.getenv('GITHUB_RUN_ID'),'attempt':os.getenv('GITHUB_RUN_ATTEMPT'),'job':os.getenv('GITHUB_JOB')}
(args.output/'evidence.json').write_text(json.dumps(evidence,sort_keys=True,indent=2),encoding='utf-8')
raise SystemExit(0 if result.wasSuccessful() and not result.skipped and math.returncode==0 else 1)
