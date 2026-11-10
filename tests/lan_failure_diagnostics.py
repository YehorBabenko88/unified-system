"""Test-only, best-effort heartbeat failure line. No runtime/authority API.

Exactly two connection/store slots; bounded IO scalars, never an event trace.
Worker callbacks never print. Original calls run once even if observation fails.
"""
import contextlib
import itertools
import json
import sys
import threading
import time
from unittest.mock import patch

PREFIX='LAN_FAIL_DIAG_V1 '
LIMIT=1960
_CODES=frozenset(('NONE','OTHER','ASSERTION','BUSY','UNAVAILABLE','DIAGNOSTIC_UNAVAILABLE','DEADLINE','DISCONNECTED','DELIVERY_UNKNOWN','CANCELLED','POLICY_REVOKED','BUDGET_STORE_UNAVAILABLE','BUDGET_CLOCK_UNCERTAIN','OVERLOADED','CLOSED','AUTH_REJECTED','PROTOCOL_REJECTED'))
_KINDS=frozenset(('NONE','OTHER','HELLO','OPEN','CREDIT','APP','PING','PONG','MUX_FRAGMENT'))
_PHASES=frozenset(('NONE','OTHER','SEND','ASSERT','WAIT','TX_BODY','TX_COMMIT','TX_DONE','TX_ERROR','TX_ERROR_EXIT','READ_1','READ_5','READ_OTHER','READ_DONE','READ_ERROR'))

def _enum(value,allowed,default='OTHER'):
    return value if type(value) is str and value in allowed else default

def _int(value,maximum=9999999,minimum=0):
    return min(maximum,max(minimum,value)) if type(value) is int else 0

def _dict(value):return value if type(value) is dict else {}
def _items(value,count):return value[:count] if type(value) in (list,tuple) else ()
def _bool(value):return value is True

def format_failure(state,code='OTHER'):
    """Rebuild from an allowlist; no arbitrary repr/str/keys enter the line."""
    state=_dict(state)
    body=dict(v=1,stage=_enum(state.get('stage'),_PHASES),code=_enum(code,_CODES),observer=_enum(state.get('observer'),frozenset(('OK','BUSY','UNAVAILABLE'))),connections=[],stores=[],io=[],truncated=_bool(state.get('truncated')))
    for item in _items(state.get('connections'),2):
        item=_dict(item)
        if item.get('busy') is True or item.get('unavailable') is True:
            body['connections'].append(dict(state='BUSY' if item.get('busy') is True else 'UNAVAILABLE'));continue
        streams=[];jobs=[]
        for row in _items(item.get('streams'),2):
            if type(row) in (list,tuple) and len(row)==4:streams.append([_int(row[0],16),_bool(row[1]),_int(row[2],2**63-1),_int(row[3],2**63-1)])
        for row in _items(item.get('jobs'),2):
            if type(row) in (list,tuple) and len(row)==5:jobs.append([_enum(row[0],_KINDS),_enum(row[1],frozenset(('control','live','bulk'))),_bool(row[2]),_enum(row[3],_CODES),_int(row[4],9999999,-9999999)])
        body['connections'].append(dict(slot=_int(item.get('slot'),2),closed=_bool(item.get('closed')),why=_enum(item.get('why'),_CODES),age_ms=_int(item.get('age_ms')),q=_int(item.get('q'),64),qb=_int(item.get('qb'),1048576),streams=streams,jobs=jobs,alive=[_bool(x) for x in _items(item.get('alive'),5)]))
    for item in _items(state.get('stores'),2):
        item=_dict(item);body['stores'].append(dict(phase=_enum(item.get('phase'),_PHASES),waiters=_int(item.get('waiters'),16),held=_bool(item.get('held')),entry_ms=_int(item.get('entry_ms')),hold_ms=_int(item.get('hold_ms')),max_ms=_int(item.get('max_ms')),n=_int(item.get('n')),budget_waiters=_int(item.get('budget_waiters'),16),budget_ms=_int(item.get('budget_ms'))))
    for item in _items(state.get('io'),4):
        item=_dict(item);body['io'].append(dict(slot=_int(item.get('slot'),2),channel=_enum(item.get('channel'),frozenset(('control','data'))),read=_enum(item.get('read'),_PHASES),write=_enum(item.get('write'),_KINDS),n=_int(item.get('n'),65536),remaining_ms=_int(item.get('remaining_ms'),9999999,-9999999),elapsed_ms=_int(item.get('elapsed_ms')),active=_bool(item.get('active')),error=_enum(item.get('error'),_CODES)))
    if any(type(state.get(name)) in (list,tuple) and len(state[name])>cap for name,cap in (('connections',2),('stores',2),('io',4))):body['truncated']=True
    def encode():return PREFIX+json.dumps(body,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)+'\n'
    line=encode()
    if len(line.encode('ascii'))>LIMIT:
        body['truncated']=True;body['io']=body['io'][:2]
        for row in body['connections']:
            if 'jobs' in row:row['jobs']=row['jobs'][:1];row['streams']=row['streams'][:1]
        line=encode()
    if len(line.encode('ascii'))>LIMIT:
        line=PREFIX+'{"code":"DIAGNOSTIC_UNAVAILABLE","truncated":true,"v":1}\n'
    return line


