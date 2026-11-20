"""Real installed SDK APIs with synthetic inputs/fake persistence only.

No socket, process, native call or SQL connection is permitted by the runner.
"""
import copy,hashlib,json,os,unittest
from contextlib import contextmanager
from datetime import datetime,timedelta,timezone
from decimal import Decimal as D,localcontext
from types import SimpleNamespace
from unittest.mock import patch
import market_math as math_owner
from market_data.public_trades import Trade,execution_record
from market_data.footprint_state import FootprintBuilder
from market_data.history_export_v11 import export_records_v11
from market_data.provenance import digest
from terminan.research_import import validate_research_import
from terminan.analytics.orderflow_adapters import from_records
from terminan.analytics.orderflow_aggregation import aggregate_by_time,aggregate_by_price
from terminan.analytics.market_history import analyze_market_history
from terminan import paper

def complete(coroutine):
 try:coroutine.send(None)
 except StopIteration as done:return done.value
 finally:coroutine.close()
 raise AssertionError('unexpected asynchronous yield in inert fake')

def history_fixture(n=3):
 rows=[];receipts={}
 for i in range(n):
  row=dict(symbol='BTCUSDT',start_ms=i*60000,end_ms=i*60000+59999,source_event_start_ms=i*60000+1,source_event_end_ms=i*60000+59998,source=dict(identity='synthetic-four-owner',source_revision='a'*40,epoch='synthetic-epoch',market_type='linear'),representation='historical_aggregate',status='PARTIAL',candle=dict(open=100+i,high=102+i,low=99+i,close=101+i,buy_volume=2,sell_volume=1))
  row['dataset_fingerprint']=digest(row);rows.append(row)
  receipts[row['dataset_fingerprint']]=dict(fingerprint=row['dataset_fingerprint'],venue='bybit',available_at_ms=(i+1)*60000,complete=True,watermark_ms=(i+1)*60000,units=dict(price='USDT/BTC',volume='BTC'),evidence_class='SYNTHETIC')
 request=dict(schema='market_data.history.request.v1',venue='bybit',market_type='linear',symbol='BTCUSDT',start_ms=0,end_ms=n*60000,as_of_ms=n*60000,max_age_ms=60000,units=dict(price='USDT/BTC',volume='BTC'))
 trust=dict(identity='synthetic-four-owner',source_revision='a'*40,epoch='synthetic-epoch',receipts=receipts,receipt_pins={k:digest(v) for k,v in receipts.items()},evidence_class='SYNTHETIC')
 return rows,request,trust

def replay_request():
 builder=FootprintBuilder(1)
 for index,side in ((1,'Buy'),(2,'Sell')):builder.add(Trade('BTCUSDT',index,D(100),D(1),side,str(index)))
 row=builder.pop_closed(60000)[0]
 profile=[dict(price=str(level['price']),volume=str(level['volume'])) for level in row['levels']]
 return dict(schema='terminan.paper.replay.v2',run_id='four-owner-synthetic',source=dict(snapshot_sha256=digest(row),as_of_ms=62000,units=dict(price='quote/base',volume='base')),parameters=dict(notional='102',fee_rate='0',slippage_bps='0'),events=[dict(kind='closed_minute',event_ms=60000,symbol='BTCUSDT',profile=profile,close='100'),dict(kind='trade',event_ms=61000,symbol='BTCUSDT',price='102'),dict(kind='trade',event_ms=62000,symbol='BTCUSDT',price='100')])

