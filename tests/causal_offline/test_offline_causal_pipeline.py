"""Mandatory actual SDK offline composition; explicit private synthetic fixtures.
Loaded by the causal installed/source runner, never a provider/native gate.
"""
import copy,hashlib,importlib.util,json,pathlib,tempfile,unittest
from decimal import Decimal
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[2]

def pipeline_type():
    path=ROOT/'unified_system/offline_causal_pipeline.py'
    if not path.is_file():raise AssertionError('canonical offline causal pipeline missing')
    from unified_system.offline_causal_pipeline import OfflineCausalPipeline
    return OfflineCausalPipeline

def policy():
    return dict(schema='terminan.paper.causal-account-policy.v2',mode='SYNTHETIC_OFFLINE',long_only=True,initial_cash_usdt='10000',notional_usdt='100',max_reserved_usdt='2000',max_positions=10,max_drawdown_fraction='0.5',max_quote_age_ms=1000,max_spread_bps='100',fee_bps='0',slippage_bps='0',latency_ms=10,entry_wait_ms=500,exit_wait_ms=500,hold_ms=100)

class GuardTests(unittest.TestCase):
    def test_canonical_math_exact_funding_units(self):
        pipeline_type()
        from market_math import exact_scaled_integer
        self.assertEqual(exact_scaled_integer(Decimal('0.125'),3600000),450000)
        self.assertEqual(exact_scaled_integer(Decimal('450000.0'),1),450000)
        with self.assertRaises(ValueError):exact_scaled_integer(Decimal('450000.1'),1)
    def test_freshness_refusal_precedes_factories_and_files(self):
        cls=pipeline_type()
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp)/'audit'
            for current in (lambda:False,lambda:1):
                with patch('unified_system.storage.object_store.ObjectStore.create',side_effect=AssertionError('NO_STORE_FACTORY')),patch('unified_system.journal.Journal.initialize',side_effect=AssertionError('NO_JOURNAL_FACTORY')),self.assertRaises(ValueError):
                    cls.create(root,account=SimpleNamespace(require_current=current),read_source=lambda q:None,clock_ms=lambda:4000,run_id='offline_1',strategy_revision='1'*40,planned_duration_ms=4000,source_max_age_ms=10000)
                self.assertFalse(root.exists())

from datetime import datetime,timezone,timedelta

def seal(value):
    from terminan.paper_ledger import canonical_json
    return dict(value,sha256=hashlib.sha256(canonical_json(value)).hexdigest())

def request(symbol,after,as_of):
    return dict(symbol=symbol,after_id=after,start_ms=0,end_ms=as_of+1,as_of_ms=as_of,max_age_ms=10000)

def stored(symbol,ident,kind,payload,event,ingest,connection='a'*32):
    data=copy.deepcopy(payload)
    if connection is not None:data['_producer_connection']=dict(schema='market_data.public-market-connection.v1',venue='bybit',category='linear',endpoint='wss://stream.bybit.com/v5/public/linear',connection_id=connection,scope='PRODUCER_DECLARED_LOCAL_CONNECTION_NOT_REMOTE_AUTHENTICATION')
    epoch=datetime(1970,1,1,tzinfo=timezone.utc)
    return dict(id=ident,symbol=symbol,source='bybit',event_type=kind,payload=data,event_ts=epoch+timedelta(milliseconds=event),ingest_ts=epoch+timedelta(milliseconds=ingest))

def book(symbol,ident,event,bid='99.9',ask='100',connection='a'*32):
    return stored(symbol,ident,'orderbook_snapshot',dict(best_bid=bid,best_ask=ask,sequence=ident,update_id=ident,cts=event,_quality={'symbol':symbol,'feeds':{'orderbook':{'status':'available'}}}),event,event+1,connection)

def funding(symbol,ident=6,*,known=True,interval='8',next_ms='28800000',event=4095):
    values=dict(funding_rate='0.0001',funding_interval_hour=interval,next_funding_time=next_ms)
    if known:values['_field_observations']=dict(schema='market_data.ticker-field-observations.v1',clock_basis='EXCHANGE_FRAME_TS_AND_PROCESS_WALL_CLOCK',fields={k:dict(event_ms=4090,observed_ms=4091,value_sha256=hashlib.sha256(json.dumps(v,separators=(',',':')).encode()).hexdigest()) for k,v in values.items()})
    return stored(symbol,ident,'derivatives_ticker',values,event,event+1)

