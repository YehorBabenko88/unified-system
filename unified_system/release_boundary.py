"""Independent bounded receipt oracle; release/receipt admission is external policy.

No source import, network, shared SQLite writer, process launch or trading path.
"""
from dataclasses import dataclass
import hashlib
import json
import math
import re
import uuid

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(value):return hashlib.sha256(canonical(value)).hexdigest()
def integer(v):return type(v) is int and 0<=v<=2**53-1
def text(v):return isinstance(v,str) and 0<len(v)<=256
def number(v):
    try:return type(v) in (int,float) and math.isfinite(v)
    except OverflowError:return False
def hex_string(v,n):return type(v) is str and re.fullmatch('[0-9a-f]{'+str(n)+'}',v) is not None
def v11(value):return isinstance(value,dict) and value=={'major':1,'minor':1} and all(type(x) is int for x in value.values())
def deny(reason):return {'verdict':'UNAVAILABLE','reason':reason,'execution_authorized':False,'trading_authorized':False,'physical_acceptance':'NOT_RUN'}

@dataclass(frozen=True)
class ReleasePin:
    producer:str
    revision:str
    tree:str
    artifact_sha256:str
    def __post_init__(self):
        if self.producer not in ('strattester','bybit-cluster-grid') or not hex_string(self.revision,40) or not hex_string(self.tree,40) or not hex_string(self.artifact_sha256,64):raise ValueError('release pin schema')
    def matches(self,revision,tree,artifact_bytes):
        return (revision==self.revision and tree==self.tree and isinstance(artifact_bytes,bytes)
                and 0<len(artifact_bytes)<=33554432 and hashlib.sha256(artifact_bytes).hexdigest()==self.artifact_sha256)

def validate_owned(record):
    """Independent reconstruction of exact input windows, not a hash-only check."""
    if not isinstance(record,dict) or len(canonical(record))>900000:return 'ARTIFACT_BOUNDS'
    if not v11(record.get('api_version')) or record.get('producer')!='strattester':return 'RECORD_VERSION'
    if record.get('mode')!='HISTORICAL' or record.get('execution_authority') is not False:return 'HISTORICAL_ONLY'
    if not text(record['producer_identity']) or not hex_string(record['source_revision'],40):return 'PRODUCER_IDENTITY'
    for key in ('run_id','producer_epoch'):
        if not isinstance(record[key],str):return 'PRODUCER_EPOCH'
        uuid.UUID(record[key])
    if not hex_string(record['completion_receipt'],64) or record['completion_receipt']!=digest({k:v for k,v in record.items() if k!='completion_receipt'}):return 'COMPLETION_INTEGRITY'
    d=record['dataset'];entries=record['input_snapshot']
    if not isinstance(d,dict) or d.get('coverage')!='COMPLETE' or d.get('missing_data')!=[]:return 'GAP'
    if d.get('market_type') not in ('spot','linear','inverse') or any(not text(d.get(k)) for k in ('source_identity','symbol','timeframe')):return 'DATASET_IDENTITY'
    if any(not integer(d.get(k)) for k in ('start_ms','end_ms')) or d['end_ms']<d['start_ms']:return 'DATASET_WINDOW'
    if not integer(record.get('completed_at_ms')) or record['completed_at_ms']<d['end_ms']:return 'COMPLETION_TIME'
    if not isinstance(entries,list) or not 1<=len(entries)<=32:return 'DATASET_MISSING'
    descriptors=[];seen=set()
    allowed={'candles','mark_price','index_price','premium_index','open_interest','funding','long_short_ratio','public_trades','public_trade_aggregates'}
    for entry in entries:
        kind,tf,rows=entry['dataset'],entry['timeframe'],entry['rows']
        if kind not in allowed or not isinstance(tf,str) or not re.fullmatch('[1-9][0-9]{0,4}[mhd]',tf):return 'DATASET_ADAPTER'
        step=int(tf[:-1])*{'m':60000,'h':3600000,'d':86400000}[tf[-1]]
        if (kind,tf) in seen or d['start_ms']%step or d['end_ms']%step:return 'DATASET_WINDOW'
        seen.add((kind,tf))
        if not isinstance(rows,list) or len(rows)>10000 or len(rows)!=(d['end_ms']-d['start_ms'])//step+1:return 'GAP'
        for index,row in enumerate(rows):
            if not isinstance(row,dict):return 'DATASET_ROW'
            ts=row.get('open_time',row.get('ts',row.get('funding_time')))
            if not integer(ts) or ts!=d['start_ms']+index*step:return 'GAP'
            if row.get('symbol',d['symbol'])!=d['symbol'] or row.get('timeframe',tf)!=tf:return 'DATASET_IDENTITY'
            if kind in ('candles','mark_price','index_price','premium_index','open_interest') and (type(row.get('complete')) not in (bool,int) or row['complete']!=1):return 'PARTIAL'
            if kind in ('candles','mark_price','index_price','premium_index'):
                if any(not number(row.get(k)) for k in ('open','high','low','close')) or not row['low']<=min(row['open'],row['close'])<=max(row['open'],row['close'])<=row['high']:return 'DATA_QUALITY'
            if kind=='candles' and (not number(row.get('volume')) or row['volume']<0):return 'DATA_QUALITY'
            if kind=='open_interest' and (not number(row.get('value')) or row['value']<0):return 'DATA_QUALITY'
            if kind=='funding' and not number(row.get('rate')):return 'DATA_QUALITY'
        descriptors.append({'dataset':kind,'timeframe':tf,'count':len(rows)})
    if d.get('datasets')!=descriptors or d['timeframe']!=','.join(sorted({x['timeframe'] for x in descriptors})):return 'DATASET_DESCRIPTOR'
    if not hex_string(d.get('fingerprint'),64) or d['fingerprint']!=digest({'dataset':{k:v for k,v in d.items() if k!='fingerprint'},'rows':entries}):return 'DATASET_INTEGRITY'
    strategy=record['strategy'];model=record['model'];assumptions=record['execution_assumptions']
    if not isinstance(strategy,dict) or any(not text(strategy.get(k)) for k in ('id','version')) or not hex_string(strategy.get('fingerprint'),64) or not isinstance(strategy.get('parameters'),dict):return 'STRATEGY_VERSION'
    if not isinstance(model,dict) or any(not text(model.get(k)) for k in ('kind','version')):return 'MODEL_VERSION'
    if not isinstance(assumptions,dict) or not text(assumptions.get('execution')) or any(not number(assumptions.get(k)) or assumptions[k]<0 for k in ('fees','slippage')):return 'EXECUTION_ASSUMPTIONS'
    if not isinstance(record.get('metrics'),(dict,list)):return 'METRICS_SCHEMA'
    return None

