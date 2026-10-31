"""In-process Unified functional profile; never creates another controller.

The caller publishes only after its ordinary journal tick, SnapshotView update
and atomic snapshot write. Readiness probes those real outputs from a previous
committed cycle: it never calls back into the supervisor while tick holds its
transaction. This is local functional evidence, not fleet or physical authority.
"""
import hashlib
import http.client
import json
import os
import re
import secrets
import socket
import sqlite3
import stat
import threading
import time
from pathlib import Path

from .module_catalog import MODULE_IDS
from .runtime_process import _safe_path

# Six-core baseline: five .5s delegated probes + .25s tick + .35s own
# HTTP + .15s journal margin, rounded to four seconds. Each actual registered
# extension adds .5s; the journal's 64-module limit bounds the age at 33s.
# This is a fail-closed functional budget, not physical/performance qualification.
PUBLICATION_MAX_AGE=4.0
PUBLICATION_EXTRA_MODULE_AGE=.5
LIMIT=1048576
ERROR='BUILTIN_RUNTIME_REJECTED'


def _need(ok):
    if not ok:raise ValueError(ERROR)


def _bytes(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


class BuiltinRuntimeDriver:
    """Composite with one builtin profile and unchanged subprocess delegation.

    No externally supplied health callback can declare this profile ready.
    Operation ownership belongs to this instance, not the controller's OS PID.
    A new instance cannot adopt a previous instance's in-memory registration.
    """
    def __init__(self,delegate,*,journal_path,snapshot_path,http_port,node_id,
                 release_id,release_sha256,authorize=None):
        _need(type(http_port) is int and 1<=http_port<=65535)
        _need(type(node_id) is str and re.fullmatch('[A-Za-z0-9_-]{1,64}',node_id))
        _need(type(release_id) is str and re.fullmatch('[A-Za-z0-9_.:-]{1,128}',release_id))
        _need(type(release_sha256) is str and re.fullmatch('[a-f0-9]{64}',release_sha256))
        self.delegate=delegate;self.journal=_safe_path(journal_path);self.snapshot=_safe_path(snapshot_path)
        _need(self.journal!=self.snapshot)
        self.port=http_port;self.identity=dict(node_id=node_id,release_id=release_id,release_sha256=release_sha256)
        self.authorize=authorize or (lambda *_:False)
        self.generation=secrets.token_hex(32);self.operations={};self.publication=None

    def _journal(self):
        path=_safe_path(self.journal);facts=path.stat()
        _need(facts.st_nlink==1 and facts.st_size<=67108864 and path.is_file())
        # sqlite URI escaping is performed by Path.as_uri; mode=ro cannot create
        # a missing database or write a second journal. Also reject linked WALs.
        for suffix in ('-wal','-shm','-journal'):_safe_path(str(path)+suffix)
        db=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=.1)
        deadline=time.monotonic()+.15
        db.set_progress_handler(lambda: int(time.monotonic()>deadline),100)
        try:
            db.execute('PRAGMA query_only=ON')
            with db:
                db.execute('BEGIN')
                identities=db.execute('SELECT body,revision FROM identity LIMIT 2').fetchall()
                _need(len(identities)==1 and len(identities[0][0])<=4096)
                identity=json.loads(identities[0][0]);revision=identities[0][1]
                _need(identity==self.identity and type(revision) is int and revision>=0)
                rows=db.execute('SELECT id,spec,state FROM modules LIMIT 65').fetchall()
                _need(len(rows)<=64 and MODULE_IDS<=set(row[0] for row in rows))
                modules={}
                for name,spec,state in rows:
                    _need(len(spec)<=16384 and len(state)<=16384)
                    modules[name]=(json.loads(spec),json.loads(state))
                return revision,modules
        finally:db.close()

    def _own(self,op):
        revision,modules=self._journal();spec,state=modules['unified-system']
        _need(state['handle']==op)
        return revision,spec,state

    def _file_bytes(self):
        path=_safe_path(self.snapshot)
        fd=os.open(path,os.O_RDONLY|getattr(os,'O_NONBLOCK',0)|getattr(os,'O_NOFOLLOW',0))
        with os.fdopen(fd,'rb') as stream:
            facts=os.fstat(stream.fileno())
            _need(stat.S_ISREG(facts.st_mode) and facts.st_nlink==1 and facts.st_size<=LIMIT)
            raw=stream.read(LIMIT+1)
        _need(0<len(raw)<=LIMIT)
        return _bytes(json.loads(raw))

    def published(self,snapshot):
        """Record a real committed publication, not a readiness assertion.

        Call immediately after view.set(snapshot) and write_snapshot(...).
        HTTP and file bytes are independently rechecked on every ready probe.
        """
        revision,modules=self._journal()
        _need(type(snapshot) is dict and snapshot.get('schema')=='unified.runtime.v2')
        _need(all(snapshot.get(k)==v for k,v in self.identity.items()))
        _need(snapshot.get('revision')==revision and set(snapshot.get('modules',{}))==set(modules))
        _need(snapshot.get('trading_authorized') is False and snapshot.get('physical_deployment_allowed') is False)
        for name,(spec,state) in modules.items():
            public=snapshot['modules'][name]
            _need(public.get('version')==spec['version'] and public.get('state')==state['state']
                  and public.get('ready') is (state['state']=='READY')
                  and public.get('administrative_stop') is state['admin_stop'])
        raw=_bytes(snapshot);_need(len(raw)<=LIMIT and self._file_bytes()==raw)
        self.publication=(hashlib.sha256(raw).digest(),revision,time.monotonic(),self.generation)

    def start(self,spec,release_id,operation_id):
        if spec.module_id!='unified-system':return self.delegate.start(spec,release_id,operation_id)
        _need(self.authorize('start','unified-system') is True)
        _need(release_id==self.identity['release_id'] and type(operation_id) is str
              and re.fullmatch('[a-f0-9-]{32,36}',operation_id))
        revision,saved,state=self._own(operation_id)
        _need(saved['version']==spec.version and state['desired']=='RUNNING' and not state['admin_stop'])
        prior=self.operations.get(operation_id)
        identity=(spec.version,release_id,self.generation)
        if prior is not None:_need(prior['identity']==identity and prior['active'])
        else:self.operations[operation_id]=dict(identity=identity,active=True,revision=revision)
        return operation_id

    def alive(self,handle):
        record=self.operations.get(handle)
        if record is not None:
            try:
                _,_,state=self._own(handle)
                return record['active'] and record['identity'][2]==self.generation and not state['admin_stop']
            except Exception:return False
        try:self._own(handle)
        except Exception:return self.delegate.alive(handle)
        return False  # Committed builtin handle from another controller instance.

    def _http_bytes(self):
        connection=http.client.HTTPConnection('127.0.0.1',self.port,timeout=.25)
        transport=None;expired=threading.Event()
        def expire():
            expired.set();sock=transport if transport is not None else connection.sock
            if sock is not None:
                try:sock.shutdown(socket.SHUT_RDWR)
                except OSError:pass
        timer=threading.Timer(.35,expire);timer.daemon=True;timer.start()
        try:
            connection.connect();transport=connection.sock
            _need(not expired.is_set())
            connection.request('GET','/internal/v2/runtime')
            response=connection.getresponse();raw=response.read(LIMIT+1)
            _need(not expired.is_set() and response.status==200 and 0<len(raw)<=LIMIT)
            return _bytes(json.loads(raw))
        finally:timer.cancel();connection.close();timer.join()

    def ready(self,spec,handle,release_id):
        if spec.module_id!='unified-system':return self.delegate.ready(spec,handle,release_id)
        try:
            _need(self.alive(handle) and release_id==self.identity['release_id'])
            record=self.operations[handle];_need(record['identity']==(spec.version,release_id,self.generation))
            digest,revision,stamp,generation=self.publication
            _need(generation==self.generation)
            current,modules=self._journal();saved,state=modules['unified-system']
            _need(state['handle']==handle)
            max_age=PUBLICATION_MAX_AGE+PUBLICATION_EXTRA_MODULE_AGE*(len(modules)-len(MODULE_IDS))
            _need(0<=time.monotonic()-stamp<=max_age)
            _need(saved['version']==spec.version)
            _need(record['revision']<=revision<=current and state['desired']=='RUNNING' and not state['admin_stop'])
            _need(hashlib.sha256(self._file_bytes()).digest()==digest)
            _need(hashlib.sha256(self._http_bytes()).digest()==digest)
            _need(0<=time.monotonic()-stamp<=max_age)
            return dict(module_id='unified-system',version=spec.version,release_id=release_id,ready=True)
        except Exception:return {'ready':False}

    def stop(self,handle):
        record=self.operations.get(handle)
        if record is not None:
            record['active']=False;return
        try:self._own(handle)
        except Exception:return self.delegate.stop(handle)
        # A previous-instance builtin registration has no child to terminate.
        # Do not signal the controller PID or delegate a foreign ownership key.
        self.operations[handle]=dict(identity=(None,None,self.generation),active=False,revision=0)
