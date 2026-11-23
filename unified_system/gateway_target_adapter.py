"""Direct disposable target only. No scheduler, authenticated submit or publication.

Trusted commissioning chooses two source repositories and an OWN temporary root.
Local context is test-call custody, NOT a Windows identity or native authority.
Journal is the existing local receipt primitive, never an experiment registry.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import threading
import time
import sys
import importlib
import importlib.machinery
import importlib.util
import types
from itertools import islice
import uuid

from .journal import Journal

REQUEST_SCHEMA='unified.gateway.target-request.v2'
RESULT_SCHEMA='unified.gateway.direct-target-result.v2'
CAPABILITY='terminan.ohlcv.untouched_levels.v1'
TERMINAN_HEAD='45313745e5d5e173022a5a8cdd2cfd2c38ea560d'
MATH_HEAD='2740143eabbc321c6085df625940fdb63f62759f'
DATASET_SHA='44639dea28a646d2a308655d7adc3f85e24a90bda22971632f88d1dd9760c938'
RESEARCH_SHA='4a8b7be2fa7cfbf72399e4abf864287feb8b10a28977aea2970846b8fb97e7e9'
EXPECTED_ARTIFACT_SHA='c7cdb408d8536fa4db3dcb714ff7ae7d64c562a45189005b23242d7da3991174'
EXPECTED_DESCRIPTOR_SHA='89a14da61c021536abeaa794388ae520210748138ddf4663c1aaf61f3db0e09b'
_FIXED_RESEARCH=json.loads("{\"analysis_now_ms\":360000,\"decision_ms\":300000,\"experiment\":{\"id\":\"fixture.gateway.btc.levels\",\"revision\":\"2\"},\"operation\":\"terminan.ohlcv.untouched_levels.v1\",\"payload\":{\"as_of_ms\":300000,\"dataset_id\":\"4cce8c09a40f4b5c231054e48971be6cb912742018f72ea0093009cc024b33d5\",\"end_ms\":180000,\"evidence_class\":\"SYNTHETIC\",\"market_type\":\"linear\",\"rows\":[{\"close\":11,\"event_end_ms\":60000,\"event_start_ms\":0,\"high\":12,\"low\":8,\"open\":10,\"volume\":3},{\"close\":10,\"event_end_ms\":120000,\"event_start_ms\":60000,\"high\":11,\"low\":9,\"open\":10,\"volume\":2},{\"close\":12,\"event_end_ms\":180000,\"event_start_ms\":120000,\"high\":12,\"low\":10,\"open\":11,\"volume\":4}],\"schema\":\"terminan.ohlcv.research.request.v1\",\"source\":{\"identity\":\"SYNTHETIC_GATEWAY_FIXTURE\",\"kind\":\"HISTORICAL_BACKFILL\",\"raw_sha256\":\"82a2c7750f843c97edaf2b1400ef986ccd976ff4eb510a0ea10c5e2fd6ca6ecf\",\"retrieval_id\":\"fixture_btc_3rows\",\"retrieved_at_ms\":240000,\"source_revision\":\"6360a75a428c0cb1538085820381324bc4dd9d6f\"},\"start_ms\":0,\"symbol\":\"BTCUSDT\",\"timeframe\":\"1m\",\"units\":{\"price\":\"USDT/BTC\",\"volume\":\"BTC\"},\"venue\":\"bybit\"},\"schema\":\"unified.gateway.fixed-ohlcv.request.v2\"}")
LOCAL_PRINCIPAL='11111111-1111-4111-8111-111111111111'
BUDGET={'max_input_bytes':16384,'max_output_bytes':16384,'max_rows':3,'max_executions':1}
_MARKER=b'unified.canonical-target.owned-disposable.v2\n'
_IMPORT_LOCK=threading.RLock()


class TargetRejected(ValueError):pass


def _need(value,code='TARGET_CONTRACT_REJECTED'):
    if not value:raise TargetRejected(code)


def _canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')
def _sha(raw):return hashlib.sha256(raw).hexdigest()


def _pairs(pairs):
    result={}
    for key,value in pairs:
        _need(key not in result);result[key]=value
    return result


def _decode(raw):
    _need(type(raw) is bytes and 0<len(raw)<=16384)
    try:
        value=json.loads(raw.decode('ascii'),object_pairs_hook=_pairs,
                         parse_constant=lambda _: (_ for _ in ()).throw(TargetRejected('TARGET_CONTRACT_REJECTED')))
        _need(_canonical(value)==raw)
        return value
    except (ValueError,TypeError,UnicodeError,RecursionError,OverflowError):
        raise TargetRejected('TARGET_CONTRACT_REJECTED') from None


def template_request():
    """Fixed data-only template; its fields issue no authority or permission."""
    return dict(schema=REQUEST_SCHEMA,request_id='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
        target_kind='terminan',target_capability=CAPABILITY,target_version=TERMINAN_HEAD,
        dataset_manifest_id='local-sha256:'+DATASET_SHA,dataset_revision='CANONICAL_FIXTURE_2',
        experiment_id='fixture.gateway.btc.levels',strategy_version=None,parameters_digest=RESEARCH_SHA,
        execution_mode='DIRECT_DISPOSABLE_SYNTHETIC',resource_budget=copy.deepcopy(BUDGET),
        quota_owner='LOCAL_TEST_ONLY',principal_id=LOCAL_PRINCIPAL,authority_generation=None,
        assignment_revision=None,fencing_token=None,idempotency_key='fixed-btc-three-row-2',
        result_schema=RESULT_SCHEMA,result_artifact_ref=None)


class _Prepared:
    __slots__=('raw',)
    def __init__(self,raw):self.raw=raw


def prepare_target(raw):
    value=_decode(raw);expected=template_request()
    _need(type(value) is dict and set(value)==set(expected))
    for name in expected.keys()-{'request_id','idempotency_key'}:
        # Canonical bytes enforce bool/int and nested exact types, no Python == alias.
        _need(_canonical(value[name])==_canonical(expected[name]))
    for name in ('request_id',):
        _need(type(value[name]) is str and re.fullmatch('[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}',value[name]) is not None)
    for name in ('idempotency_key','experiment_id'):
        _need(type(value[name]) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,95}',value[name]) is not None)
    return _Prepared(raw)


def public_submit(_request):raise TargetRejected('PUBLIC_SUBMIT_DENY')


def capability_registry():
    rows=[]
    for repo,kind in [('terminan','historical_backtest'),('terminan','historical_replay'),('math','statistical_computation'),('terminan',CAPABILITY)]:
        active=kind==CAPABILITY
        rows.append(dict(owning_repository=repo,capability=kind,
            availability='DIRECT_DISPOSABLE_ONLY' if active else 'UNAVAILABLE',
            entrypoint='terminan.analytics.ohlcv_research.analyze_ohlcv_research -> terminan.analytics.core.untouched_levels -> market_math.untouched_decimal_levels' if active else None,
            input_schema='terminan.ohlcv.research.request.v1' if active else None,
            output_schema='terminan.ohlcv.research.result.v1' if active else None,
            dataset='local-sha256:'+DATASET_SHA if active else None,resource_budget=copy.deepcopy(BUDGET) if active else None,
            authority_scope='LOCAL_TEST_SCOPE_NOT_AUTHENTICATED' if active else None,
            cancellation='COOPERATIVE_DISCARD_BEFORE_RESULT_COMMIT' if active else 'UNAVAILABLE',
            recovery='ORIGINAL_INTENT_UNKNOWN_NO_REEXECUTION' if active else 'UNAVAILABLE',scheduler_admission='BLOCKED',
            limitations=['NO_NATIVE_CPU_RSS_CONTAINMENT','NO_SCHEDULER_OR_PUBLICATION','SYNTHETIC_LOCAL_ONLY'] if active else ['NOT_QUALIFIED_FOR_THIS_ADAPTER']))
    return rows


class _LocalContext:
    __slots__=()


class DisposableTargetStand:
    """Exclusive own temporary workspace. Not a hostile-local-admin sandbox.

    Only fixed pinned source is executed. Trusted commissioning owns directory
    ACL/custody and Python/dependencies; source hashes do not authenticate code.
    The small fixed workload is in-process/cooperative, NOT a CPU/RSS guarantee.
    """
    def __init__(self,root,*,terminan_source_root,math_source_root,git_executable,git_sha256,runtime_sha256):
        self.root=Path(root).absolute();self.terminan_source_root=terminan_source_root;self.math_source_root=math_source_root
        self.git_executable=git_executable;self.git_sha256=git_sha256;self.runtime_sha256=runtime_sha256
        self._contexts=[];self._cancelled=set();self._mutex=threading.Lock();self._decision_lock=threading.Lock();self._closed=True;self.invocations=0
        self._lock=None
        try:
            self._runtime_custody()
            for path in (self.root,*self.root.parents):
                s=path.lstat();_need(stat.S_ISDIR(s.st_mode) and not getattr(s,'st_file_attributes',0)&1024 and not path.is_symlink())
            entries=list(islice(self.root.iterdir(),4));_need(len(entries)<=3)
            names={p.name for p in entries}
            _need(names<= {'canonical-target.v2.marker','canonical-target.v2.lock','canonical-target.v2.sqlite'})
            for child in entries:
                info=child.lstat();_need(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and not getattr(info,'st_file_attributes',0)&1024 and not child.is_symlink())
                cap=len(_MARKER) if child.name=='canonical-target.v2.marker' else 1 if child.name=='canonical-target.v2.lock' else 2097152
                _need(info.st_size<=cap)
            marker=self.root/'canonical-target.v2.marker'
            if names:_need(marker.read_bytes()==_MARKER)
            else:
                with marker.open('xb') as stream:stream.write(_MARKER)
            self._lock=(self.root/'canonical-target.v2.lock').open('a+b')
            info=os.fstat(self._lock.fileno());_need(info.st_nlink==1 and not getattr(info,'st_file_attributes',0)&1024)
            if info.st_size==0:self._lock.write(b'0');self._lock.flush()
            self._lock.seek(0)
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(self._lock.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self._lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            path=self.root/'canonical-target.v2.sqlite'
            if path.exists():
                info=path.lstat();_need(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and not getattr(info,'st_file_attributes',0)&1024 and info.st_size<=2097152)
            self._journal=Journal(path);self._journal.initialize();self._records();self._closed=False
        except BaseException:
            if self._lock:self._lock.close()
            raise TargetRejected('DISPOSABLE_STAND_UNAVAILABLE') from None

    def close(self):
        with self._mutex:
            self._closed=True
            for state in self._contexts:state[3].set()
            if self._lock:self._lock.close();self._lock=None

    def local_test_context(self,*,scope='DIRECT_TARGET',lifetime_seconds=60):
        _need(not self._closed and type(scope) is str and type(lifetime_seconds) is int and 0<=lifetime_seconds<=60 and len(self._contexts)<32)
        ctx=_LocalContext();self._contexts.append((ctx,scope,time.monotonic()+lifetime_seconds,threading.Event()));return ctx

    def revoke(self,context):
        with self._decision_lock:
            state=next((state for state in self._contexts if context is state[0]),None)
            _need(state is not None);state[3].set()

    def cancel(self,request_id):
        with self._decision_lock:
            _need(type(request_id) is str and len(request_id)<=36 and len(self._cancelled)<64)
            self._cancelled.add(request_id)

    def _check(self,context):
        state=next((state for state in self._contexts if context is state[0]),None)
        _need(not self._closed and type(context) is _LocalContext and state is not None
              and not state[3].is_set() and state[1]=='DIRECT_TARGET' and time.monotonic()<state[2],'LOCAL_TEST_SCOPE_DENIED')

    def _records(self):
        _need(self._journal.path.stat().st_size<=2097152)
        records=self._journal.read();_need(len(records)<=64);requests={};keys={}
        for row in records:
            receipt=row['receipt'];_need(type(receipt) is dict and len(receipt)==6 and set(receipt)=={'schema','request_raw','request_sha256','phase','result_raw','result_sha256'})
            _need(receipt['schema']=='unified.canonical-target.journal.v2')
            text=receipt['request_raw'];_need(type(text) is str and 0<len(text)<=16384)
            original=text.encode('ascii');prepare_target(original);q=_decode(original);_need(_sha(original)==receipt['request_sha256'])
            phase=receipt['phase'];_need(type(phase) is str and phase in ('STARTED','FINISHED'))
            request_id=q['request_id'];key=q['idempotency_key']
            if phase=='STARTED':
                _need(request_id not in requests and key not in keys and receipt['result_raw'] is None and receipt['result_sha256'] is None)
                requests[request_id]=(original,'STARTED');keys[key]=request_id
            else:
                _need(request_id in requests and requests[request_id]==(original,'STARTED') and keys.get(key)==request_id)
                text=receipt['result_raw'];_need(type(text) is str and 0<len(text)<=16384)
                result=text.encode('ascii');_need(_sha(result)==receipt['result_sha256']);value=_decode(result)
                self._validate_stored_result(q,original,value);requests[request_id]=(original,'FINISHED')
        return records

    def _validate_stored_result(self,q,raw,value):
        _need(type(value) is dict and type(value.get('status')) is str)
        status=value['status'];error=value.get('error');actual=None
        if status=='DIRECT_TARGET_PASS':
            _need(error is None and type(value.get('result')) is dict and type(value.get('research_descriptor')) is dict)
            artifact=_canonical(value['result']);descriptor=value['research_descriptor']
            _need(len(artifact)<=8192 and _sha(artifact)==EXPECTED_ARTIFACT_SHA and _sha(_canonical(descriptor))==EXPECTED_DESCRIPTOR_SHA)
            actual=dict(artifact_bytes=artifact,descriptor=descriptor)
        else:_need((status,error) in (('CANCELLED','LOCAL_CANCELLED'),('FAILED','TARGET_RESULT_UNAVAILABLE'),('UNKNOWN','TARGET_RESULT_UNAVAILABLE')))
        expected=self._envelope(q,raw,status,actual,error)
        _need(_canonical(expected)==_canonical(value),'STORED_RESULT_BINDING_REJECTED')

    def _append(self,raw,phase,result=None):
        records=self._records();_need(len(records)<64,'LOCAL_JOURNAL_CAPACITY')
        data=None if result is None else _canonical(result)
        self._journal.append('OBSERVING',dict(schema='unified.canonical-target.journal.v2',request_raw=raw.decode('ascii'),
            request_sha256=_sha(raw),phase=phase,result_raw=None if data is None else data.decode('ascii'),
            result_sha256=None if data is None else _sha(data)),expected_sequence=len(records))

    def _runtime_custody(self):
        from .owned_python import reject_external_namespace
        from integration.source_guard import _ordinary
        _need(sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode,'ISOLATED_RUNTIME_REQUIRED')
        _need(type(self.runtime_sha256) is str and re.fullmatch('[a-f0-9]{64}',self.runtime_sha256) is not None)
        executable=_ordinary(sys.executable);_need(executable.stat().st_size<=64*1024*1024 and _sha(executable.read_bytes())==self.runtime_sha256,'RUNTIME_PIN_MISMATCH')
        _need(type(sys.pycache_prefix) is str and Path(sys.pycache_prefix).is_absolute(),'ISOLATED_CACHE_REQUIRED')
        cache=_ordinary(sys.pycache_prefix).resolve(strict=True);_need(cache.is_dir() and next(cache.iterdir(),None) is None,'FRESH_ISOLATED_CACHE_REQUIRED')
        if os.name!='nt':_need(stat.S_IMODE(cache.stat().st_mode)&0o077==0,'PRIVATE_CACHE_REQUIRED')
        for raw in (self.terminan_source_root,self.math_source_root,self.git_executable):
            _need(type(raw) is str and Path(raw).is_absolute());reject_external_namespace(raw)
        for source in (self.terminan_source_root,self.math_source_root):
            path=Path(source).resolve();_need(cache!=path and path not in cache.parents and cache not in path.parents,'CACHE_SOURCE_OVERLAP')
        _need(all(getattr(hook,'__module__','') in ('_frozen_importlib','_frozen_importlib_external') for hook in sys.meta_path),'UNQUALIFIED_IMPORT_HOOK')
        self._cache=cache

    def _source_fences(self):
        from integration.source_guard import SourceFence
        self._runtime_custody();fences={}
        for owner,root,pin,repo in [('terminan',self.terminan_source_root,TERMINAN_HEAD,'Terminan'),('math',self.math_source_root,MATH_HEAD,'math')]:
            fence=SourceFence(root,pin,isolated_cache=self._cache,git_executable=self.git_executable,git_sha256=self.git_sha256)
            snapshot=fence.check();_need(all(item['comparison']=='RAW_IDENTICAL' for item in snapshot['runtime_files'].values()),'RAW_SOURCE_REQUIRED')
            origin=fence.git('config','--get','remote.origin.url').decode().strip()
            _need(origin in ('https://github.com/YehorBabenko88/'+repo,'https://github.com/YehorBabenko88/'+repo+'.git'),'SOURCE_ORIGIN_MISMATCH')
            fences[owner]=fence
        return fences

    @staticmethod
    def _app_modules(fences):
        for name,module in tuple(sys.modules.items()):
            owner='terminan' if name=='terminan' or name.startswith('terminan.') else 'math' if name in ('market_math','market_compute_api','market_math_api') else None
            if owner is not None:
                _need(type(module) is types.ModuleType and type(getattr(module,'__cached__',None)) is str,'QUALIFIED_APP_CACHE_REQUIRED')
                spec=getattr(module,'__spec__',None);_need(spec is not None and isinstance(spec.loader,importlib.machinery.SourceFileLoader),'QUALIFIED_SOURCE_LOADER_REQUIRED')
                _need(getattr(spec,'origin',None)==getattr(module,'__file__',None) and spec.loader.path==module.__file__,'SOURCE_SPEC_MISMATCH')
                fences[owner].module(module)

    def _invoke(self,cancelled):
        with _IMPORT_LOCK:return self._invoke_locked(cancelled)

    def _invoke_locked(self,cancelled):
        try:
            fences=self._source_fences();self._app_modules(fences)
            _need(cancelled() is False,'LOCAL_CANCELLED')
            original_path=list(sys.path)
            base=Path(sys.base_prefix).resolve()
            stdlib=[]
            for item in original_path:
                if not item:continue
                path=Path(item).resolve()
                if (path==base or base in path.parents) and not any(part in ('site-packages','dist-packages') for part in path.parts):stdlib.append(item)
            try:
                sys.path[:]=[self.terminan_source_root,str(Path(self.math_source_root)/'python'),*stdlib]
                for name,expected in [('terminan',Path(self.terminan_source_root)/'terminan/__init__.py'),('market_math',Path(self.math_source_root)/'python/market_math.py')]:
                    spec=importlib.util.find_spec(name);_need(spec is not None and spec.origin is not None and Path(spec.origin).resolve()==expected.resolve(),'SOURCE_IMPORT_SHADOW')
                module=importlib.import_module('terminan.analytics.ohlcv_research');self._app_modules(fences)
                research=copy.deepcopy(_FIXED_RESEARCH);_need(_sha(_canonical(research))==RESEARCH_SHA and _sha(_canonical(research['payload']))==DATASET_SHA)
                _need(cancelled() is False,'LOCAL_CANCELLED');self.invocations+=1
                value=module.analyze_ohlcv_research(research['payload'],decision_ms=research['decision_ms'],now_ms=research['analysis_now_ms'])
                artifact=_canonical(value)
                descriptor=dict(schema='unified.gateway.canonical-research-descriptor.v2',capability=CAPABILITY,terminan_revision=TERMINAN_HEAD,math_revision=MATH_HEAD,
                    request_sha256=RESEARCH_SHA,dataset_sha256=DATASET_SHA,artifact=dict(raw_sha256=_sha(artifact),byte_count=str(len(artifact))),
                    scope='SYNTHETIC_LOCAL_UNATTESTED',financial=dict(net_pnl=None),execution_authority=False,trading_authorized=False,training_authorized=False)
                self._app_modules(fences)
            finally:sys.path[:]=original_path
            for fence in fences.values():
                snapshot=fence.finish();_need(all(item['comparison']=='RAW_IDENTICAL' for item in snapshot['runtime_files'].values()),'RAW_SOURCE_REQUIRED')
            _need(cancelled() is False,'LOCAL_CANCELLED')
            return dict(descriptor=descriptor,artifact_bytes=artifact)
        except TargetRejected:raise
        except Exception:raise TargetRejected('TARGET_SOURCE_OR_ANALYTICS_UNAVAILABLE') from None



    def _envelope(self,q,raw,status,result=None,error=None):
        artifact=None if result is None else result['artifact_bytes']
        return dict(schema=RESULT_SCHEMA,status=status,request_id=q['request_id'],request_sha256=_sha(raw),
            target_capability=CAPABILITY,target_version=TERMINAN_HEAD,experiment_id=q['experiment_id'],
            dataset={'manifest_id':q['dataset_manifest_id'],'revision':q['dataset_revision'],'raw_sha256':DATASET_SHA,'kind':'FIXED_SYNTHETIC_LOCAL_NOT_QUALIFIED_MARKET_DATA'},
            parameters_digest=q['parameters_digest'],execution_mode=q['execution_mode'],resource_budget=copy.deepcopy(BUDGET),
            result=None if artifact is None else json.loads(artifact),research_descriptor=None if result is None else result['descriptor'],
            result_artifact_ref=None if artifact is None else {'kind':'LOCAL_UNATTESTED_SHA256','sha256':_sha(artifact),'byte_count':str(len(artifact))},
            publication_status='LOCAL_UNATTESTED',execution_authority=False,scheduler_admission='BLOCKED',
            authenticated_gateway=False,physical_acceptance=False,error=error,
            provenance={'terminan_head':TERMINAN_HEAD,'math_head':MATH_HEAD,'research_input_sha256':RESEARCH_SHA},
            limitations=['LOCAL_TEST_SCOPE_NOT_AUTHENTICATED','NO_NATIVE_RESOURCE_CONTAINMENT','NO_REPLICA_OR_PUBLICATION_PROOF','NO_ORDERS_NO_LEDGER','WHOLE_WINDOW_NOT_HISTORICAL_SIGNAL'])

    def execute(self,prepared,*,context):
        self._check(context);_need(type(prepared) is _Prepared)
        raw=prepare_target(prepared.raw).raw;q=_decode(raw)
        with self._mutex:
            self._check(context)
            try:
                records=self._records();matches=[]
                for row in records:
                    r=row['receipt'];prior=_decode(r['request_raw'].encode('ascii'))
                    if prior['request_id']==q['request_id'] or prior['idempotency_key']==q['idempotency_key']:
                        _need(r['request_raw'].encode('ascii')==raw,'IDEMPOTENCY_COLLISION');matches.append(r)
                if matches:
                    last=matches[-1]
                    return _decode(last['result_raw'].encode('ascii')) if last['phase']=='FINISHED' else self._envelope(q,raw,'UNKNOWN',error='ORIGINAL_INTENT_OUTCOME_UNKNOWN_NO_REEXECUTION')
                self._append(raw,'STARTED')
                def cancelled():
                    self._check(context)
                    return q['request_id'] in self._cancelled
                if cancelled():result=self._envelope(q,raw,'CANCELLED',error='LOCAL_CANCELLED')
                else:
                    try:
                        actual=self._invoke(cancelled)
                        _need(type(actual) is dict and set(actual)=={'descriptor','artifact_bytes'})
                        artifact=actual['artifact_bytes'];_need(type(artifact) is bytes and 0<len(artifact)<=8192)
                        decoded=_decode(artifact)
                        _need(decoded['units']=={'price':'USDT/BTC','volume':'BTC'} and decoded['execution_authority'] is False)
                        _need(actual['descriptor']['artifact']['raw_sha256']==_sha(artifact))
                        _need(actual['descriptor']['artifact']['byte_count']==str(len(artifact)))
                        # Fixed-profile independent golden bytes: JSON Schema
                        # numeric equality does not prove canonical byte identity.
                        _need(_sha(artifact)==EXPECTED_ARTIFACT_SHA and
                              _sha(_canonical(actual['descriptor']))==EXPECTED_DESCRIPTOR_SHA)
                        result=self._envelope(q,raw,'CANCELLED',error='LOCAL_CANCELLED') if cancelled() else self._envelope(q,raw,'DIRECT_TARGET_PASS',actual)
                    except Exception as error:
                        code=getattr(error,'code',None)
                        status=('CANCELLED' if code=='CANCELLED' else 'UNKNOWN'
                                if (isinstance(error,TargetRejected) and str(error)=='LOCAL_TEST_SCOPE_DENIED')
                                or (code is None and not isinstance(error,(TargetRejected,subprocess.SubprocessError,OSError))) else 'FAILED')
                        result=self._envelope(q,raw,status,error='LOCAL_CANCELLED' if status=='CANCELLED' else 'TARGET_RESULT_UNAVAILABLE')
                with self._decision_lock:
                    # Local cancellation/revocation and final Journal commit have
                    # one ordering. This is not distributed commit-time fencing.
                    self._check(context)
                    if q['request_id'] in self._cancelled:result=self._envelope(q,raw,'CANCELLED',error='LOCAL_CANCELLED')
                    _need(len(_canonical(result))<=16384)
                    self._append(raw,'FINISHED',result)
                return result
            except TargetRejected:raise
            except Exception:raise TargetRejected('LOCAL_JOURNAL_OR_RESULT_UNAVAILABLE') from None
