"""Pinned actual producers with synthetic providers only; no exchange/network/keys."""
import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

PINNED={'strattester':'943095d00d5d56276f3832c42b36b290bea77a84','grid':'bf9f108b6777085d6725675eac778d61ec55f42b'}
parser=argparse.ArgumentParser();parser.add_argument('--strattester',required=True);parser.add_argument('--grid',required=True)
args=parser.parse_args()
roots={k:Path(getattr(args,k)).resolve() for k in PINNED}
trees={}
for name,path in roots.items():
    head=subprocess.check_output(['git','-C',str(path),'rev-parse','HEAD'],text=True).strip()
    if head!=PINNED[name]:raise SystemExit('source revision mismatch: '+name)
    trees[name]=subprocess.check_output(['git','-C',str(path),'rev-parse','HEAD^{tree}'],text=True).strip()
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),*(str(x) for x in roots.values())]
from unified_system.release_boundary import HistoricalBoundary,MarketBoundary,ReleasePin,digest
from strattester.research.runner import ResearchRunner
from strattester.marketdata.sqlite_store import SQLiteMarketStore
from strattester.persistence.result_store import ResultStore
from strattester.strategies.base import StrategyDefinition,DataRequirement
from grid.research_handoff import accept_handoff
from grid.cluster import FootprintBuilder
from grid.models import Trade
from grid.provenance import producer,minute_record

class SyntheticHistory:
    calls=0
    def fetch_klines(self,symbol,start,end,interval='1'):
        self.calls+=1
        return [[str(t),'1','2','1','2','1','2'] for t in (60000,0) if start<=t<=end]
class SyntheticResearch:
    def run(self,candles,checkpoint=None):return {'sum':sum(x.close for x in candles)}

with tempfile.TemporaryDirectory(prefix='five-boundary-') as temp:
    store=SQLiteMarketStore.open(Path(temp)/'history.db');results=ResultStore.open(Path(temp)/'results.db')
    try:
        client=SyntheticHistory();definition=StrategyDefinition('fixture','1',(DataRequirement('candles',('1m',)),),SyntheticResearch)
        runner=ResearchRunner(store,client,clock_ms=lambda:999999)
        metadata={'source_identity':'SYNTHETIC_HISTORY','market_type':'linear','producer_identity':'SYNTHETIC_RESEARCH','source_revision':PINNED['strattester'],'model':{'kind':'synthetic','version':'1'},'execution_assumptions':{'execution':'none','fees':0,'slippage':0}}
        output=runner.run(definition,{'symbol':'BTCUSDT','launchTime':'0'},start_ms=0,end_ms=60000,result_store=results,provenance=metadata)
        assert output.output=={'sum':4} and client.calls>0
        record=json.loads(results.con.execute("SELECT record FROM owned_runs WHERE state='COMPLETE'").fetchone()[0])
        release_bytes=b'SYNTHETIC_RELEASE:'+PINNED['strattester'].encode()
        release=ReleasePin('strattester',PINNED['strattester'],trees['strattester'],hashlib.sha256(release_bytes).hexdigest())
        admitted={(record['producer_identity'],record['source_revision'],record['run_id'],record['completion_receipt'])}
        boundary=HistoricalBoundary(release,admitted,artifact_bytes=release_bytes)
        receipt=boundary.verify(record,observed_revision=release.revision,observed_tree=release.tree,artifact_bytes=release_bytes)
        assert receipt['verdict']=='VERIFIED_SOURCE_RECEIPT' and not receipt['trading_authorized']
        assert accept_handoff(record,admitted)['status']=='ACCEPTED_HISTORICAL'
        assert accept_handoff(record,set())['status']=='UNAVAILABLE'
        altered=json.loads(json.dumps(record));altered['metrics']['sum']=999
        altered['completion_receipt']=digest({k:v for k,v in altered.items() if k!='completion_receipt'})
        assert boundary.verify(altered,observed_revision=release.revision,observed_tree=release.tree,artifact_bytes=release_bytes)['verdict']=='UNAVAILABLE'
        builder=FootprintBuilder(.1);builder.add(Trade('BTCUSDT',1,.3,1,'Buy','fixture'))
        row=builder.pop_closed(60000)[0];row['source_provenance']=producer('SYNTHETIC_GRID',PINNED['grid'],'wss://stream.bybit.com/v5/public/linear')
        # Pure producer metadata builder: the URL is never connected.
        minute=minute_record(row,60001,'SYNTHETIC_GRID')
        assert minute['status']=='PARTIAL'
        page={'api_version':{'major':1,'minor':1},'producer':'bybit-cluster-grid','read_only':True,'status':'PARTIAL','symbol':'BTCUSDT','timeframe':'1m','rows':[minute],'dataset_fingerprint':digest([minute])}
        grid_bytes=b'SYNTHETIC_RELEASE:'+PINNED['grid'].encode()
        grid_release=ReleasePin('bybit-cluster-grid',PINNED['grid'],trees['grid'],hashlib.sha256(grid_bytes).hexdigest())
        market=MarketBoundary(grid_release).inspect(page,observed_revision=grid_release.revision,observed_tree=grid_release.tree,artifact_bytes=grid_bytes,now_ms=60001)
        assert market['status']=='PARTIAL' and market['ingestion_requires_trading'] is False
        evidence={'scope':'SYNTHETIC_ONLY_ACTUAL_PINNED_PRODUCERS','source_heads':PINNED,'source_trees':trees,'history_provider_calls':client.calls,'research_to_grid':'PASS','unattested_market':'PARTIAL','physical':'NOT_RUN','production':'NO_GO'}
        print(json.dumps(evidence,sort_keys=True))
    finally:results.close();store.close()