class FailureDiagnostics:
    def __init__(self,writer=None):
        self._writer=writer;self._lock=threading.Lock();self._connections=[];self._stores=[];self._io={}
        self._emitted=False;self._unavailable=False;self._truncated=False;self._frozen=None;self._errors=()
        self._test_thread=threading.get_ident()  # Private ownership only; never serialized.

    def _note(self,callback,*args):
        try:callback(*args)
        except BaseException:self._unavailable=True

    def register_connection(self,connection):
        if not self._lock.acquire(False):self._unavailable=True;return
        try:
            if any(c is connection for c in self._connections):return
            if len(self._connections)<2:self._connections.append(connection)
            else:self._truncated=True
        finally:self._lock.release()

    def _code(self,exc):
        if type(exc) is AssertionError:return 'ASSERTION'
        if type(exc) in self._errors and type(exc.args) is tuple and len(exc.args)==1:return _enum(exc.args[0],_CODES)
        return 'OTHER'

    def _connection(self,connection,slot):
        try:
            if not connection.cv.acquire(False):return dict(busy=True)
            try:
                streams=[[k,v['opened'],v['grant'],v['sent']] for k,v in itertools.islice(connection.tx_streams.items(),2)]
                jobs=[[j['kind'],j['cls'],j['started'],_enum(j['error'],_CODES),int((j['deadline']-time.monotonic())*1000)] for j in itertools.islice(connection.outgoing,2)]
                return dict(slot=slot,closed=connection.closed,why=_enum(connection.error,_CODES),age_ms=int((time.monotonic()-connection.last_rx)*1000),q=len(connection.outgoing),qb=connection.queued_bytes,streams=streams,jobs=jobs,alive=[t.is_alive() for t in itertools.islice(connection.threads,5)])
            finally:connection.cv.release()
        except BaseException:return dict(unavailable=True)

    def snapshot(self):
        if not self._lock.acquire(False):return dict(observer='BUSY')
        try:
            connections=list(self._connections)
            stores=[{k:v for k,v in row.items() if k not in ('ref','since','budget_since')} for row in self._stores]
            now=time.monotonic()
            for row,original in zip(stores,self._stores):
                if original['held']:row['hold_ms']=int((now-original['since'])*1000)
                if original.get('budget_waiters',0):row['budget_ms']=int((now-original['budget_since'])*1000)
            io=[dict(row) for row in self._io.values()]
            state=dict(observer='UNAVAILABLE' if self._unavailable else 'OK',stage='SEND',stores=stores,io=io,truncated=self._truncated)
        finally:self._lock.release()
        state['connections']=[self._connection(c,i+1) for i,c in enumerate(connections)]
        return state

    def emit_failure(self,exc):
        if self._emitted:return
        self._emitted=True
        try:
            state=self._frozen[1] if self._frozen is not None and self._frozen[0] is exc else self.snapshot()
            line=format_failure(state,self._code(exc))
        except BaseException:line=PREFIX+'{"code":"DIAGNOSTIC_UNAVAILABLE","v":1}\n'
        try:
            writer=self._writer if self._writer is not None else sys.stderr.write
            writer(line)
        except BaseException:pass  # Never replace the original test failure.

    @contextlib.contextmanager
    def failure_boundary(self):
        try:yield
        except BaseException as exc:
            self.emit_failure(exc)
            raise

    def _store(self,store,phase,start):
        if not self._lock.acquire(False):self._unavailable=True;return
        try:
            row=next((r for r in self._stores if r['ref'] is store),None)
            if row is None:
                if len(self._stores)>=2:self._truncated=True;return
                row=dict(ref=store,phase='NONE',waiters=0,held=False,entry_ms=0,hold_ms=0,max_ms=0,n=0,since=start,budget_waiters=0,budget_ms=0,budget_since=start);self._stores.append(row)
            elapsed=int((time.monotonic()-start)*1000)
            if phase=='WAIT':
                row['waiters']+=1
                if not row['held']:row['phase']='WAIT'
                return
            if phase=='TX_ENTER_ERROR':
                row['waiters']=max(0,row['waiters']-1);row['n']+=1;row['max_ms']=max(row['max_ms'],elapsed)
                if not row['held']:row['phase']='WAIT' if row['waiters'] else 'TX_ERROR'
                return
            if phase=='TX_BODY':row['waiters']=max(0,row['waiters']-1);row['entry_ms']=elapsed;row['held']=True;row['since']=time.monotonic()
            if phase in ('TX_DONE','TX_ERROR'):row['held']=False;row['n']+=1;row['max_ms']=max(row['max_ms'],elapsed)
            row['phase']='WAIT' if not row['held'] and row['waiters'] else phase
        finally:self._lock.release()

    def _budget_event(self,store,active,start):
        if not self._lock.acquire(False):self._unavailable=True;return
        try:
            row=next((r for r in self._stores if r['ref'] is store),None)
            if row is None:
                if len(self._stores)>=2:self._truncated=True;return
                row=dict(ref=store,phase='NONE',waiters=0,held=False,entry_ms=0,hold_ms=0,max_ms=0,n=0,since=start,budget_waiters=0,budget_ms=0,budget_since=start);self._stores.append(row)
            if active:
                if not row['budget_waiters']:row['budget_since']=start
                row['budget_waiters']+=1
            else:
                row['budget_waiters']=max(0,row['budget_waiters']-1)
                row['budget_ms']=int((time.monotonic()-start)*1000)
        finally:self._lock.release()

    def _freeze(self,exc):
        # Only the test-thread send can own its pre-cleanup snapshot. Worker
        # errors still update bounded IO phases, but cannot replace this state.
        if threading.get_ident()==self._test_thread:self._frozen=(exc,self.snapshot())

    def _io_update(self,connection=None,sock=None,channel='control',**fields):
        if not self._lock.acquire(False):self._unavailable=True;return
        try:
            slot=next((i+1 for i,c in enumerate(self._connections) if c is connection),0);channel=_enum(channel,frozenset(('control','data')),default='control')
            if sock is not None:
                slot=0
                for i,c in enumerate(self._connections):
                    for name in ('control','data'):
                        if c.channels[name] is sock:slot=i+1;channel=name;break
                    if slot:break
            if not slot:return
            key=(slot,channel)
            row=self._io.setdefault(key,dict(slot=slot,channel=channel))
            for name,value in fields.items():
                if name=='write':row[name]=_enum(value,_KINDS)
                elif name=='read':row[name]=_enum(value,_PHASES)
                elif name=='error':row[name]=_enum(value,_CODES)
                elif name=='active':row[name]=_bool(value)
                elif name in ('n','remaining_ms','elapsed_ms'):row[name]=_int(value,9999999,-9999999 if name=='remaining_ms' else 0)
        finally:self._lock.release()

    @contextlib.contextmanager
    def observe(self,lan,budget):
        """Only the selected heartbeat case installs these test-process wrappers."""
        owner=self;self._errors=(lan.TransportError,budget.BudgetError)
        transaction=budget._Store.transaction;wait=budget.NodeBudget.wait_take
        send=lan.Connection._send;emit=lan.Connection._emit;read=lan._read_exact
        @contextlib.contextmanager
        def observed_transaction(store):
            start=time.monotonic();entered=False;owner._note(owner._store,store,'WAIT',start)
            try:
                with transaction(store) as con:
                    entered=True;owner._note(owner._store,store,'TX_BODY',start)
                    try:yield con
                    except BaseException:
                        owner._note(owner._store,store,'TX_ERROR_EXIT',start);raise
                    else:owner._note(owner._store,store,'TX_COMMIT',start)
                owner._note(owner._store,store,'TX_DONE',start)
            except BaseException:
                owner._note(owner._store,store,'TX_ERROR' if entered else 'TX_ENTER_ERROR',start);raise
        def observed_wait(store,*args,**kwargs):
            start=time.monotonic();owner._note(owner._budget_event,store,True,start)
            try:return wait(store,*args,**kwargs)
            finally:owner._note(owner._budget_event,store,False,start)
        def observed_send(connection,*args,**kwargs):
            owner._note(owner.register_connection,connection)
            try:return send(connection,*args,**kwargs)
            except BaseException as exc:
                owner._note(owner._freeze,exc)
                raise
        def observed_emit(connection,*args,**kwargs):
            owner._note(owner.register_connection,connection);start=time.monotonic()
            kind=_enum(args[0] if args else kwargs.get('kind'),_KINDS)
            traffic=_enum(args[2] if len(args)>2 else kwargs.get('cls'),frozenset(('control','live','bulk')))
            channel='data' if kind=='MUX_FRAGMENT' or kind=='APP' and traffic!='control' else 'control'
            owner._note(lambda:owner._io_update(connection=connection,channel=channel,write=kind,active=True))
            try:
                result=emit(connection,*args,**kwargs)
                owner._note(lambda:owner._io_update(connection=connection,channel=channel,active=False,elapsed_ms=int((time.monotonic()-start)*1000)));return result
            except BaseException as exc:
                owner._note(lambda:owner._io_update(connection=connection,channel=channel,active=False,error=owner._code(exc),elapsed_ms=int((time.monotonic()-start)*1000)));raise
        def observed_read(sock,n,deadline,*args,**kwargs):
            start=time.monotonic();phase='READ_1' if n==1 else 'READ_5' if n==5 else 'READ_OTHER'
            owner._note(lambda:owner._io_update(sock=sock,read=phase,n=n,remaining_ms=int((deadline-start)*1000)))
            try:
                result=read(sock,n,deadline,*args,**kwargs)
                owner._note(lambda:owner._io_update(sock=sock,read='READ_DONE',elapsed_ms=int((time.monotonic()-start)*1000)));return result
            except BaseException as exc:
                owner._note(lambda:owner._io_update(sock=sock,read='READ_ERROR',error=owner._code(exc),elapsed_ms=int((time.monotonic()-start)*1000)));raise
        with contextlib.ExitStack() as stack:
            for target,name,value in ((budget._Store,'transaction',observed_transaction),(budget.NodeBudget,'wait_take',observed_wait),(lan.Connection,'_send',observed_send),(lan.Connection,'_emit',observed_emit),(lan,'_read_exact',observed_read)):
                stack.enter_context(patch.object(target,name,value))
            yield self