def tape(symbol,prices,*,after=0,start=1000,large=False,connection='b'*32):
    rows=[]
    for i,price in enumerate(prices):
        stamp=start+i*250;buy=40 if large else 10
        data=dict(start_ms=stamp,open=price,high=price,low=price,close=price,buy_volume=buy,sell_volume=1,buy_count=buy,sell_count=1,trade_count=buy+1,delta=buy-1,cvd=buy-1,range=0,aggressor_imbalance='0.9512195121951219' if large else '0.8181818181818182')
        rows.append(stored(symbol,after+i+1,'trade_tape_250ms',data,stamp,stamp+251,connection))
    return rows

class Source:
    def __init__(self):self.rows=[];self.requests=[];self.failure=False;self.on_read=None
    def __call__(self,q):
        self.requests.append(copy.deepcopy(q))
        if self.failure:raise OSError('synthetic-unavailable')
        if self.on_read:self.on_read()
        from market_data.paper_inputs import export_paper_inputs
        return export_paper_inputs(self.rows,q)

class ComposedTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=pathlib.Path(self.tmp.name);self.clock=[4000];self.source=Source();self.p=policy();self.account=None;self.pipeline=None
    def create(self,*,planned=4000,p=None):
        from terminan.causal_account import CausalAccountJournal
        self.p=policy() if p is None else p
        self.account=CausalAccountJournal.create(self.root/'account',self.p,require_current=lambda:True)
        self.pipeline=pipeline_type().create(self.root/'audit',account=self.account,read_source=self.source,clock_ms=lambda:self.clock[0],run_id='offline_1',strategy_revision='1'*40,planned_duration_ms=planned,source_max_age_ms=10000,min_history=4)
        return self.pipeline
    def feed(self,rows,after,now,symbol='BTCUSDT',*,as_of=None):
        self.source.rows=rows;self.clock[0]=now
        return self.pipeline.poll(request(symbol,after,now if as_of is None else as_of))
    def warm(self,symbol='BTCUSDT'):
        self.feed(tape(symbol,['100','100.01','100.02','100.03']),0,4000,symbol)
    def opened(self,*,known=True,connection='b'*32):
        self.create();self.warm();self.feed([book('BTCUSDT',5,4090),funding('BTCUSDT',known=known)],4,4100)
        self.feed(tape('BTCUSDT',['101'],after=6,start=4000,large=True,connection=connection),6,4300)
    def close(self):
        self.feed([book('BTCUSDT',8,4310)],7,4320)
        self.feed([book('BTCUSDT',9,4410)],8,4420)
        self.feed([book('BTCUSDT',10,4430,'102','102.1')],9,4440)
    def test_ten_symbols_actual_sdk_store_journal_roundtrip(self):
        from terminan.causal_replay import SYMBOLS
        from terminan.causal_artifacts import validate_causal_ledger_artifact
        self.create();symbols=sorted(SYMBOLS)
        for symbol in symbols:self.warm(symbol)
        for symbol in symbols:self.feed([book(symbol,5,4090),funding(symbol)],4,4100,symbol)
        for symbol in symbols:self.feed(tape(symbol,['101'],after=6,start=4000,large=True),6,4300,symbol)
        for ident,event,now,bid,ask in [(8,4310,4320,'99.9','100'),(9,4410,4420,'99.9','100'),(10,4430,4440,'102','102.1')]:
            for symbol in symbols:self.feed([book(symbol,ident,event,bid,ask)],ident-1,now,symbol)
        receipt=self.pipeline.publish();raw=self.pipeline.read_publication(receipt);body=validate_causal_ledger_artifact(raw,expected_sha256=receipt['detail']['paper_sha256'])
        self.assertEqual(body['row_count'],10);self.assertEqual({r['symbol'] for r in body['rows']},set(symbols));self.assertEqual(Decimal(self.account.snapshot()['cash_usdt']),Decimal('10020'));self.assertEqual(self.account.snapshot()['reserved_usdt'],'0')
        self.assertIs(receipt['publication_confirmed'],False);self.assertEqual(receipt['native_commit'],'NOT_ATTEMPTED');self.assertEqual(body['point_in_time_availability'],'UNKNOWN')
    def test_unknown_funding_and_unavailable_context_never_fill(self):
        self.opened(known=False,connection=None);self.close();self.assertEqual(self.account.snapshot()['reserved_usdt'],'0');self.assertEqual(json.loads(self.pipeline.read_publication(self.pipeline.publish()))['row_count'],0)
    def test_processing_delay_preserves_declared_source_clocks(self):
        self.create();self.warm();self.source.on_read=lambda:self.clock.__setitem__(0,4300)
        self.feed([book('BTCUSDT',5,4090),funding('BTCUSDT')],4,4100);self.source.on_read=None
        raw=self.pipeline._store.read(self.pipeline.status()['last_source_packet_sha256']);value=json.loads(raw);self.assertEqual(value['request']['as_of_ms'],4100);self.assertEqual(value['rows'][1]['payload']['_field_observations']['fields']['next_funding_time']['observed_ms'],4091)
    def test_fractional_funding_units_reach_actual_session(self):
        self.create();self.warm();self.feed([book('BTCUSDT',5,4090),funding('BTCUSDT',interval=0.125,next_ms=450000.0)],4,4100);self.feed(tape('BTCUSDT',['101'],after=6,start=4000,large=True),6,4300)
        value=self.account.snapshot()['reservations'][0]['candidate']['funding'];self.assertEqual((value['interval_ms'],value['next_ms']),(450000,450000))
    def test_risk_delay_does_not_refresh_proposal_ttl(self):
        self.create();self.warm();self.feed([book('BTCUSDT',5,4090),funding('BTCUSDT')],4,4100);original=self.account.reserve
        def delayed(*a,**kw):
            result=original(*a,**kw);self.clock[0]+=501;return result
        with patch.object(self.account,'reserve',side_effect=delayed):self.feed(tape('BTCUSDT',['101'],after=6,start=4000,large=True),6,4300)
        r=self.account.snapshot()['reservations'][0];self.assertEqual(r['status'],'UNCERTAIN');self.assertEqual(r['candidate']['signal']['expires_ms'],4800);self.assertNotEqual(self.account.snapshot()['reserved_usdt'],'0')
    def test_reconnect_retains_uncertain_collateral(self):
        self.opened();self.feed([book('BTCUSDT',8,4310,connection='c'*32)],7,4320);r=self.account.snapshot()['reservations'][0];self.assertEqual((r['status'],r['uncertainty']),('UNCERTAIN','SOURCE_GAP'));self.assertNotEqual(self.account.snapshot()['reserved_usdt'],'0')
    def test_publication_uncertainty_blocks_without_retry_or_source_read(self):
        self.opened();self.close();original=self.pipeline._store.put;calls=[]
        def unknown(*a,**kw):
            calls.append(1);original(*a,**kw);raise OSError('COMMIT_ACK_UNKNOWN')
        with patch.object(self.pipeline._store,'put',side_effect=unknown),self.assertRaises(OSError):self.pipeline.publish()
        before={p.relative_to(self.root/'audit').as_posix():p.read_bytes() for p in (self.root/'audit').rglob('*') if p.is_file()};reads=len(self.source.requests)
        with self.assertRaises(ValueError):self.pipeline.publish()
        with self.assertRaises(ValueError):self.pipeline.poll({})
        self.assertEqual(len(calls),1);self.assertEqual(len(self.source.requests),reads);self.assertEqual(self.pipeline.status()['state'],'BLOCKED');self.assertEqual(before,{p.relative_to(self.root/'audit').as_posix():p.read_bytes() for p in (self.root/'audit').rglob('*') if p.is_file()})
    def test_capacity_refuses_before_audit_factories(self):
        from terminan.causal_account import CausalAccountJournal
        p=policy();p.update(hold_ms=1,latency_ms=1,entry_wait_ms=2,exit_wait_ms=2);account=CausalAccountJournal.create(self.root/'account',p,require_current=lambda:True)
        with patch('unified_system.storage.object_store.ObjectStore.create',side_effect=AssertionError('NO_STORE')),patch('unified_system.journal.Journal.initialize',side_effect=AssertionError('NO_JOURNAL')),self.assertRaises(ValueError):pipeline_type().create(self.root/'audit',account=account,read_source=self.source,clock_ms=lambda:4000,run_id='offline_1',strategy_revision='1'*40,planned_duration_ms=600000,source_max_age_ms=10000)
        self.assertFalse((self.root/'audit').exists())
    def test_early_quote_is_not_relabelled_as_entry(self):
        self.opened();self.feed([book('BTCUSDT',8,4305)],7,4310);self.assertEqual(self.account.snapshot()['reservations'][0]['status'],'DECIDED');self.feed([book('BTCUSDT',9,4310)],8,4320);self.assertEqual(self.account.snapshot()['reservations'][0]['entry_quote']['event_ms'],4310)
    def test_revocation_precedes_read_and_preserves_collateral(self):
        self.opened();before={p.name:p.read_bytes() for p in (self.root/'account').iterdir()};reads=len(self.source.requests);self.account.require_current=lambda:False
        with self.assertRaises(ValueError):self.pipeline.poll({})
        self.assertEqual(len(self.source.requests),reads);self.assertEqual(before,{p.name:p.read_bytes() for p in (self.root/'account').iterdir()});self.assertEqual(self.pipeline.status()['state'],'BLOCKED')
    def test_elapsed_window_does_not_read_source(self):
        self.create();self.clock[0]=8000;self.pipeline.poll({'unread':'x'*1000000});self.assertEqual(self.source.requests,[]);self.assertEqual(self.pipeline.status()['state'],'WINDOW_ENDED');self.assertFalse(self.pipeline.status()['execution_authority'])
    def test_provider_failure_preserves_cursor_and_later_request_cut(self):
        self.create();self.warm();self.source.failure=True;self.clock[0]=4050;self.pipeline.poll(request('BTCUSDT',4,4050));self.assertEqual(self.pipeline.status()['session']['instruments']['BTCUSDT']['cursor'],4)
        self.source.failure=False;self.feed([book('BTCUSDT',5,4090),funding('BTCUSDT')],4,4100);self.assertEqual(self.source.requests[-1]['as_of_ms'],4100);self.assertEqual(self.pipeline.status()['session']['instruments']['BTCUSDT']['cursor'],6)
    def test_foreign_financial_result_refuses_before_object_publication(self):
        from terminan.causal_replay import calculate_causal_receipt
        self.create();base=dict(symbol='BTCUSDT',source_id='synthetic',raw_sha256='a'*64)
        def r(ident,**kw):return seal(dict(base,receipt_id=ident,**kw))
        a=r('open',decision_ms=100,observed_ms=99,expires_ms=600,side='long');b=r('close',decision_ms=300,observed_ms=300,expires_ms=800);x=r('entry',epoch='e',sequence=1,event_ms=110,observed_ms=111,bid='99.9',ask='100');y=r('exit',epoch='e',sequence=2,event_ms=310,observed_ms=311,bid='102',ask='102.1');f=r('funding',kind='COMPLETE_INTERVAL',observed_ms=90,previous_ms=0,next_ms=2000,interval_ms=2000,events=[])
        q=dict(schema='terminan.paper.causal-quote.request.v2',request_id='foreign',strategy='causal_quote',strategy_revision='1'*40,evidence_class='SYNTHETIC',symbol='BTCUSDT',units=dict(price='USDT/BTC',qty='BTC'),policy=dict(notional='100',fee_bps='0',slippage_bps='0',latency_ms=10,max_quote_age_ms=1000,max_hold_ms=600),signal=a,close_signal=b,quotes=[x,y],funding=f)
        self.account._results.record(calculate_causal_receipt(q,now_ms=320))
        with patch.object(self.pipeline._store,'put',side_effect=AssertionError('NO_FINANCIAL_PUBLICATION')),self.assertRaises(ValueError):self.pipeline.publish()
        self.assertEqual(self.pipeline.status()['state'],'BLOCKED')
    def test_actual_artifact_store_to_term_reader_and_idempotent_readback(self):
        from terminan.causal_artifacts import validate_causal_ledger_artifact
        self.opened();self.close();receipt=self.pipeline.publish();raw=self.pipeline.read_publication(receipt);body=validate_causal_ledger_artifact(raw,expected_sha256=receipt['detail']['paper_sha256']);self.assertEqual(body['row_count'],1);self.assertEqual(Decimal(body['rows'][0]['metrics']['net']),Decimal(2));before=self.pipeline.status()['audit_sequence']
        with patch.object(self.account,'close_trade',side_effect=AssertionError('NO_TRADE_REEXECUTION')),patch.object(self.pipeline._session,'publication_artifact',side_effect=AssertionError('VERIFIED_SAME_INSTANCE_READBACK')):self.assertEqual(self.pipeline.publish(),receipt)
        self.assertEqual(self.pipeline.status()['audit_sequence'],before);self.assertEqual(self.pipeline.read_publication(receipt),raw)