class HistoricalBoundary:
    def __init__(self,release,admitted_receipts,*,artifact_bytes=None):
        if not isinstance(release,ReleasePin) or release.producer!='strattester':raise ValueError('Strattester release required')
        self.release=release;self.admitted=frozenset(tuple(x) for x in admitted_receipts);self.artifact_bytes=artifact_bytes
        if len(self.admitted)>10000:raise ValueError('receipt policy bounds')
    def verify(self,record,*,observed_revision,observed_tree,artifact_bytes):
        try:
            if not self.release.matches(observed_revision,observed_tree,artifact_bytes):return deny('RELEASE_PIN_MISMATCH')
            reason=validate_owned(record)
            if reason:return deny(reason)
            if record['source_revision']!=observed_revision:return deny('RECORD_REVISION_MISMATCH')
            pin=(record['producer_identity'],record['source_revision'],record['run_id'],record['completion_receipt'])
            if pin not in self.admitted:return deny('OWNER_RECEIPT_NOT_ADMITTED')
            return {'verdict':'VERIFIED_SOURCE_RECEIPT','mode':'HISTORICAL','run_id':record['run_id'],
                    'completion_receipt':record['completion_receipt'],'dataset_fingerprint':record['dataset']['fingerprint'],
                    'source_revision':observed_revision,'release_digest':self.release.artifact_sha256,
                    'source_authenticity':'OWNER_POLICY_ADMITTED','runtime_attestation':'UNVERIFIED',
                    'execution_authorized':False,'trading_authorized':False,'physical_acceptance':'NOT_RUN'}
        except (KeyError,TypeError,ValueError,AttributeError,OverflowError,RecursionError):return deny('MALFORMED_SOURCE_RECORD')
    def lifecycle_verifier(self,stage,evidence,*,status,completed,total):
        if stage not in ('STRAT_RESULT_SEALED','HANDOFF_VERIFY') or status!='COMPLETE' or not integer(completed) or not integer(total) or completed!=total:return deny('UNSUPPORTED_SOURCE_STAGE')
        try:result=self.verify(evidence['record'],observed_revision=evidence['revision'],observed_tree=evidence['tree'],artifact_bytes=self.artifact_bytes)
        except (TypeError,KeyError):return deny('MALFORMED_SOURCE_RECORD')
        if result['verdict']=='VERIFIED_SOURCE_RECEIPT':result.update(stage=stage,status=status,completed=completed,total=total)
        return result

