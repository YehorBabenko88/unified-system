"""Independent in-memory-only SQL recorder; no database, network or deletion."""
import asyncio,hashlib,importlib.util,json,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1];repo=ROOT/'work/review-grid262';out=ROOT/'outputs/phase14';out.mkdir(exist_ok=True)
head='a17f1db6b9aa04c105d2e993496026a83849ecfd';path='grid/instrument_lifecycle.py';raw=(repo/path).read_bytes()
blob=subprocess.check_output(['git','-C',str(repo),'show',head+':'+path]);assert raw==blob
spec=importlib.util.spec_from_file_location('a8_lifecycle_probe',repo/path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class FakeConnection:
 def __init__(self):self.calls=[]
 async def fetch(self,query,*args):self.calls.append({'method':'fetch','sql':query,'args':args});return [{'symbol':'A8_SYNTHETIC_RETIRED'}]
 async def fetchval(self,query,*args):self.calls.append({'method':'fetchval','sql':query,'args':args});return False
 async def execute(self,query,*args):self.calls.append({'method':'execute','sql':query,'args':args});return 'FAKE_ONLY_NO_DATABASE'
class Context:
 def __init__(self,c):self.c=c
 async def __aenter__(self):return self.c
 async def __aexit__(self,*args):pass
class Pool:
 def __init__(self):self.c=FakeConnection()
 def acquire(self):return Context(self.c)
pool=Pool();result=asyncio.run(module.purge_retired(pool,grace_days=30));deletes=[c for c in pool.c.calls if c['sql'].startswith('DELETE ')]
assert result==['A8_SYNTHETIC_RETIRED'] and len(deletes)==6
assert (repo/path).read_bytes()==raw
evidence={'head':head,'tree':subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD^{tree}']).decode().strip(),'path':path,'git_blob':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),'source_sha256':hashlib.sha256(raw).hexdigest(),'calls':pool.c.calls,'returned':result,'delete_statements_recorded':6,'environment':'IN_MEMORY_FAKE_POOL_ONLY_NO_DATABASE_NO_NETWORK','active_refresh_call':'grid/coordinator.py:953','actual_historical_data_loss':'NOT_OBSERVED_NOT_TESTED','risk':'RETIREMENT_PLUS_NO_STRATEGY_JOB_TRIGGERS_HISTORY_DELETE_WITHOUT_EXPLICIT_RETENTION_OR_REPLICA_GATES','status':'FAIL_SOURCE_SAFETY_OPEN_PENDING_EXACT_FIX_REVIEW','severity':'P1'}
(out/'retired-history-probe.json').write_text(json.dumps(evidence,indent=2));print(json.dumps(evidence))