class CustodyTests(unittest.TestCase):
    setUp=ComposedTests.setUp
    create=ComposedTests.create
    warm=ComposedTests.warm
    feed=ComposedTests.feed
    def test_audit_tamper_latches_and_restored_bytes_cannot_retry(self):
        self.create();before=self.pipeline.path.read_bytes();self.pipeline.path.write_bytes(before+b'corrupt');reads=len(self.source.requests)
        with self.assertRaises(ValueError):self.pipeline.poll(request('BTCUSDT',0,4000))
        self.assertEqual(self.pipeline.status()['state'],'BLOCKED')
        self.pipeline.path.write_bytes(before)
        with self.assertRaises(ValueError):self.pipeline.poll(request('BTCUSDT',0,4000))
        self.assertEqual(len(self.source.requests),reads)
    def test_source_object_and_audit_precede_actual_session_consumption(self):
        self.create();original=self.pipeline._session.accept_packet;seen=[]
        def consume(packet,**kwargs):
            raw=self.pipeline._canonical(packet);pin=hashlib.sha256(raw).hexdigest();self.assertEqual(self.pipeline._store.read(pin),raw)
            last=self.pipeline._audit.read()[-1]['receipt'];self.assertEqual(last['kind'],'SOURCE_PACKET_RETAINED');self.assertEqual(last['detail']['source_packet_sha256'],pin);seen.append(pin);return original(packet,**kwargs)
        with patch.object(self.pipeline._session,'accept_packet',side_effect=consume):self.warm()
        self.assertEqual(len(seen),1)
    def test_journal_commit_unknown_blocks_without_source_or_audit_retry(self):
        self.create();original=self.pipeline._audit.append;calls=[]
        def unknown(*a,**kw):
            calls.append(1);original(*a,**kw);raise OSError('AUDIT_COMMIT_ACK_UNKNOWN')
        with patch.object(self.pipeline._audit,'append',side_effect=unknown),self.assertRaises(OSError):self.warm()
        self.assertEqual(self.pipeline.status()['state'],'BLOCKED');reads=len(self.source.requests)
        with self.assertRaises(ValueError):self.pipeline.poll({})
        self.assertEqual(len(calls),1);self.assertEqual(len(self.source.requests),reads);self.assertGreater(len(list((self.root/'audit/store/objects').iterdir())),0)

    def test_unretained_source_descriptor_cannot_become_root_evidence(self):
        from terminan.causal_session import SessionDescriptor
        self.create();value=dict(schema='terminan.paper.session-event.v2',sequence=1,kind='SOURCE_PACKET_OBSERVED',run_id='offline_1',symbol='BTCUSDT',reservation_id=None,at_ms=4000,detail=dict(cursor=4,source_request_sha256='a'*64),source_packet_sha256='f'*64,evidence_class='SYNTHETIC',source_authenticity='NOT_EVALUATED',point_in_time_availability='UNKNOWN',execution_authority=False,trading_authorized=False)
        from terminan.paper_ledger import canonical_json
        raw=canonical_json(value);event=SessionDescriptor(raw,hashlib.sha256(raw).hexdigest())
        with patch.object(self.pipeline._session,'accept_packet',return_value=(event,)),self.assertRaises(ValueError):self.warm()
        self.assertEqual(self.pipeline.status()['state'],'BLOCKED')

    def test_forged_receipt_equality_cannot_rebind_an_artifact_read(self):
        self.create();receipt=self.pipeline.publish();descriptor_sha=receipt['detail']['descriptor_sha256']
        class Forged:
            def __eq__(self,other):return True
            def __getitem__(self,key):return {'paper_sha256':descriptor_sha}
        with self.assertRaises(ValueError):self.pipeline.read_publication(Forged())
        self.assertEqual(self.pipeline.read_publication(receipt),self.pipeline._store.read(receipt['detail']['paper_sha256']))
