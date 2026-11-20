"""Causal paper composition over existing Grid strategy and native Stratt ledger.

No CLI, credentials, URL/SQL selectors, replacement strategy, simulator or queue.
An already admitted protected runtime supplies read-only Grid I/O and a live
kernel/source gate. Python callbacks are not self-authenticating grants. Their
production construction and the source/owner phase remain caller obligations.

Only NEW observed book samples after durable risk-bound decisions may be used.
Producer-declared local connection IDs are not remote/exchange authentication.
All source, execution and financial qualification limits remain unchanged.
"""
import copy
from collections import deque
from contextlib import closing
from decimal import Decimal, localcontext
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import threading
import time

SYMBOLS=tuple(name+'USDT' for name in ('BTC','ETH','SOL','XRP','BNB','DOGE','ADA','AVAX','LINK','DOT'))
MAX_AUDIT_EVENTS=4096
MAX_AUDIT_BYTES=64*1024*1024
MAX_EVENT_BYTES=65536
MAX_PACKET_BYTES=2*1024*1024
CODES=frozenset(('PIPELINE_ADMISSION_REQUIRED','PIPELINE_ADMISSION_REVOKED','PIPELINE_SOURCE_REJECTED',
    'PIPELINE_INPUT_REJECTED','PIPELINE_CLOCK_REJECTED','PIPELINE_RECOVERY_REQUIRED','PIPELINE_CAPACITY',
    'PIPELINE_AUDIT_REJECTED','PIPELINE_PUBLICATION_REJECTED','PIPELINE_STOPPED','PIPELINE_ACCOUNT_REJECTED'))


class PipelineBlocked(ValueError):
    def __init__(self, code='PIPELINE_INPUT_REJECTED'):
        self.code=code if code in CODES else 'PIPELINE_INPUT_REJECTED';super().__init__(self.code)


def need(condition, code='PIPELINE_INPUT_REJECTED'):
    if not condition:raise PipelineBlocked(code)


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def digest(value):return hashlib.sha256(canonical(value)).hexdigest()


def label(value):
    need(type(value) is str and re.fullmatch('[A-Za-z0-9_-]{1,32}',value) and 'ADMINIT' not in value.upper())
    return value


def _clock(value):
    need(type(value) is int and 0<value<2**53,'PIPELINE_CLOCK_REJECTED');return value


def _int_numeric(value, *, scale=1):
    need(type(value) in (int,float,str) and type(scale) is int and 0<scale<=86400000)
    text=str(value)
    need(len(text)<=128 and re.fullmatch(r'-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?',text) is not None)
    with localcontext() as context:
        context.prec=160
        parsed=Decimal(text)*scale
        need(parsed.is_finite() and 0<parsed<2**53 and parsed==parsed.to_integral_value())
        return int(parsed)

def _seal(value):
    result=copy.deepcopy(value);result['sha256']=digest(result);return result


