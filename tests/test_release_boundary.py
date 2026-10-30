import copy
import hashlib
import json
import unittest
from pathlib import Path
from unified_system.release_boundary import ReleasePin,HistoricalBoundary,MarketBoundary,digest,inspect_market

RECORD=json.loads((Path(__file__).parent/'fixtures/owned-run.synthetic.json').read_text())
ARTIFACT=b'explicit synthetic release fixture, never a real producer binary'
PIN=ReleasePin('strattester',RECORD['source_revision'],'b'*40,hashlib.sha256(ARTIFACT).hexdigest())
def boundary(record=RECORD):
    return HistoricalBoundary(PIN,{(record['producer_identity'],record['source_revision'],record['run_id'],record['completion_receipt'])},artifact_bytes=ARTIFACT)
def reseal(record):
    d=record['dataset'];d['fingerprint']=digest({'dataset':{k:v for k,v in d.items() if k!='fingerprint'},'rows':record['input_snapshot']})
    record['completion_receipt']=digest({k:v for k,v in record.items() if k!='completion_receipt'})
    return record

class ReleaseBoundaryTests(unittest.TestCase):
    def verify(self,record=RECORD,oracle=None,**kwargs):
        return (oracle or boundary()).verify(record,observed_revision=PIN.revision,observed_tree=PIN.tree,artifact_bytes=ARTIFACT,**kwargs)
    def test_independent_source_oracle_and_release_admission(self):
        result=self.verify()
        self.assertEqual(result['verdict'],'VERIFIED_SOURCE_RECEIPT')
        self.assertFalse(result['execution_authorized']);self.assertFalse(result['trading_authorized'])
        self.assertEqual(result['physical_acceptance'],'NOT_RUN')
    def test_no_pin_and_rehashed_forgery_denied(self):
        self.assertEqual(self.verify(oracle=HistoricalBoundary(PIN,set()))['verdict'],'UNAVAILABLE')
        forged=copy.deepcopy(RECORD);forged['metrics']['sum']=99;reseal(forged)
        self.assertEqual(self.verify(forged)['verdict'],'UNAVAILABLE')
    def test_self_consistent_gap_and_invalid_data_never_sealed(self):
        for mutation in ('gap','ohlc','boolean','model'):
            record=copy.deepcopy(RECORD)
            if mutation=='gap':record['input_snapshot'][0]['rows'].pop()
            elif mutation=='ohlc':record['input_snapshot'][0]['rows'][0]['close']=999
            elif mutation=='boolean':record['api_version']['major']=True
            else:record['model']={}
            reseal(record)
            self.assertEqual(self.verify(record,oracle=boundary(record))['verdict'],'UNAVAILABLE',mutation)
    def test_release_bytes_and_tree_are_independent(self):
        b=boundary()
        self.assertEqual(b.verify(RECORD,observed_revision=PIN.revision,observed_tree='c'*40,artifact_bytes=ARTIFACT)['verdict'],'UNAVAILABLE')
        self.assertEqual(b.verify(RECORD,observed_revision=PIN.revision,observed_tree=PIN.tree,artifact_bytes=b'wrong')['verdict'],'UNAVAILABLE')
    def test_transition_proof_is_historical_only(self):
        evidence={'record':RECORD,'revision':PIN.revision,'tree':PIN.tree}
        result=boundary().lifecycle_verifier('HANDOFF_VERIFY',evidence,status='COMPLETE',completed=0,total=0)
        self.assertEqual(result['stage'],'HANDOFF_VERIFY');self.assertEqual(result['status'],'COMPLETE')
        self.assertEqual(boundary().lifecycle_verifier('GRID_MARKET_READY',evidence,status='COMPLETE',completed=0,total=0)['verdict'],'UNAVAILABLE')
    def test_market_missing_completeness_and_false_available(self):
        for status in ('PARTIAL','STALE','GAP','AVAILABLE'):
            value={'api_version':{'major':1,'minor':1},'producer':'bybit-cluster-grid','read_only':True,'status':status,'reason':'SYNTHETIC'}
            result=inspect_market(value)
            self.assertFalse(result['ingestion_requires_trading'])
            self.assertNotEqual(result['status'],'AVAILABLE')
    def test_valid_market_partial_requires_release_pin_and_invalid_rows_denied(self):
        row={'api_version':{'major':1,'minor':1},'producer':'bybit-cluster-grid','source':{'identity':'fixture','epoch':'00000000-0000-4000-8000-000000000001','source_revision':'a'*40,'market_type':'linear'},'symbol':'BTCUSDT','timeframe':'1m','start_ms':0,'end_ms':59999,'source_event_start_ms':1,'source_event_end_ms':59999,'ingestion_ms':60000,'representation':'historical_aggregate','execution_authority':False,'quality_status':'GOOD','status':'PARTIAL','candle':{'open':1,'high':2,'low':1,'close':2,'buy_volume':1,'sell_volume':0,'delta':1,'trade_count':1,'poc_price':2},'levels':[{'price':2,'buy_volume':1,'sell_volume':0,'delta':1,'volume':1,'buy_count':1,'sell_count':0}]}
        row['dataset_fingerprint']=digest(row)
        page={'api_version':{'major':1,'minor':1},'producer':'bybit-cluster-grid','read_only':True,'status':'PARTIAL','symbol':'BTCUSDT','timeframe':'1m','rows':[row],'dataset_fingerprint':digest([row])}
        release=ReleasePin('bybit-cluster-grid','a'*40,'b'*40,PIN.artifact_sha256)
        oracle=MarketBoundary(release)
        result=oracle.inspect(page,observed_revision='a'*40,observed_tree='b'*40,artifact_bytes=ARTIFACT,now_ms=60000)
        self.assertEqual(result['status'],'PARTIAL')
        for declared in ('STALE','GAP'):
            weaker=copy.deepcopy(page);r=weaker['rows'][0];r['status']=declared
            r['dataset_fingerprint']=digest({k:v for k,v in r.items() if k!='dataset_fingerprint'});weaker['dataset_fingerprint']=digest([r])
            self.assertEqual(oracle.inspect(weaker,observed_revision='a'*40,observed_tree='b'*40,artifact_bytes=ARTIFACT)['status'],declared)
        for kind in ('authority','row_unavailable','ohlc','symbol','poc','nonpositive'):
            bad=copy.deepcopy(page);r=bad['rows'][0]
            if kind=='authority':bad['execution_authority']=True
            elif kind=='row_unavailable':r['status']='UNAVAILABLE'
            elif kind=='ohlc':r['candle']['close']=999
            elif kind=='symbol':r['symbol']='OTHER'
            elif kind=='poc':r['candle']['poc_price']=1.5
            else:r['candle']['low']=0
            r['dataset_fingerprint']=digest({k:v for k,v in r.items() if k!='dataset_fingerprint'});bad['dataset_fingerprint']=digest([r])
            self.assertEqual(oracle.inspect(bad,observed_revision='a'*40,observed_tree='b'*40,artifact_bytes=ARTIFACT)['status'],'UNAVAILABLE',kind)

if __name__=='__main__':unittest.main()
