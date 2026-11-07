"""Independent fake-feed/SQL boundaries and known residual reproduction, no real I/O."""
import hashlib,json,pathlib,subprocess
r=pathlib.Path(__file__).resolve().parents[1];repo=r/'work/review-book268-1f08';out=r/'outputs/phase64';py=r.parent/'codex-agent-3-bybit-historical-live/work/test-venv/Scripts/python.exe'
script='''import sys,json,pathlib,asyncio,copy,ipaddress,time
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
repo=pathlib.Path(sys.argv[1]);out=pathlib.Path(sys.argv[2]);sys.path[:0]=[str(repo),str(repo/'tests')]
def no_external(event,args):
 if event in ('socket.connect','socket.bind'):
  target=args[1]
  if not isinstance(target,tuple) or not ipaddress.ip_address(target[0]).is_loopback:raise AssertionError('NO_PROVIDER_REAL_DB')
sys.addaudithook(no_external)
from grid import microstructure as module
from grid.unified_features import UnifiedFeatureBuilder
from test_scientific_book_capability import good_payload,Socket,frame
now=datetime.now(timezone.utc);row=dict(symbol='BTCUSDT',ts=now,open=100,high=102,low=99,close=101,buy_volume=8,sell_volume=2,delta=6,poc_price=100,quality_status='GOOD')
class Pool:
 def __init__(self,payload,stamp=None,error=False):self.payload=payload;self.stamp=stamp or now;self.error=error;self.queries=[]
 async def fetchrow(self,sql,*args):
  self.queries.append((sql,args))
  if self.error:raise RuntimeError('FAKE_SQL_UNAVAILABLE')
  assert 'symbol=$1' in sql and 'event_ts<=$2' in sql and "event_ts>=$2-($3 * interval '1 second')" in sql and 'ORDER BY event_ts DESC LIMIT 1' in sql
  if 'orderbook_snapshot' not in sql:return None
  return dict(event_ts=self.stamp,payload=self.payload) if self.stamp<=args[1] and self.stamp>=args[1]-timedelta(seconds=args[2]) else None
def built(pool):return asyncio.run(UnifiedFeatureBuilder().build(pool,row))
cases=[]
for mutation in ['missing_quality','nonfinite_spread','boolean_depth','infinite_qty','over200levels','duplicate_price']:
 p=good_payload()
 if mutation=='missing_quality':p.pop('_quality')
 elif mutation=='nonfinite_spread':p['spread']='NaN'
 elif mutation=='boolean_depth':p['bid_depth']=True
 elif mutation=='infinite_qty':p['book']['asks']=[[101,'Infinity']]
 elif mutation=='over200levels':p['book']['bids']=[[100-i/1000,1] for i in range(201)]
 else:p['book']['bids']=[[100,1],[100,2]]
 before=copy.deepcopy(p);v=built(Pool(p));assert not v['capabilities']['orderbook'] and all(v['features'][k] is None for k in ['spread','bid_depth','ask_depth','book_imbalance']) and p==before;cases.append(mutation)
for name,stamp,available in [('future',now+timedelta(milliseconds=1),False),('older_than5s',now-timedelta(seconds=5,milliseconds=1),False),('exact5s',now-timedelta(seconds=5),True)]:
 pool=Pool(good_payload(),stamp);v=built(pool);assert v['capabilities']['orderbook'] is available and pool.queries[0][1]==('BTCUSDT',now,5);cases.append('SQL_asof_'+name)
try:built(Pool(good_payload(),error=True))
except RuntimeError as exc:assert str(exc)=='FAKE_SQL_UNAVAILABLE'
else:raise AssertionError('DATABASE_ERROR_FABRICATED_FEATURE_SUCCESS')
cases.append('SQL_error_propagates_no_feature_success')
# Real collector logic over fake frames leaves only its previous valid persisted row.
class Recording:
 def __init__(self):self.rows=[]
 async def insert_event(self,symbol,ts,kind,payload):self.rows.append(dict(symbol=symbol,event_ts=ts,kind=kind,payload=payload))
async def feed():
 db=Recording();ms=int(time.time()*1000);sock=Socket([json.dumps(dict(op='subscribe',success=True)),frame(ms,100,'snapshot',[['100','1']],[['101','2']]),frame(ms+1000,101,'delta',[['100','0']],[])])
 async def ready():pass
 with patch.object(module,'wait_for_internet',ready),patch.object(module.websockets,'connect',lambda *a,**k:sock):
  try:await module.MicrostructureCollector(db).run_batch(['BTCUSDT'])
  except asyncio.CancelledError:pass
  else:raise AssertionError('EXPECTED_FAKE_SOCKET_END')
 return [x for x in db.rows if x['kind']=='orderbook_snapshot']
rows=asyncio.run(feed());assert len(rows)==1 and rows[0]['payload']['_quality']['feeds']['orderbook']['status']=='available'
# Mirror existing db.insert_event SQL to_timestamp(event_ms/1000.0); no real DB.
stored_time=datetime.fromtimestamp(rows[0]['event_ts']/1000.0,timezone.utc);now=stored_time+timedelta(seconds=2);row['ts']=now;v=built(Pool(rows[0]['payload'],stored_time));assert v['capabilities']['orderbook'] is True
report=dict(independent_positive_negative_cases=cases,count=10,skips=0,network_provider_real_DB_connections=0,known_residual=dict(status='OPEN_P1_REPRODUCED_NOT_CLOSED',persisted_available_snapshots_after_empty_side_gap=1,query_age_seconds=2,orderbook_capability_still_true=True,scope='PREVIOUS_VALID_ROW_QUERY_ELIGIBLE_UNTIL5S_NO_PERSISTED_INVALIDATION'),summary_metrics_derivation_or_provenance='NOT_QUALIFIED_BY_THIS_GATE')
(out/'independent-extra.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
'''
p=subprocess.run([str(py),'-I','-B','-c',script,str(repo),str(out)],cwd=repo,capture_output=True,timeout=60);(out/'extra.stdout.log').write_bytes(p.stdout);(out/'extra.stderr.log').write_bytes(p.stderr);assert p.returncode==0,p.stderr.decode(errors='replace')[-2000:];print((out/'independent-extra.json').read_text(encoding='utf-8'))
