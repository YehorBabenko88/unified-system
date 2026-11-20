"""Root-only SYNTHETIC_OFFLINE retention/audit around actual canonical SDKs.
No provider, strategy, financial evaluator, store or operational grant is added.
"""
import copy,hashlib,json,os,pathlib,stat,threading,uuid
MAX_PACKET_BYTES=2*1024*1024
MAX_ARTIFACT_BYTES=4*1024*1024
MAX_AUDIT_BYTES=64*1024*1024
MAX_AUDIT_EVENTS=4096

class PipelineBlocked(ValueError):pass

def _need(value,code):
    if not value:raise PipelineBlocked(code)

def _plain(path,*,directory):
    info=path.lstat()
    _need(not stat.S_ISLNK(info.st_mode) and not getattr(info,'st_file_attributes',0)&1024,'PIPELINE_PATH_ALIAS')
    _need(stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode) and info.st_nlink==1,'PIPELINE_PATH_KIND')
    return info.st_dev,info.st_ino

def _fresh_path(value):
    _need(type(value) in (str,type(pathlib.Path())),'PIPELINE_PATH_TYPE')
    path=pathlib.Path(value)
    _need(path.is_absolute() and '..' not in path.parts and not str(path).startswith(('//',chr(92))) and ':' not in str(path)[len(path.drive):],'PIPELINE_LOCAL_PATH_REQUIRED')
    for parent in reversed(path.parents):_plain(parent,directory=True)
    _need(not path.exists() and not path.is_symlink(),'PIPELINE_FRESH_NAMESPACE_REQUIRED')
    return path

def _same_receipt(actual,expected):
    if type(actual) is not type(expected):return False
    if type(expected) is dict:
        if len(actual)!=len(expected) or any(type(k) is not str or k not in expected for k in actual):return False
        return all(_same_receipt(actual[k],v) for k,v in expected.items())
    if type(expected) is list:return len(actual)==len(expected) and all(_same_receipt(a,b) for a,b in zip(actual,expected))
    return actual==expected