class PaperPipeline:
    @classmethod
    def create(cls, audit_root, *, account, read_source, writer, admission, run_id,
               source_max_age_ms, planned_duration_ms, clock_ms=None,
               market_snapshot=None, fleet_snapshot=None):
        result=cls();result._blocked=None
        try:
            need(admission is not None and not isinstance(admission,dict)
                 and callable(getattr(admission,'require_current',None))
                 and callable(getattr(admission,'full_admission',None)),'PIPELINE_ADMISSION_REQUIRED')
            need(admission.require_current() is True,'PIPELINE_ADMISSION_REVOKED')
            sources=copy.deepcopy(admission.full_admission())
            need(type(sources) is dict and set(sources)=={'schema','run_id','evidence_class','network_scope','order_mode','symbols','sources'}
                 and sources['schema']=='unified.lab.paper-sources.v1'
                 and sources['network_scope']=='EXISTING_GRID_READ_ONLY' and sources['order_mode']=='PAPER_ONLY'
                 and sources['evidence_class'] in ('SYNTHETIC','HISTORICAL','LIVE')
                 and sources['symbols']==list(SYMBOLS) and sources['run_id']==label(run_id),'PIPELINE_SOURCE_REJECTED')
            need(type(sources['sources']) is dict and set(sources['sources'])=={'unified-system','bybit-cluster-grid','strattester','Terminan'}
                 and all(type(pin) is str and re.fullmatch('[a-f0-9]{40}',pin) for pin in sources['sources'].values()),'PIPELINE_SOURCE_REJECTED')
            need(admission.require_current() is True,'PIPELINE_ADMISSION_REVOKED')
            # All application imports follow the central kernel/capsule/source
            # callback. Source verification is reused there, never copied here.
            from grid.book_tape_research import BookTapeResearch
            from grid.lab_observation_export import validate_paper_inputs, paper_funding_at
            from strattester.research.paper_account import PaperAccount,MAX_CLOSED,MAX_DECISIONS
            from .journal import Journal
            from .installation_progress import safe
            from .owned_python import reject_external_namespace
            need(type(account) is PaperAccount and callable(read_source) and callable(getattr(writer,'publish',None)))
            need(type(source_max_age_ms) is int and account.policy['max_quote_age_ms']<=source_max_age_ms<=3600000)
            need(type(planned_duration_ms) is int and 1<=planned_duration_ms<=3600000)
            view=account.snapshot()
            need(not any(r['status'] not in ('DENIED','SETTLED') for r in view['reservations']),'PIPELINE_RECOVERY_REQUIRED')
            cooldown=account.policy['hold_ms']+account.policy['entry_wait_ms']+account.policy['exit_wait_ms']
            forecast=(planned_duration_ms//cooldown+1)*len(SYMBOLS)
            need(view['closed_count']+forecast<=MAX_CLOSED and len(view['reservations'])+forecast<=MAX_DECISIONS
                 and forecast*7+1<=MAX_AUDIT_EVENTS,'PIPELINE_CAPACITY')
            result.admission=admission;result.sources=sources;result.account=account;result.read_source=read_source
            result.writer=writer;result.run_id=run_id;result.source_max_age_ms=source_max_age_ms
            result.planned_duration_ms=planned_duration_ms;result.forecast=forecast;result.cooldown=cooldown
            result.clock_ms=(lambda:int(time.time()*1000)) if clock_ms is None else clock_ms
            need(callable(result.clock_ms));result._last_clock=0;result.started_ms=result._now()
            result.market_snapshot=market_snapshot;result.fleet_snapshot=fleet_snapshot
            need(all(value is None or callable(value) for value in (market_snapshot,fleet_snapshot)))
            result._validate_packet=validate_paper_inputs;result._funding_at=paper_funding_at;result._strategy_type=BookTapeResearch
            result._lock=threading.RLock();result._publication_sequence=0;result._audit_sequence=0
            result._pending={};result._ended=False;result._initial_closed_count=view['closed_count']
            result.state={symbol:dict(cursor=0,received=0,last_book=None,book_context=None,tape_context=None,
                funding=None,prefix=deque(maxlen=32),strategy=BookTapeResearch(),last_candidate=None,
                last_event={},issue=None,candidates=0,denied=0,closed=0,last_book_row=None,
                first_book_ingest_ms=None,last_book_ingest_ms=None,max_book_gap_ms=0) for symbol in SYMBOLS}
            result.root=Path(audit_root);need(result.root.is_absolute() and '..' not in result.root.parts)
            # Reuse the existing local-file guard, without an existing-path
            # adoption fallback. The namespace belongs to this one producer run.
            reject_external_namespace(str(result.root));safe(result.root,exists=False)
            need(not result.root.exists() and not result.root.is_symlink(),'PIPELINE_AUDIT_REJECTED')
            result._current();result.root.mkdir(mode=0o700,exist_ok=False)
            result.path=result.root/'audit.sqlite';fd=os.open(result.path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
            result._safe=safe;result._root_identity=result._identity(result.root)
            result._audit_identity=result._identity(result.path);result.audit=Journal(result.path);result.audit.initialize()
            result._audit('STARTED',None,None,result.started_ms,dict(source_pins=sources,capacity_forecast=forecast,
                scope='CAUSAL_PAPER_RESEARCH_ONLY',physical='NOT_RUN',source_authenticity='NOT_EVALUATED'))
            return result
        except PipelineBlocked:raise
        except Exception:raise PipelineBlocked('PIPELINE_SOURCE_REJECTED') from None

    @staticmethod
    def _identity(path):
        info=path.lstat();return info.st_dev,info.st_ino

    def _current(self):
        need(self._blocked is None,self._blocked or 'PIPELINE_STOPPED')
        try:valid=self.admission.require_current() is True
        except Exception:valid=False
        if not valid:self._blocked='PIPELINE_ADMISSION_REVOKED'
        need(valid,'PIPELINE_ADMISSION_REVOKED')

    def _now(self):
        now=_clock(self.clock_ms());need(now>=self._last_clock,'PIPELINE_CLOCK_REJECTED');self._last_clock=now;return now

    def _audit(self,kind,symbol,reservation_id,at_ms,detail):
        self._current();self._safe(self.path)
        need(self._identity(self.root)==self._root_identity and self._identity(self.path)==self._audit_identity,'PIPELINE_AUDIT_REJECTED')
        need(self.path.stat().st_size<=MAX_AUDIT_BYTES,'PIPELINE_CAPACITY')
        with closing(sqlite3.connect(self.path.resolve().as_uri()+'?mode=ro',uri=True)) as connection:
            count=connection.execute('SELECT count(*) FROM transitions').fetchone()[0]
        need(count==self._audit_sequence and count<MAX_AUDIT_EVENTS,'PIPELINE_AUDIT_REJECTED')
        record=dict(schema='unified.lab.paper-event.v1',kind=kind,run_id=self.run_id,symbol=symbol,
            reservation_id=reservation_id,at_ms=at_ms,detail=detail,execution_authority=False,trading_authorized=False)
        need(len(canonical(record))<=MAX_EVENT_BYTES,'PIPELINE_CAPACITY')
        self.audit.append('OBSERVING',record,expected_sequence=count);self._audit_sequence+=1

    def _records(self):
        # Non-authoritative routing cache only. Every mutation below calls the
        # account's fresh full native/journal validation and BEGIN IMMEDIATE.
        # This cache never decides spendable cash, releases or publication truth.
        return copy.deepcopy(self._pending)

    def _uncertain(self,symbol,reason,now):
        record=self._records().get(symbol)
        if record is not None and record['status']!='UNCERTAIN':
            self.account.mark_uncertain(record['id'],reason,now_ms=now)
            record.update(status='UNCERTAIN',uncertainty=reason);self._pending[symbol]=record
            self._audit('UNCERTAIN',symbol,record['id'],now,dict(reason=reason))

    def _advance(self,now):
        self._current()
        for symbol,record in self._records().items():
            if record['status']=='UNCERTAIN':continue
            book=self.state[symbol]['last_book']
            if book is None or now-book['observed_ms']>self.account.policy['max_quote_age_ms']:
                self._uncertain(symbol,'SOURCE_GAP',now);continue
            if record['status'] in ('RESERVED','DECIDED'):
                expires=(record['decision'] or record['signal'])['expires_ms']
                if now>expires:self._uncertain(symbol,'QUOTE_TIMEOUT',now)
            elif record['status']=='ENTRY_SELECTED':
                entry=record['entry_quote'];due=entry['observed_ms']+self.account.policy['hold_ms']
                if now>entry['event_ms']+self.account.execution_policy['max_hold_ms']:
                    self._uncertain(symbol,'QUOTE_TIMEOUT',now);continue
                if now>=due:
                    decision=_seal(dict(receipt_id=record['id']+'_close',symbol=symbol,source_id='STRATT_PAPER_CLOSE_DECISION',
                        raw_sha256=digest(dict(schema='stratt.paper.close-decision-input.v1',opening_decision_sha256=record['decision']['sha256'],
                            entry_quote_sha256=entry['sha256'],risk_sha256=digest(record['risk_receipt']),hold_ms=self.account.policy['hold_ms'])),
                        decision_ms=now,observed_ms=now,expires_ms=now+self.account.policy['exit_wait_ms']))
                    updated=self.account.record_exit_decision(record['id'],decision,now_ms=now);self._pending[symbol]=updated
                    self._audit('EXIT_DECISION',symbol,record['id'],now,dict(decision=decision))
            elif record['status']=='EXIT_DECIDED' and now>record['close_decision']['expires_ms']:
                self._uncertain(symbol,'QUOTE_TIMEOUT',now)

    def _context(self,symbol,row,now):
        state=self.state[symbol];kind=row['event_type'];context=row['payload'].get('_producer_connection')
        if context is None:
            state['issue']='PRODUCER_CONTEXT_UNAVAILABLE';self._uncertain(symbol,'SOURCE_GAP',now);return None
        # Endpoint/category/schema consistency belongs to Grid's existing packet
        # validator. These are producer-declared local connection IDs only.
        channel='tape_context' if kind=='trade_tape_250ms' else 'book_context'
        connection=context['connection_id']
        previous=state[channel]
        if previous is not None and previous!=connection:
            self._uncertain(symbol,'SOURCE_GAP',now);state['last_book']=None;state['funding']=None
            if channel=='tape_context':state['strategy']=self._strategy_type();state['prefix'].clear()
            state['issue']='LOCAL_CONNECTION_CHANGED'
        state[channel]=connection;return connection

    def _funding(self,symbol,now):
        saved=self.state[symbol]['funding']
        if saved is None:return None
        packet,row=saved
        try:
            assessment=self._funding_at(packet,row_id=row['id'],now_ms=now)
            need(assessment==dict(funding_status='KNOWN_SOURCE_FIELDS',evaluated_at_ms=now,
                source_request_sha256=digest(packet['request']),row_sha256=row['row_sha256']))
            need(row['payload']['_producer_connection']['connection_id']==self.state[symbol]['book_context'])
            payload=row['payload'];interval=_int_numeric(payload['funding_interval_hour'],scale=3600000)
            next_ms=_int_numeric(payload['next_funding_time']);need(next_ms>=interval and interval<=86400000)
            observed=max((proof['observed_ms'] for proof in payload['_field_observations']['fields'].values()),default=0)
            observed=max(observed,(row['ingest_us']+999)//1000)
            return _seal(dict(receipt_id=f'f_{self.run_id}_{symbol}_{row["id"]}',symbol=symbol,source_id='GRID_PERSISTED_FUNDING_FIELDS',
                raw_sha256=row['row_sha256'],kind='COMPLETE_INTERVAL',observed_ms=observed,
                previous_ms=next_ms-interval,next_ms=next_ms,interval_ms=interval,events=[]))
        except Exception:return None

    def _proposal(self,symbol,row,observed,answer,history,now):
        state=self.state[symbol]
        if answer.get('eligible') is not True or answer.get('direction') not in (-1,1):return
        if self._records().get(symbol) is not None:return
        if state['last_candidate'] is not None and now-state['last_candidate']<self.cooldown:return
        if self.started_ms+self.planned_duration_ms-now<=self.cooldown:
            state['issue']='RUN_WINDOW_CLOSING';return
        if now-max(observed,row['event_us']//1000+250)>self.account.policy['max_quote_age_ms']:
            state['issue']='STALE_STRATEGY_INPUT';return
        reference=state['last_book']
        if reference is None:state['issue']='QUOTE_UNAVAILABLE';return
        ident=f'p_{self.run_id}_{symbol}_{row["id"]}'
        bundle=dict(schema='unified.paper.strategy-input.v1',strategy='book_tape_research_v1',
            strategy_revision=self.sources['sources']['bybit-cluster-grid'],source_rows=history+[copy.deepcopy(row)],result=answer)
        signal=_seal(dict(receipt_id=ident+'_proposal',symbol=symbol,source_id='GRID_CAUSAL_TAPE_STRATEGY',raw_sha256=digest(bundle),
            decision_ms=now,observed_ms=observed,expires_ms=now+self.account.policy['entry_wait_ms'],
            side='long' if answer['direction']==1 else 'short'))
        funding=self._funding(symbol,now)
        self._current();risk=self.account.reserve(ident,signal=signal,strategy='book_tape_research_v1',
            strategy_revision=self.sources['sources']['bybit-cluster-grid'],evidence_class=self.sources['evidence_class'],
            reference_quote=reference,funding=funding,now_ms=now)
        state['last_candidate']=now;state['candidates']+=1
        if risk['accepted'] is True:
            # Retain a known committed reservation even if audit/decision
            # publication fails next. This is routing metadata, never cash proof.
            self._pending[symbol]=dict(id=ident,signal=copy.deepcopy(signal),status='RESERVED',
                decision=None,entry_quote=None,close_decision=None,risk_receipt=copy.deepcopy(risk),
                funding=copy.deepcopy(funding),strategy='book_tape_research_v1',
                strategy_revision=self.sources['sources']['bybit-cluster-grid'],evidence_class=self.sources['evidence_class'])
        self._audit('RISK_DECISION',symbol,ident,now,dict(strategy_bundle=bundle,proposal=signal,risk=risk,
            reference_quote_row=state['last_book_row'],funding_row=state['funding'][1] if funding is not None else None))
        if risk['accepted'] is not True:
            state['denied']+=1;state['issue']='RISK_DENIED_'+risk['reason']
            need(risk['reason']!='LEDGER_CAPACITY','PIPELINE_CAPACITY');return
        # Actual decision is constructed and durably committed AFTER risk. No
        # already fetched book row can satisfy its later-event clock requirement.
        at=self._now()
        if at+self.account.policy['latency_ms']>signal['expires_ms']:
            self.account.mark_uncertain(ident,'QUOTE_TIMEOUT',now_ms=at)
            state['issue']='PROPOSAL_TTL_CONSUMED';return
        decision=_seal(dict(signal,receipt_id=ident+'_decision',source_id='STRATT_PAPER_RISK_DECISION',
            raw_sha256=digest(dict(schema='stratt.paper.risk-decision-input.v1',proposal_sha256=signal['sha256'],risk_sha256=digest(risk))),
            decision_ms=at,observed_ms=at,expires_ms=signal['expires_ms']))
        decision.pop('sha256');decision['sha256']=digest(decision)
        updated=self.account.record_decision(ident,decision,now_ms=at);self._pending[symbol]=updated
        self._audit('ENTRY_DECISION',symbol,ident,at,dict(decision=decision))

    def _book(self,symbol,row,connection,now,financial):
        state=self.state[symbol];payload=row['payload'];previous=state['last_book']
        if previous is not None:
            prior=state.get('last_book_source')
            if prior is not None and (payload['sequence']<=prior['sequence'] or payload['update_id']<=prior['update_id']):
                self._uncertain(symbol,'SOURCE_GAP',now);state['issue']='BOOK_SEQUENCE_REGRESSION';return
        quote=_seal(dict(receipt_id=f'q_{self.run_id}_{symbol}_{row["id"]}',symbol=symbol,source_id='GRID_PERSISTED_LOCAL_BOOK',
            raw_sha256=row['row_sha256'],epoch='BOOK_'+connection,sequence=row['id'],
            event_ms=row['event_us']//1000,observed_ms=(row['ingest_us']+999)//1000,
            bid=float(payload['best_bid']),ask=float(payload['best_ask'])))
        state['last_book']=quote;state['last_book_source']=copy.deepcopy(payload);state['last_book_row']=copy.deepcopy(row)
        observed=quote['observed_ms']
        if state['first_book_ingest_ms'] is None:state['first_book_ingest_ms']=observed
        if state['last_book_ingest_ms'] is not None:
            state['max_book_gap_ms']=max(state['max_book_gap_ms'],observed-state['last_book_ingest_ms'])
        state['last_book_ingest_ms']=observed
        if not financial:return
        record=self._records().get(symbol)
        if record is None or record['status']=='UNCERTAIN':return
        if record['status']=='DECIDED':
            decision=record['decision']
            if quote['event_ms']<decision['decision_ms']+self.account.policy['latency_ms']:return
            updated=self.account.record_entry(record['id'],quote,now_ms=now);self._pending[symbol]=updated
            self._audit('ENTRY_SELECTED',symbol,record['id'],now,dict(source_row=row,quote=quote))
        elif record['status']=='EXIT_DECIDED':
            decision=record['close_decision']
            if quote['event_ms']<decision['decision_ms']+self.account.policy['latency_ms']:return
            request=dict(schema='stratt.paper.quote.request.v1',request_id=record['id'],strategy=record['strategy'],
                strategy_revision=record['strategy_revision'],evidence_class=record['evidence_class'],symbol=symbol,
                units={'price':'USDT/'+symbol[:-4],'qty':symbol[:-4]},policy=self.account.execution_policy,
                signal=record['decision'],close_signal=decision,quotes=[record['entry_quote'],quote],funding=record['funding'])
            self._current();result=self.account.close_trade(request,now_ms=now);state['closed']+=1
            del self._pending[symbol]
            self._audit('LEDGER_COMMITTED',symbol,record['id'],now,dict(source_row=row,request_sha256=digest(request),result_sha256=digest(result)))

    def poll(self):
        with self._lock:
            try:
                self._current()
                if self._ended:return self.status()
                now=self._now();self._advance(now)
                if now>=self.started_ms+self.planned_duration_ms:
                    self._ended=True;self._audit('WINDOW_ENDED',None,None,now,dict(qualification='NOT_EVALUATED',unresolved_reservations=len(self._pending)))
                    return self.status()
                for symbol in SYMBOLS:
                    self._current();now=self._now();state=self.state[symbol]
                    request=dict(symbol=symbol,after_id=state['cursor'],start_ms=max(0,now-self.source_max_age_ms),
                        end_ms=now+1,as_of_ms=now,max_age_ms=self.source_max_age_ms)
                    try:
                        packet=self._validate_packet(self.read_source(copy.deepcopy(request)))
                        need(packet['request']==request and len(canonical(packet))<=MAX_PACKET_BYTES,'PIPELINE_SOURCE_REJECTED')
                    except Exception:state['issue']='SOURCE_UNAVAILABLE';continue
                    self._current();at=self._now()
                    financial=packet.get('producer_context_status')=='CONSISTENT'
                    if any(row['event_type']=='derivatives_ticker' for row in packet['rows']):
                        tickers=[r for r in packet['rows'] if r['event_type']=='derivatives_ticker']
                        pending=self._records().get(symbol)
                        if pending is not None and pending.get('funding') is not None:
                            payload=tickers[-1]['payload']
                            try:
                                changed=(_int_numeric(payload['next_funding_time'])!=pending['funding']['next_ms']
                                    or _int_numeric(payload['funding_interval_hour'],scale=3600000)!=pending['funding']['interval_ms'])
                            except Exception:changed=False # Unknown facts do not become fabricated changes.
                            if changed:self._uncertain(symbol,'FUNDING_CHANGED',at)
                        state['funding']=(copy.deepcopy(packet),copy.deepcopy(tickers[-1])) if packet['funding_status']=='KNOWN_SOURCE_FIELDS' and financial else None
                    for row in packet['rows']:
                        self._current();at=self._now();kind=row['event_type'];event=row['event_us']
                        previous=state['last_event'].get(kind)
                        if previous is not None and event<=previous:
                            state['issue']='SOURCE_EVENT_REGRESSION';self._uncertain(symbol,'SOURCE_GAP',at);continue
                        state['last_event'][kind]=event;state['received']+=1
                        connection=self._context(symbol,row,at)
                        if connection is None:continue
                        if kind=='orderbook_snapshot':self._book(symbol,row,connection,at,financial)
                        elif kind=='trade_tape_250ms':
                            history=list(state['prefix']);answer=state['strategy'].observe(dict(symbol=symbol,event_type=kind,
                                event_ts=event//1000,payload=row['payload']))
                            if financial:self._proposal(symbol,row,(row['ingest_us']+999)//1000,answer,history,at)
                            state['prefix'].append(copy.deepcopy(row))
                    state['cursor']=packet['cursor']
                    if packet.get('availability',{}).get('state') in ('PARTIAL','UNAVAILABLE'):state['issue']='VISIBLE_PREFIX_'+packet['availability']['state']
                self._advance(self._now());return self.status()
            except PipelineBlocked as error:
                if self._blocked is None:self._blocked=error.code
                raise
            except Exception:
                self._blocked='PIPELINE_ACCOUNT_REJECTED';raise PipelineBlocked(self._blocked) from None

    def publish(self):
        with self._lock:
            self._current()
            try:
                # Financial corruption is a producer stop, not an ignored view
                # callback failure hidden inside a successful display write.
                paper=self.account.verified_paper_snapshot()
                sources={'paper':lambda:paper}
                if self.market_snapshot is not None:sources['market']=self.market_snapshot
                if self.fleet_snapshot is not None:sources['fleet']=self.fleet_snapshot
                result=self.writer.publish(expected_sequence=self._publication_sequence,generated_at_ms=self._now(),sources=sources)
                need(type(result) is dict and result.get('sequence')==self._publication_sequence+1)
                self._publication_sequence+=1;return result
            except Exception:
                # Never retry a failed publication into retained staging files.
                # Account collateral and all native/journal evidence remain.
                try:self._audit('PUBLICATION_BLOCKED',None,None,self._now(),dict(code='PIPELINE_PUBLICATION_REJECTED'))
                except Exception:pass
                self._blocked='PIPELINE_PUBLICATION_REJECTED';raise PipelineBlocked(self._blocked) from None

    def status(self):
        return dict(schema='unified.lab.paper-pipeline.v1',run_id=self.run_id,mode='LAB_SIMULATION',
            state='BLOCKED' if self._blocked else 'WINDOW_ENDED' if self._ended else 'OBSERVING',error_code=self._blocked,
            elapsed_ms=self._last_clock-self.started_ms,planned_duration_ms=self.planned_duration_ms,
            capacity_forecast_decisions=self.forecast,source_authenticity='NOT_EVALUATED',
            source_completeness='NOT_EVALUATED',execution_authority=False,trading_authorized=False,
            publication_sequence=self._publication_sequence,nodes='NOT_ATTESTED',
            qualification='NOT_EVALUATED',unresolved_reservations=len(self._pending),
            instruments={symbol:{key:value for key,value in state.items() if key in ('cursor','received','issue','candidates','denied','closed',
                'first_book_ingest_ms','last_book_ingest_ms','max_book_gap_ms')}
                for symbol,state in self.state.items()})