class CanonicalSdkTests(unittest.TestCase):
 def test_exact_data_trade_to_math_terminal_precision_3_5_28(self):
  import market_compute_api as api
  import terminan.analytics.orderflow_aggregation as bridge
  self.assertIs(bridge.aggregate_orderflow_stream,api.aggregate_orderflow_stream)
  for precision in (3,5,28):
   with localcontext() as context:
    context.prec=precision
    for signal in context.traps:context.traps[signal]=True
    def records():
     for i in range(100000):
      trade=Trade('BTCUSDT',i,D('100.005'),D('1e-50'),'Buy',str(i))
      yield dict(timestamp_ms=trade.ts_ms,price=trade.price,volume=trade.qty,side=trade.side)
    grouped=aggregate_by_time(from_records(records()),60000)
    self.assertEqual(sum(row.trade_count for _,row in grouped),100000)
    self.assertEqual(math_owner.exact_sum(row.buy_volume for _,row in grouped),D('1e-45'))
    priced=aggregate_by_price(from_records([dict(timestamp_ms=1,price='100.005',volume='0.1',side='buy')]),D('.1'))
    self.assertEqual(priced[0][0],D('100.0'));self.assertFalse(any(context.flags.values()))
 def test_data_first_seen_poc_half_even_and_finalization_refusal(self):
  for precision in (3,5,28):
   with localcontext() as context:
    context.prec=precision
    for signal in context.traps:context.traps[signal]=True
    builder=FootprintBuilder('.5');builder.add(Trade('BTCUSDT',1,D('1.25'),D(1),'Buy','a'));builder.add(Trade('BTCUSDT',2,D('1.75'),D(1),'Sell','b'))
    row=builder.pop_closed(60000)[0];self.assertEqual(row['poc_price'],1.);self.assertEqual([v['price']for v in row['levels']],[1.,2.])
    self.assertFalse(builder.add(Trade('BTCUSDT',1,D(1),D(1),'Buy','late')))
 def test_actual_data_history_export_to_terminal_causal_analysis(self):
  rows,q,trust=history_fixture();before=copy.deepcopy((rows,q,trust));packet=export_records_v11(rows,q,trust)
  early=analyze_market_history(packet,decision_ms=60000);full=analyze_market_history(packet,decision_ms=180000)
  self.assertEqual(len(early['candles']),1);self.assertEqual(early['excluded_rows'],2);self.assertEqual(len(full['candles']),3)
  for value in (early,full):
   self.assertEqual(value['source_authenticity'],'NOT_EVALUATED');self.assertIs(value['execution_authority'],False);self.assertIs(value['trading_authorized'],False)
   self.assertTrue(all(level['available_at_ms']<=value['decision_ms'] for level in value['levels']))
  self.assertEqual((rows,q,trust),before)
  later=export_records_v11(rows,{**q,'as_of_ms':180001},trust)
  self.assertEqual(packet['dataset_id'],later['dataset_id']);self.assertNotEqual(packet['dataset_fingerprint'],later['dataset_fingerprint'])
 def test_history_tamper_future_watermark_and_authority_upgrade_refuse(self):
  rows,q,trust=history_fixture();packet=export_records_v11(rows,q,trust)
  for mutate in (lambda p:p['rows'][0].update(close=999),lambda p:p.update(execution_authority=True),lambda p:p.update(schema='grid.history.v1.1')):
   changed=copy.deepcopy(packet);mutate(changed)
   with self.assertRaises(ValueError):analyze_market_history(changed,decision_ms=180000)
  fp=rows[0]['dataset_fingerprint'];trust['receipts'][fp]['watermark_ms']=120000;trust['receipt_pins'][fp]=digest(trust['receipts'][fp])
  with self.assertRaises(ValueError):export_records_v11(rows,q,trust)
 def test_canonical_handoff_receiver_and_independent_root_receipt_oracle(self):
  from unified_system.lifecycle import MODULES
  self.assertEqual(set(MODULES),{'unified_system','market_data','math','terminan'})
  import test_release_boundary as fixture
  record=copy.deepcopy(fixture.RECORD);pin=(record['producer_identity'],record['source_revision'],record['run_id'],record['completion_receipt'])
  self.assertEqual(validate_research_import(record,())["status"],'UNAVAILABLE')
  accepted=validate_research_import(record,(pin,));self.assertEqual(accepted['status'],'ACCEPTED_HISTORICAL');self.assertIs(accepted['trading_authorized'],False)
  historical=fixture.boundary().verify(record,observed_revision=fixture.PIN.revision,observed_tree=fixture.PIN.tree,artifact_bytes=fixture.ARTIFACT)
  self.assertEqual(historical['verdict'],'VERIFIED_SOURCE_RECEIPT');self.assertIs(historical['execution_authorized'],False);self.assertIs(historical['trading_authorized'],False);self.assertEqual(historical['physical_acceptance'],'NOT_RUN')
  for version in ({'major':True,'minor':1},{'major':2,'minor':0}):
   invalid=copy.deepcopy(record);invalid['api_version']=version;self.assertEqual(validate_research_import(invalid,(pin,))['status'],'UNAVAILABLE')
  self.assertEqual(validate_research_import({'schema':'terminan.paper.result.v2','status':'COMPLETE'},(pin,))['status'],'UNAVAILABLE')
  record['metrics']['sum']=999
  self.assertEqual(validate_research_import(record,(pin,))['reason'],'RESEARCH_RECEIPT_CORRUPT')
  self.assertEqual(fixture.boundary().verify(record,observed_revision=fixture.PIN.revision,observed_tree=fixture.PIN.tree,artifact_bytes=fixture.ARTIFACT)['verdict'],'UNAVAILABLE')
 def test_actual_data_profile_math_and_sole_terminal_replay_remain_unattested(self):
  request=replay_request();before=copy.deepcopy(request)
  with patch.dict(os.environ,{'TERMINAN_PAPER_LEDGER':''}):
   for precision in (3,5,28):
    with localcontext() as context:
     context.prec=precision
     for signal in context.traps:context.traps[signal]=True
     result=paper.replay_paper(request)
     self.assertEqual(D(result['fills'][0]['net']),D(2));self.assertIs(result['execution_authority'],False);self.assertIs(result['trading_authorized'],False);self.assertEqual(result['status'],'OFFLINE_UNATTESTED')
     self.assertFalse(any(context.flags.values()))
  self.assertEqual(request,before);self.assertTrue(all(d.implementation is paper.PaperEngine for d in paper.STRATEGIES.discover()))
 def test_paper_owner_refusal_and_future_input_do_not_publish_receipt(self):
  request=replay_request();request['source']['as_of_ms']=61000
  with patch.dict(os.environ,{'TERMINAN_PAPER_LEDGER':''}),self.assertRaises(ValueError):paper.replay_paper(request)
  engine=paper.PaperEngine(fee_rate=D(0),slippage_bps=D(0));engine.enabled=True;start=datetime(2026,1,1,tzinfo=timezone.utc)
  engine.on_closed_minute('BTCUSDT',paper.ClosedMinute(start,D(100),True));engine.on_trade(paper.ExecutionTrade('BTCUSDT',start+timedelta(seconds=61),D(102)));before=copy.deepcopy(engine.__dict__)
  with patch('market_math.paper_fill_metrics',side_effect=ValueError('SYNTHETIC_OWNER_REFUSAL')),self.assertRaises(ValueError):engine.on_trade(paper.ExecutionTrade('BTCUSDT',start+timedelta(seconds=62),D(100)))
  self.assertEqual(engine.__dict__,before)
 def test_nonatomic_ledger_ack_requires_readback_on_retry_and_conflict_refusal(self):
  class FakeLedger:
   saved=None;writes=0
   def __init__(self,path):pass
   @classmethod
   def lookup_existing(cls,path,run_id,sha):
    if cls.saved is None:return None
    if cls.saved['request_sha256']!=sha:raise ValueError('INERT_REPLAY_CONFLICT')
    return copy.deepcopy(cls.saved)
   def record(self,result):
    type(self).saved=copy.deepcopy(result);type(self).writes+=1;raise OSError('SYNTHETIC_COMMIT_ACK_LOST')
  request=replay_request()
  with patch.object(paper,'PaperReplayLedger',FakeLedger),patch.dict(os.environ,{'TERMINAN_PAPER_LEDGER':'INERT_NOT_A_DATABASE'}):
   with self.assertRaises(OSError):paper.replay_paper(request)
   with patch('market_compute_api.compute_batch',side_effect=AssertionError('NO_REEXECUTION')):
    replay=paper.replay_paper(request)
   self.assertEqual(replay,FakeLedger.saved);self.assertEqual(FakeLedger.writes,1)
   request['parameters']['notional']='103'
   with self.assertRaises(ValueError):paper.replay_paper(request)
 def test_archive_unconfirmed_commit_keeps_wal_and_poisoned_owner_refuses_retry(self):
  from market_data import archive_import as archive
  from market_data.raw_capture import decode_observation
  from market_data.public_trades import digest_json
  event=execution_record(Trade('BTCUSDT',1735689600000,D(1),D('.1'),'Buy','one'))
  @contextmanager
  def snapshot(*args):yield 'INERT_BLOB'
  class WAL:
   def __init__(self):self.pending={};self.acks=[]
   def iter_recover(self):return list(self.pending.items())
   async def append(self,payload):self.pending['one']=copy.deepcopy(payload);return 'one'
   async def ack(self,rid):self.acks.append(rid);self.pending.pop(rid)
  class Store:
   def __init__(self,mode):self.mode=mode;self.calls=0
   async def archive_checkpoint(self,identity):return None
   async def store_archive_batch(self,*,observation_bytes,events):
    self.calls+=1;a=decode_observation(observation_bytes)['archive'];result=dict(import_id=a['import_id'],committed_source_rows=int(a['end_row']),observation_sha256=hashlib.sha256(observation_bytes).hexdigest(),committed=True,source_authenticity='UNKNOWN',point_in_time_availability='UNKNOWN',native_authority_verified=False)
    if self.mode=='missing':return None
    if self.mode=='false':result['committed']=False
    if self.mode=='nonliteral':result['committed']=1
    if self.mode=='mismatch':result['observation_sha256']='0'*64
    return result
  with patch.object(archive,'blob_snapshot',snapshot),patch.object(archive,'audit_trade_gzip',return_value=SimpleNamespace(valid=True,rows=1)),patch.object(archive,'parse_archive_events',side_effect=lambda *args:iter([event])):
   for mode in ('missing','false','nonliteral','mismatch'):
    wal=WAL();store=Store(mode);owner=archive.ArchiveImporter('.',store,wal,source_revision='a'*40)
    with self.assertRaises(ValueError):complete(owner.ingest('fixture.csv.gz','a'*64,1,'BTCUSDT'))
    self.assertEqual(wal.acks,[]);self.assertEqual(len(wal.pending),1);self.assertTrue(owner.failed)
    with self.assertRaises(ValueError):complete(owner.recover())
    self.assertEqual(store.calls,1)
    fresh=archive.ArchiveImporter('.',store,wal,source_revision='a'*40)
    with self.assertRaises(ValueError):complete(fresh.recover())
    self.assertEqual(len(wal.pending),1);self.assertEqual(wal.acks,[])
 def test_packet_closed_map_bounds_before_proportional_allocation(self):
  import tracemalloc
  from market_data.paper_inputs import validate_paper_inputs,ExportBlocked
  packet={str(i):None for i in range(100000)};tracemalloc.start()
  try:
   with self.assertRaises(ExportBlocked):validate_paper_inputs(packet)
   peak=tracemalloc.get_traced_memory()[1]
  finally:tracemalloc.stop()
  self.assertLess(peak,262144)

 def test_actual_root_execute_cli_refuses_before_prepare_or_process(self):
  import contextlib,io
  from unified_system import lab_runtime
  output=io.StringIO()
  with patch.object(lab_runtime,'prepare',side_effect=AssertionError('NO_PREPARE')),patch.object(lab_runtime,'run_runtime',side_effect=AssertionError('NO_RUNTIME')),contextlib.redirect_stdout(output):
   code=lab_runtime.main(['--mode','LAB_SIMULATION','--root','UNADMITTED_NOT_A_CAPSULE','--manifest-sha256','0'*64,'--execute'])
  self.assertEqual(code,1);self.assertIn('CANONICAL_STARTUP_ADMISSION_REQUIRED',output.getvalue())

if __name__=='__main__':unittest.main()