class OfflineCausalPipeline:
    @classmethod
    def create(cls,audit_root,*,account,read_source,clock_ms,run_id,strategy_revision,planned_duration_ms,source_max_age_ms,min_history=8):
        self=object.__new__(cls);self._blocked=None;self.account=account;self._lock=threading.RLock()
        self._current()
        _need(callable(read_source) and callable(clock_ms),'PIPELINE_EXPLICIT_CALLBACKS_REQUIRED')
        # All application factories/imports follow exact-True caller freshness.
        # This callback is not source/kernel/service authentication or permission.
        from terminan.causal_account import CausalAccountJournal
        from terminan.causal_session import CausalPaperSession,SessionDescriptor,SessionPublication
        from terminan.causal_artifacts import validate_causal_ledger_artifact
        _need(type(account) is CausalAccountJournal,'PIPELINE_ACTUAL_ACCOUNT_REQUIRED')
        session=CausalPaperSession(account,run_id=run_id,strategy_revision=strategy_revision,planned_duration_ms=planned_duration_ms,source_max_age_ms=source_max_age_ms,clock_ms=clock_ms,min_history=min_history)
        root=_fresh_path(audit_root)
        from .storage.object_store import ObjectStore
        from .journal import Journal
        from .contracts import canonical
        self._session=session;self._descriptor_type=SessionDescriptor;self._publication_type=SessionPublication;self._validate_artifact=validate_causal_ledger_artifact;self._canonical=canonical
        self._read_source=read_source;self._clock_ms=clock_ms;self._last_clock=session.started_ms;self._run_id=run_id;self._source_max_age=source_max_age_ms;self._symbols=tuple(session.status()['instruments'])
        self._descriptor_sequence=0;self._source_refs=set();self._generation=0;self._last_publication=None;self._last_source=None;self._audit_count=0;self._audit_tail='0'*64
        self.root=root;self._current();root.mkdir(exist_ok=False)
        self._root_identity=_plain(root,directory=True);self.path=root/'audit.sqlite'
        with self.path.open('xb'):pass
        self._audit_identity=_plain(self.path,directory=False);self._current()
        try:
            self._store=ObjectStore.create(root/'store',store_id=str(uuid.uuid4()))
            self._audit=Journal(self.path);self._audit.initialize();self._audit_sha=self._file_sha()
            self._append('STARTED',dict(mode='SYNTHETIC_OFFLINE',started_ms=session.started_ms,planned_duration_ms=planned_duration_ms,source_max_age_ms=source_max_age_ms))
        except Exception:
            self._blocked='PIPELINE_INITIALIZATION_UNCONFIRMED';raise
        return self

    def _current(self):
        _need(self._blocked is None,self._blocked or 'PIPELINE_BLOCKED')
        try:valid=callable(getattr(self.account,'require_current',None)) and self.account.require_current() is True
        except Exception:valid=False
        if not valid:self._blocked='PIPELINE_FRESHNESS_UNAVAILABLE'
        _need(valid,self._blocked or 'PIPELINE_FRESHNESS_UNAVAILABLE')

    def _now(self):
        now=self._clock_ms()
        _need(type(now) is int and self._last_clock<=now<=2**53-1,'PIPELINE_CLOCK_REJECTED')
        self._last_clock=now;return now

    def _hash(self,value):return hashlib.sha256(self._canonical(value)).hexdigest()

    def _file_sha(self):
        _plain(self.path,directory=False);before=self.path.stat();_need(before.st_size<=MAX_AUDIT_BYTES,'PIPELINE_AUDIT_CAPACITY')
        digest=hashlib.sha256()
        with self.path.open('rb') as stream:
            for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
        after=self.path.stat()
        _need((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns),'PIPELINE_AUDIT_CHANGED')
        return digest.hexdigest()

    def _guard(self):
        try:
            self._current();_need(_plain(self.root,directory=True)==self._root_identity,'PIPELINE_ROOT_CHANGED')
            names=[]
            for path in self.root.iterdir():
                names.append(path.name);_need(len(names)<=2,'PIPELINE_FOREIGN_NAMESPACE')
            _need(set(names)=={'audit.sqlite','store'},'PIPELINE_FOREIGN_NAMESPACE')
            _need(_plain(self.path,directory=False)==self._audit_identity and self._file_sha()==self._audit_sha,'PIPELINE_AUDIT_CHANGED')
            self._store._check()  # Existing Root identity-bound store check; no adoption.
            records=self._audit.read();tail='0'*64 if not records else self._hash(records[-1])
            _need(len(records)==self._audit_count and tail==self._audit_tail,'PIPELINE_AUDIT_CHAIN_CHANGED')
            self._current()
        except Exception:
            if self._blocked is None:self._blocked='PIPELINE_CUSTODY_UNCERTAIN'
            raise

    def _append(self,kind,detail):
        self._guard();_need(self._audit_count<MAX_AUDIT_EVENTS,'PIPELINE_AUDIT_CAPACITY')
        receipt=dict(schema='unified.offline-causal.audit.v1',kind=kind,run_id=self._run_id,detail=detail,status='LOCAL_UNATTESTED',publication_confirmed=False,native_commit='NOT_ATTEMPTED',source_authenticity='NOT_EVALUATED',point_in_time_availability='UNKNOWN',physical='NOT_RUN',execution_authority=False,trading_authorized=False)
        _need(len(self._canonical(receipt))<=65536,'PIPELINE_AUDIT_RECEIPT_CAPACITY')
        try:
            self._current();body=self._audit.append('OBSERVING',receipt,expected_sequence=self._audit_count)
            expected_count=self._audit_count+1;expected_tail=self._hash(body)
            actual_sha=self._file_sha();records=self._audit.read()
            _need(len(records)==expected_count and self._hash(records[-1])==expected_tail,'PIPELINE_AUDIT_ACK_UNKNOWN')
            self._current();self._audit_count=expected_count;self._audit_tail=expected_tail;self._audit_sha=actual_sha
        except Exception:
            self._blocked='PIPELINE_AUDIT_ACK_UNKNOWN';raise
        return copy.deepcopy(receipt)

    def _put(self,raw,limit):
        self._guard();self._current();stored=self._store.put(raw,max_bytes=limit)
        _need(self._store.read(stored.sha256,max_bytes=limit)==raw,'PIPELINE_OBJECT_READBACK_REJECTED')
        self._current();return stored

    def _events(self,events):
        _need(type(events) is tuple,'PIPELINE_DESCRIPTOR_BATCH_REJECTED')
        for event in events:
            _need(type(event) is self._descriptor_type,'PIPELINE_ACTUAL_DESCRIPTOR_REQUIRED')
            value=event.decode();_need(value['run_id']==self._run_id and value['sequence']==self._descriptor_sequence+1,'PIPELINE_DESCRIPTOR_ORDER_REJECTED')
            _need(value['source_packet_sha256'] is None or value['source_packet_sha256'] in self._source_refs,'PIPELINE_UNRETAINED_SOURCE_REFERENCE')
            stored=self._put(event.payload_json,65536)
            self._append('SESSION_DESCRIPTOR',dict(descriptor_sha256=event.sha256,object_ref=stored.content_ref(),session_sequence=value['sequence'],kind=value['kind'],source_packet_sha256=value['source_packet_sha256']))
            self._descriptor_sequence=value['sequence']
        self._generation+=1

    def _request(self,value,now):
        keys=('symbol','after_id','start_ms','end_ms','as_of_ms','max_age_ms')
        _need(type(value) is dict and len(value)==len(keys) and all(type(k) is str and k in keys for k in value),'PIPELINE_REQUEST_SHAPE_REJECTED')
        _need(type(value['symbol']) is str and value['symbol'] in self._symbols,'PIPELINE_REQUEST_SYMBOL_REJECTED')
        _need(all(type(value[k]) is int and 0<=value[k]<=2**53-1 for k in keys if k!='symbol'),'PIPELINE_REQUEST_CLOCK_REJECTED')
        _need(value['max_age_ms']==self._source_max_age and value['as_of_ms']<=now,'PIPELINE_REQUEST_CUT_REJECTED')
        _need(value['after_id']==self._session.status()['instruments'][value['symbol']]['cursor'],'PIPELINE_REQUEST_CURSOR_REJECTED')
        raw=self._canonical(value);_need(len(raw)<=2048,'PIPELINE_REQUEST_BYTES_REJECTED');return json.loads(raw)

    def poll(self,request):
        with self._lock:
            self._guard()
            try:
                now=self._now()
                if self._session.status()['state'] in ('WINDOW_ENDED','FINISHED'):return self.status()
                if now>=self._session.started_ms+self._session.duration:
                    self._events(self._session.advance());return self.status()
                query=self._request(request,now)
                try:packet=self._read_source(copy.deepcopy(query))
                except Exception:
                    self._current();self._events(self._session.advance());self._append('SOURCE_UNAVAILABLE',dict(source_request_sha256=self._hash(query)));return self.status()
                from market_data.paper_inputs import validate_paper_inputs
                checked=validate_paper_inputs(packet)
                _need(checked['request']==query and all(type(checked['request'][k]) is type(query[k]) for k in query),'PIPELINE_SOURCE_QUERY_REJECTED')
                raw=self._canonical(checked);stored=self._put(raw,MAX_PACKET_BYTES);self._last_source=stored.sha256
                self._append('SOURCE_PACKET_RETAINED',dict(object_ref=stored.content_ref(),source_packet_sha256=stored.sha256,source_request_sha256=self._hash(query)))
                self._source_refs.add(stored.sha256)
                # Never advance ordinary financial timers before a visible gap.
                self._current();events=self._session.accept_packet(checked,expected_request=query);self._events(events);return self.status()
            except Exception:
                if self._blocked is None:self._blocked='PIPELINE_SOURCE_OR_CONSUMER_UNCERTAIN'
                raise

    def advance(self):
        with self._lock:
            self._guard()
            try:self._now();self._events(self._session.advance());return self.status()
            except Exception:
                if self._blocked is None:self._blocked='PIPELINE_CONSUMER_UNCERTAIN'
                raise

    def finish(self):
        with self._lock:
            self._guard()
            try:self._now();self._events(self._session.finish());return self.status()
            except Exception:
                if self._blocked is None:self._blocked='PIPELINE_CONSUMER_UNCERTAIN'
                raise

    def status(self):
        return dict(schema='unified.offline-causal-pipeline.status.v1',run_id=self._run_id,state='BLOCKED' if self._blocked else self._session.status()['state'],error_code=self._blocked,audit_sequence=self._audit_count,last_source_packet_sha256=self._last_source,session=self._session.status(),mode='SYNTHETIC_OFFLINE',status='LOCAL_UNATTESTED',publication_confirmed=False,native_commit='NOT_ATTEMPTED',source_authenticity='NOT_EVALUATED',point_in_time_availability='UNKNOWN',physical='NOT_RUN',execution_authority=False,trading_authorized=False)

    def publish(self):
        with self._lock:
            self._guard()
            try:
                if self._last_publication is not None and self._last_publication[0]==self._generation:
                    receipt=self._last_publication[1];self._read_publication(receipt);return copy.deepcopy(receipt)
                publication=self._session.publication_artifact()
                _need(type(publication) is self._publication_type and type(publication.artifact_json) is bytes,'PIPELINE_ACTUAL_PUBLICATION_REQUIRED')
                self._validate_artifact(publication.artifact_json,expected_sha256=publication.sha256)
                stored=self._put(publication.artifact_json,MAX_ARTIFACT_BYTES)
                self._events((publication.descriptor,))
                receipt=self._append('PAPER_ARTIFACT_RETAINED',dict(paper_sha256=publication.sha256,object_ref=stored.content_ref(),durability=stored.durability,descriptor_sha256=publication.descriptor.sha256))
                self._last_publication=(self._generation,receipt);return copy.deepcopy(receipt)
            except Exception:
                if self._blocked is None:self._blocked='PIPELINE_PUBLICATION_UNCONFIRMED'
                raise

    def _read_publication(self,receipt):
        raw=self._store.read(receipt['detail']['paper_sha256'],max_bytes=MAX_ARTIFACT_BYTES)
        _need(hashlib.sha256(raw).hexdigest()==receipt['detail']['paper_sha256'],'PIPELINE_PUBLICATION_CHANGED');self._current();return raw

    def read_publication(self,receipt):
        with self._lock:
            self._guard();_need(self._last_publication is not None and _same_receipt(receipt,self._last_publication[1]),'PIPELINE_UNKNOWN_PUBLICATION')
            try:return self._read_publication(receipt)
            except Exception:
                if self._blocked is None:self._blocked='PIPELINE_PUBLICATION_UNCONFIRMED'
                raise