def inspect_market(payload,*,now_ms=None):
    """Observe unqualified market data without making ingestion imply order authority."""
    result={'status':'UNAVAILABLE','reason':'GRID_SOURCE_UNQUALIFIED','market_truth':'NOT_ATTESTED','ingestion_requires_trading':False,'trading_authorized':False}
    try:
        if not isinstance(payload,dict) or len(canonical(payload))>8388608 or payload.get('producer')!='bybit-cluster-grid' or not v11(payload.get('api_version')) or payload.get('read_only') is not True:return result
        if payload.get('execution_authority',False) is not False or payload.get('trading_authorized',False) is not False:return result
        status=payload.get('status')
        if status not in ('PARTIAL','STALE','GAP','UNAVAILABLE'):
            result['reason']='UNATTESTED_AVAILABLE_FORBIDDEN';return result
        if status=='UNAVAILABLE':return result
        rows=payload['rows']
        if not isinstance(rows,list) or not 1<=len(rows)<=1000 or payload['dataset_fingerprint']!=digest(rows):return result
        times=[];epochs=set()
        for row in rows:
            if not v11(row['api_version']) or row['producer']!='bybit-cluster-grid' or row['representation']!='historical_aggregate' or row['execution_authority'] is not False:return result
            if row.get('status') not in ('PARTIAL','STALE','GAP') or row.get('quality_status') not in ('GOOD','DEGRADED') or row.get('symbol')!=payload.get('symbol') or row.get('timeframe')!='1m' or payload.get('timeframe')!='1m':return result
            candle=row['candle'];levels=row['levels']
            if any(not number(candle.get(k)) for k in ('open','high','low','close','buy_volume','sell_volume','delta','poc_price')) or not integer(candle.get('trade_count')):return result
            if not 0<candle['low']<=min(candle['open'],candle['close'])<=max(candle['open'],candle['close'])<=candle['high'] or min(candle['buy_volume'],candle['sell_volume'])<0 or candle['trade_count']==0:return result
            if not math.isclose(candle['delta'],candle['buy_volume']-candle['sell_volume'],rel_tol=1e-12,abs_tol=1e-12):return result
            if not isinstance(levels,list) or not 1<=len(levels)<=10000:return result
            prices=set()
            for level in levels:
                if any(not number(level.get(k)) for k in ('price','buy_volume','sell_volume','delta','volume')) or any(not integer(level.get(k)) for k in ('buy_count','sell_count')):return result
                price=level['price']
                if price in prices or min(level['buy_volume'],level['sell_volume'])<0:return result
                prices.add(price)
                if price<candle['low'] and not math.isclose(price,candle['low'],rel_tol=0,abs_tol=max(math.ulp(price),math.ulp(candle['low']))*8):return result
                if price>candle['high'] and not math.isclose(price,candle['high'],rel_tol=0,abs_tol=max(math.ulp(price),math.ulp(candle['high']))*8):return result
                if not math.isclose(level['delta'],level['buy_volume']-level['sell_volume'],rel_tol=1e-12,abs_tol=1e-12) or not math.isclose(level['volume'],level['buy_volume']+level['sell_volume'],rel_tol=1e-12,abs_tol=1e-12):return result
            if any(not math.isclose(sum(l[k] for l in levels),candle[k],rel_tol=1e-12,abs_tol=1e-12) for k in ('buy_volume','sell_volume')) or sum(l['buy_count']+l['sell_count'] for l in levels)!=candle['trade_count']:return result
            if not any(l['price']==candle['poc_price'] and math.isclose(l['volume'],max(x['volume'] for x in levels),rel_tol=1e-12,abs_tol=1e-12) for l in levels):return result
            if row['quality_status']=='DEGRADED' or row['status']=='GAP':status='GAP'
            elif row['status']=='STALE' and status!='GAP':status='STALE'
            if row['dataset_fingerprint']!=digest({k:v for k,v in row.items() if k!='dataset_fingerprint'}):return result
            if any(not integer(row.get(k)) for k in ('start_ms','end_ms','source_event_start_ms','source_event_end_ms','ingestion_ms')):return result
            if row['start_ms']%60000 or not row['start_ms']<=row['source_event_start_ms']<=row['source_event_end_ms']<=row['end_ms']==row['start_ms']+59999 or row['ingestion_ms']<row['source_event_end_ms']:return result
            source=row['source']
            if source['market_type'] not in ('linear','spot','inverse') or not text(source['identity']) or not hex_string(source['source_revision'],40):return result
            uuid.UUID(source['epoch']);epochs.add(source['epoch']);times.append(row['start_ms'])
        if len(set(times))!=len(times):return result
        if len(epochs)!=1 or (max(times)-min(times))//60000+1!=len(times):status='GAP'
        if now_ms is not None:
            if not integer(now_ms) or max(r['source_event_end_ms'] for r in rows)>now_ms:return result
            if status!='GAP' and now_ms-max(r['source_event_end_ms'] for r in rows)>120000:status='STALE'
        result.update(status=status,reason='EXCHANGE_COMPLETENESS_NOT_INDEPENDENTLY_ATTESTED',dataset_fingerprint=payload['dataset_fingerprint'])
        return result
    except (KeyError,TypeError,ValueError,AttributeError,OverflowError,RecursionError):return result

class MarketBoundary:
    def __init__(self,release):
        if not isinstance(release,ReleasePin) or release.producer!='bybit-cluster-grid':raise ValueError('Grid release required')
        self.release=release
    def inspect(self,payload,*,observed_revision,observed_tree,artifact_bytes,now_ms=None):
        if not self.release.matches(observed_revision,observed_tree,artifact_bytes):return {'status':'UNAVAILABLE','reason':'RELEASE_PIN_MISMATCH','trading_authorized':False,'ingestion_requires_trading':False}
        result=inspect_market(payload,now_ms=now_ms)
        try:
            if any(r['source']['source_revision']!=self.release.revision for r in payload.get('rows',[])):
                result.update(status='UNAVAILABLE',reason='PRODUCER_REVISION_MISMATCH')
        except (KeyError,TypeError,AttributeError):result.update(status='UNAVAILABLE',reason='PRODUCER_REVISION_MISMATCH')
        return result
