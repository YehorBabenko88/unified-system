"""Explicit cross-repository synthetic causal composition; no physical/live claim."""
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

from unified_system.lab_paper_pipeline import PaperPipeline, PipelineBlocked, SYMBOLS, _int_numeric


def policy():
    return dict(schema='stratt.paper.account-policy.v1',mode='LAB_SIMULATION',long_only=True,
        initial_cash_usdt=10000.,notional_usdt=100.,max_reserved_usdt=2000.,max_positions=10,
        max_drawdown_fraction=.5,max_quote_age_ms=1000,max_spread_bps=100.,fee_bps=10.,
        slippage_bps=10.,latency_ms=10,entry_wait_ms=500,exit_wait_ms=500,hold_ms=100)


class Admission:
    live=True
    def require_current(self):return self.live
    def full_admission(self):
        return dict(schema='unified.lab.paper-sources.v1',run_id='synthetic',evidence_class='SYNTHETIC',
                    network_scope='EXISTING_GRID_READ_ONLY',order_mode='PAPER_ONLY',symbols=list(SYMBOLS),
                    sources={name:'a'*40 for name in ('unified-system','bybit-cluster-grid','strattester','Terminan')})


class GuardTests(unittest.TestCase):
    def test_numeric_funding_representation_is_exact_without_rounding_milliseconds(self):
        self.assertEqual(_int_numeric(8.0,scale=3600000),28800000)
        self.assertEqual(_int_numeric('8.0',scale=3600000),28800000)
        self.assertEqual(_int_numeric('0.5',scale=3600000),1800000)
        self.assertEqual(_int_numeric(0.25,scale=3600000),900000)
        for value,scale in ((True,1),(1.1,1),('0.0000001',3600000),('nan',1),('1e999999',1)):
            with self.subTest(value=value),self.assertRaises(PipelineBlocked):_int_numeric(value,scale=scale)

    def test_missing_kernel_source_admission_precedes_all_factories_and_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'no-effects'
            with self.assertRaises(PipelineBlocked):
                PaperPipeline.create(root,account=object(),read_source=lambda _:None,writer=object(),
                    admission=None,run_id='synthetic',source_max_age_ms=10000,planned_duration_ms=10000)
            self.assertFalse(root.exists())


class ComposedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        grid=os.environ.get('PAPER_TEST_GRID_ROOT');stratt=os.environ.get('PAPER_TEST_STRATT_ROOT')
        if not grid or not stratt:raise unittest.SkipTest('explicit Grid/Stratt source checkouts absent; composed runtime NOT_RUN')
        sys.path[:0]=[stratt,grid]
        from strattester.research.paper_account import PaperAccount
        from grid.lab_observation_export import export_paper_inputs
        cls.PaperAccount=PaperAccount;cls.export=staticmethod(export_paper_inputs)

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve()
        self.clock=[3000];self.admission=Admission();self.admission.live=True
        self.account=self.PaperAccount.create(self.root/'account',policy(),require_current=self.admission.require_current)
        self.source_rows={symbol:[] for symbol in SYMBOLS};self.requests=[]
        self.writer=type('Writer',(),{'publish':lambda owner,**kw:{'sequence':kw['expected_sequence']+1}})()

    def source(self,request):
        self.requests.append(copy.deepcopy(request))
        rows=[r for r in self.source_rows[request['symbol']] if r['id']>request['after_id']]
        return self.export(rows,request)

    def create(self,**kwargs):
        return PaperPipeline.create(self.root/'pipeline',account=self.account,read_source=self.source,writer=self.writer,
            admission=self.admission,run_id='synthetic',source_max_age_ms=10000,planned_duration_ms=10000,
            clock_ms=lambda:self.clock[0],**kwargs)

    def context(self,connection):
        return dict(schema='grid.public-market-connection.v1',venue='bybit',category='linear',
            endpoint='wss://stream.bybit.com/v5/public/linear',connection_id=connection,
            scope='PRODUCER_DECLARED_LOCAL_CONNECTION_NOT_REMOTE_AUTHENTICATION')

    def row(self,symbol,ident,kind,event,ingest,payload):
        from datetime import datetime,timezone,timedelta
        stamp=lambda ms:datetime(1970,1,1,tzinfo=timezone.utc)+timedelta(milliseconds=ms)
        return dict(id=ident,symbol=symbol,event_type=kind,source='bybit',event_ts=stamp(event),ingest_ts=stamp(ingest),payload=payload)

    def seed(self,symbol,index=0):
        rows=[];offset=index*100;book_context=self.context('a'*32);tape_context=self.context(f'{index+1:032x}')
        for step in range(1,9):
            close=100+step/10
            payload=dict(start_ms=step*250,open=close,high=close,low=close,close=close,buy_volume=.6,sell_volume=.4,
                         buy_count=1,sell_count=1,trade_count=2,delta=.2,cvd=.2*step,range=0.,aggressor_imbalance=.2,
                         _producer_connection=tape_context)
            rows.append(self.row(symbol,offset+step,'trade_tape_250ms',step*250,step*250+250,payload))
        rows.append(self.row(symbol,offset+9,'orderbook_snapshot',2990,2991,
            dict(best_bid='101.9',best_ask='102.0',sequence=10,update_id=10,cts=2990,
                 _quality={'symbol':symbol,'feeds':{'orderbook':{'status':'available'}}},_producer_connection=book_context)))
        funding=dict(funding_rate='0.0001',funding_interval_hour='1',next_funding_time='3600000')
        digest=lambda v:hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()).hexdigest()
        funding['_field_observations']=dict(schema='grid.ticker-field-observations.v1',clock_basis='EXCHANGE_FRAME_TS_AND_PROCESS_WALL_CLOCK',
            fields={key:dict(event_ms=2990,observed_ms=2990,value_sha256=digest(value)) for key,value in funding.items()})
        funding['_producer_connection']=book_context
        rows.append(self.row(symbol,offset+10,'derivatives_ticker',2990,2991,funding))
        rows.append(self.row(symbol,offset+11,'trade_tape_250ms',2750,3000,
            dict(start_ms=2750,open=102.,high=102.,low=102.,close=102.,buy_volume=2.,sell_volume=0.,buy_count=1,sell_count=0,
                trade_count=1,delta=2.,cvd=3.6,range=0.,aggressor_imbalance=1.,_producer_connection=tape_context)))
        self.source_rows[symbol]=rows

    def book(self,symbol,ident,event,ingest,sequence,bid,ask,connection='a'*32):
        self.source_rows[symbol].append(self.row(symbol,ident,'orderbook_snapshot',event,ingest,
            dict(best_bid=str(bid),best_ask=str(ask),sequence=sequence,update_id=sequence,cts=event,
                 _quality={'symbol':symbol,'feeds':{'orderbook':{'status':'available'}}},_producer_connection=self.context(connection))))

    def test_ten_actual_strategy_risk_later_quotes_native_ledger_and_writer(self):
        for index,symbol in enumerate(SYMBOLS):self.seed(symbol,index)
        pipeline=self.create();pipeline.poll()
        view=self.account.snapshot()
        self.assertEqual(len([r for r in view['reservations'] if r['status']=='DECIDED']),10)
        self.assertEqual(view['closed_count'],0)
        # The already fetched reference book cannot become a later fill.
        self.assertTrue(all(r['entry_quote'] is None for r in view['reservations']))
        self.clock[0]=3011
        for index,symbol in enumerate(SYMBOLS):self.book(symbol,index*100+12,3010,3011,20,102.,102.1)
        pipeline.poll();self.assertEqual(len(self.account.snapshot()['open_positions']),10)
        self.clock[0]=3111;pipeline.poll() # Durable close decision, no fabricated exit fill.
        self.assertEqual(self.account.snapshot()['closed_count'],0)
        self.clock[0]=3122
        for index,symbol in enumerate(SYMBOLS):self.book(symbol,index*100+13,3121,3122,30,103.,103.1)
        pipeline.poll();self.assertEqual(self.account.snapshot()['closed_count'],10)
        native=self.account.verified_paper_snapshot();self.assertTrue(all(r['result']['paper_eligible']=='NOT_QUALIFIED' for r in native['rows']))
        self.assertEqual(pipeline.publish()['sequence'],1)
        kinds=[row['receipt']['kind'] for row in pipeline.audit.read()]
        self.assertEqual(kinds.count('RISK_DECISION'),10);self.assertEqual(kinds.count('ENTRY_DECISION'),10)
        self.assertEqual(kinds.count('ENTRY_SELECTED'),10);self.assertEqual(kinds.count('EXIT_DECISION'),10)
        self.assertEqual(kinds.count('LEDGER_COMMITTED'),10)
        self.assertEqual({r['symbol'] for r in self.requests},set(SYMBOLS))

    def test_unknown_funding_and_legacy_context_never_create_paper_fill(self):
        self.seed(SYMBOLS[0]);self.source_rows[SYMBOLS[0]][9]['payload'].pop('_field_observations')
        pipeline=self.create();pipeline.poll()
        self.assertEqual(self.account.snapshot()['closed_count'],0)
        self.assertTrue(all(not r['risk_receipt']['accepted'] for r in self.account.snapshot()['reservations']))

    def test_funding_survives_actual_processing_delay_without_relabelling_selection(self):
        for delay in (1,17):
            with self.subTest(delay=delay):
                if delay!=1:
                    # Independent owned run/state for each temporal variant.
                    self.root=self.root/'later';self.root.mkdir();self.clock[0]=3000
                    self.account=self.PaperAccount.create(self.root/'account',policy(),require_current=self.admission.require_current)
                    self.source_rows={symbol:[] for symbol in SYMBOLS};self.requests=[]
                symbol=SYMBOLS[0];self.seed(symbol);actual=self.source
                def delayed(request):
                    result=actual(request);self.clock[0]+=delay;return result
                pipeline=self.create();pipeline.read_source=delayed;pipeline.poll()
                record=self.account.snapshot()['reservations'][0]
                self.assertTrue(record['risk_receipt']['accepted'])
                self.assertEqual(record['status'],'DECIDED')
                packet,_=pipeline.state[symbol]['funding']
                self.assertEqual(packet['request']['as_of_ms'],3000)
                self.assertEqual(packet['availability']['as_of_ms'],3000)
                self.assertIsNotNone(pipeline._funding(symbol,self.clock[0]))
                self.assertIsNone(pipeline._funding(symbol,15000)) # Old source clocks remain old.

    def test_fractional_hour_and_integral_float_funding_values_keep_exact_units(self):
        symbol=SYMBOLS[0];self.seed(symbol)
        payload=self.source_rows[symbol][9]['payload']
        payload.update(funding_interval_hour='0.5',next_funding_time=1800000.0)
        for name,proof in payload['_field_observations']['fields'].items():
            proof['value_sha256']=hashlib.sha256(json.dumps(payload[name],sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()).hexdigest()
        pipeline=self.create();pipeline.poll();record=self.account.snapshot()['reservations'][0]
        self.assertTrue(record['risk_receipt']['accepted'])
        self.assertEqual(record['funding']['interval_ms'],1800000)
        self.assertEqual(record['funding']['next_ms'],1800000)

    def test_risk_processing_cannot_refresh_expired_strategy_window(self):
        symbol=SYMBOLS[0];self.seed(symbol,0)
        original=self.account.reserve
        def delayed(*args,**kwargs):
            receipt=original(*args,**kwargs)
            self.clock[0]+=501
            return receipt
        self.account.reserve=delayed
        pipeline=self.create();pipeline.poll()
        record=self.account.snapshot()['reservations'][0]
        self.assertEqual(record['status'],'UNCERTAIN')
        self.assertIsNone(record['decision'])
        self.assertEqual(record['uncertainty'],'QUOTE_TIMEOUT')
        self.assertGreater(self.account.snapshot()['reserved_usdt'],0)

    def test_reconnect_retains_uncertain_collateral_and_never_reuses_old_book(self):
        symbol=SYMBOLS[0];self.seed(symbol);pipeline=self.create();pipeline.poll()
        self.clock[0]=3011;self.book(symbol,12,3010,3011,20,102.,102.1,connection='b'*32)
        pipeline.poll();view=self.account.snapshot()
        self.assertEqual(view['reservations'][0]['status'],'UNCERTAIN')
        self.assertGreater(view['reserved_usdt'],0);self.assertEqual(view['closed_count'],0)

    def test_publication_failure_stops_without_retry_or_new_source_io(self):
        from unified_system.lab_observation_writer import ObservationRejected
        calls=[]
        def fail(**kwargs):calls.append(kwargs);raise ObservationRejected('OBSERVATION_REJECTED')
        self.writer.publish=fail;pipeline=self.create()
        with self.assertRaises(PipelineBlocked):pipeline.publish()
        before=len(self.requests)
        with self.assertRaises(PipelineBlocked):pipeline.publish()
        with self.assertRaises(PipelineBlocked):pipeline.poll()
        self.assertEqual(len(calls),1);self.assertEqual(len(self.requests),before)

    def test_tiny_hold_budget_rejects_ten_minute_plan_before_audit_creation(self):
        with self.assertRaises(PipelineBlocked):
            PaperPipeline.create(self.root/'no-audit',account=self.account,read_source=self.source,writer=self.writer,
                admission=self.admission,run_id='synthetic',source_max_age_ms=10000,planned_duration_ms=600000,
                clock_ms=lambda:self.clock[0])
        self.assertFalse((self.root/'no-audit').exists())

    def test_first_new_quote_before_latency_is_not_relabelled_as_a_fill(self):
        symbol=SYMBOLS[0];self.seed(symbol);pipeline=self.create();pipeline.poll()
        self.clock[0]=3006;self.book(symbol,12,3005,3006,20,102.,102.1);pipeline.poll()
        self.assertEqual(self.account.snapshot()['open_positions'],[])
        self.clock[0]=3011;self.book(symbol,13,3010,3011,30,102.,102.1);pipeline.poll()
        entry=self.account.snapshot()['open_positions'][0]['entry_quote']
        self.assertEqual(entry['event_ms'],3010);self.assertEqual(entry['sequence'],13)

    def test_revocation_stops_before_another_source_read_and_preserves_cash_reservation(self):
        symbol=SYMBOLS[0];self.seed(symbol);pipeline=self.create();pipeline.poll()
        before=len(self.requests);self.admission.live=False
        with self.assertRaises(PipelineBlocked):pipeline.poll()
        self.assertEqual(len(self.requests),before)
        import sqlite3
        from contextlib import closing
        with closing(sqlite3.connect(self.account.account_path)) as connection:
            records=[json.loads(r[0]) for r in connection.execute('SELECT body FROM reservations')]
        self.assertTrue(any(r['status']=='DECIDED' and float(r['collateral'])>0 for r in records))

    def test_elapsed_window_stops_reads_without_claiming_qualification(self):
        pipeline=self.create();pipeline.poll();before=len(self.requests)
        self.clock[0]=13000;result=pipeline.poll()
        self.assertEqual(result['state'],'WINDOW_ENDED');self.assertEqual(result['qualification'],'NOT_EVALUATED')
        self.assertEqual(len(self.requests),before)
        pipeline.poll();self.assertEqual(len(self.requests),before)

    def test_provider_failure_holds_cursor_then_normal_poll_uses_real_later_asof(self):
        symbol=SYMBOLS[0];self.seed(symbol);read=self.source;failed=[False]
        def unavailable(request):
            if request['symbol']==symbol and not failed[0]:failed[0]=True;raise ValueError('PRIVATE_SOURCE_ERROR')
            return read(request)
        pipeline=self.create();pipeline.read_source=unavailable;pipeline.poll()
        self.assertEqual(pipeline.status()['instruments'][symbol]['cursor'],0)
        self.clock[0]=3001;pipeline.poll()
        self.assertEqual(pipeline.status()['instruments'][symbol]['cursor'],11)
        self.assertEqual(self.account.snapshot()['closed_count'],0)
        self.assertNotIn('PRIVATE',json.dumps(pipeline.status()))

    def test_foreign_native_ledger_trade_stops_before_writer_callback(self):
        from strattester.research.quote_paper import PaperLedger
        from tests.test_quote_paper import fixture
        value=fixture();PaperLedger(self.account.ledger_path).append(value,now_ms=1300)
        calls=[];self.writer.publish=lambda **kwargs:calls.append(kwargs)
        # Account corruption must also prevent constructing a new pipeline.
        with self.assertRaises(PipelineBlocked):self.create()
        self.assertEqual(calls,[])

    def test_actual_native_result_reaches_existing_writer_and_pinned_term_reader(self):
        term_root=os.environ.get('PAPER_TEST_TERMINAN_ROOT');pin=os.environ.get('PAPER_TEST_TERMINAN_LAB_SHA256')
        if not term_root or not pin:self.skipTest('explicit pinned Term source absent; view integration NOT_RUN')
        import types
        from unified_system.lab_observation_writer import SnapshotWriter
        path=Path(term_root)/'terminan/lab_view.py';raw=path.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),pin)
        term=types.ModuleType('_pinned_pipeline_view');exec(compile(raw,str(path),'exec'),term.__dict__)
        viewer=SnapshotWriter.create(self.root/'viewer',release_id='synthetic',run_id='synthetic',
            validate=term.validate_v2,require_current=self.admission.require_current);self.addCleanup(viewer.close)
        self.writer=viewer;symbol=SYMBOLS[0];self.seed(symbol);pipeline=self.create();pipeline.poll()
        self.clock[0]=3011;self.book(symbol,12,3010,3011,20,102.,102.1);pipeline.poll()
        self.clock[0]=3111;pipeline.poll()
        self.clock[0]=3122;self.book(symbol,13,3121,3122,30,103.,103.1);pipeline.poll()
        result=pipeline.publish();decoded,_=term.read_snapshot(str(viewer.path),limit=2097152)
        self.assertEqual(decoded,result);self.assertEqual(decoded['sections']['paper']['payload']['returned_count'],1)
        self.assertEqual(decoded['sections']['paper']['payload']['rows'][0]['result']['paper_eligible'],'NOT_QUALIFIED')
        self.assertEqual(decoded['sections']['market']['state'],'UNAVAILABLE')


if __name__=='__main__':unittest.main()
