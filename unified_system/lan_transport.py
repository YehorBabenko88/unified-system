"""Identity-bound paired application channels, available only in isolation.

No OS/network changes, discovery scans, provider calls or production factory.
Existing SSH observation transport is deliberately separate and unchanged.
"""
from collections import deque
from dataclasses import dataclass
import hashlib
import ipaddress
import json
import math
import random
import socket
import ssl
import struct
import threading
import time
import uuid
from types import MappingProxyType
from .network_budget import BudgetError, NodeBudget, NODES

MAX_FRAME=65536
MAX_CONTROL=4096
WINDOW=65536
MAX_STREAMS=16
MAX_QUEUE=64
MAX_PEER_BYTES=1048576
MAX_NODE_BYTES=8388608
HEARTBEAT_INTERVAL=10
IDLE_TIMEOUT=30
_PREFIX=struct.Struct('!HI')
_ROLES={'control':'control','live':'ingestion','bulk':'storage'}


class TransportError(ValueError):
    pass


def _need(ok,code='PROTOCOL_REJECTED'):
    if not ok:
        raise TransportError(code)


def _pairs(pairs):
    out={}
    for k,v in pairs:
        _need(k not in out)
        out[k]=v
    return out


def _json(raw):
    try:
        return json.loads(raw,object_pairs_hook=_pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError()))
    except (ValueError,TypeError,RecursionError,UnicodeError):
        raise TransportError('PROTOCOL_REJECTED') from None


def _canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')


def _uuid(value):
    try:
        return type(value) is str and str(uuid.UUID(value))==value and uuid.UUID(value).version==4
    except (ValueError,TypeError,AttributeError):
        return False


@dataclass(frozen=True)
class Endpoint:
    address: str
    port: int
    priority: int
    transport: str


@dataclass(frozen=True)
class Peer:
    node_id: str
    enrollment_id: str
    fingerprints: tuple
    roles: tuple
    endpoints: tuple
    enabled: bool


@dataclass(frozen=True)
class PeerRegistry:
    cluster_id: str
    generation: int
    _peers: object
    digest: str

    @classmethod
    def from_document(cls,doc):
        try:return cls._validated(doc)
        except (TypeError,ValueError,RecursionError,KeyError) as exc:
            if isinstance(exc,TransportError):raise
            raise TransportError('REGISTRY_REJECTED') from None

    @classmethod
    def _validated(cls,doc):
        _need(len(_canonical(doc))<=65536,'REGISTRY_REJECTED')
        _need(type(doc) is dict and set(doc)=={'schema','cluster_id','generation','nodes'},'REGISTRY_REJECTED')
        _need(doc['schema']=='unified.lan-peer-registry.v1' and _uuid(doc['cluster_id']),'REGISTRY_REJECTED')
        _need(type(doc['generation']) is int and 1<=doc['generation']<2**63,'REGISTRY_REJECTED')
        _need(type(doc['nodes']) is list and len(doc['nodes'])==6,'REGISTRY_REJECTED')
        peers={};pins=set();enrollments=set()
        for row in doc['nodes']:
            _need(type(row) is dict and set(row)=={'node_id','enrollment_id','fingerprints','roles','endpoints','enabled'},'REGISTRY_REJECTED')
            node=row['node_id'];_need(type(node) is str and node in NODES and node not in peers,'REGISTRY_REJECTED')
            _need(_uuid(row['enrollment_id']) and row['enrollment_id'] not in enrollments,'REGISTRY_REJECTED')
            enrollments.add(row['enrollment_id'])
            fps=row['fingerprints'];roles=row['roles']
            _need(type(fps) is list and 1<=len(fps)<=2 and len(set(fps))==len(fps),'REGISTRY_REJECTED')
            for pin in fps:
                _need(type(pin) is str and len(pin)==64 and all(c in '0123456789abcdef' for c in pin) and pin not in pins,'REGISTRY_REJECTED')
                pins.add(pin)
            _need(type(roles) is list and 1<=len(roles)<=3 and len(set(roles))==len(roles) and set(roles)<={'control','ingestion','storage'},'REGISTRY_REJECTED')
            _need(type(row['enabled']) is bool and type(row['endpoints']) is list and 1<=len(row['endpoints'])<=4,'REGISTRY_REJECTED')
            endpoints=[]
            for ep in row['endpoints']:
                _need(type(ep) is dict and set(ep)=={'address','port','priority','transport'},'REGISTRY_REJECTED')
                try: address=ipaddress.ip_address(ep['address'])
                except (ValueError,TypeError): raise TransportError('REGISTRY_REJECTED') from None
                _need(str(address)==ep['address'] and not(address.is_unspecified or address.is_multicast or address.is_link_local),'REGISTRY_REJECTED')
                _need(ep['transport'] in ('lan','tailscale') and type(ep['port']) is int and 1<=ep['port']<=65535,'REGISTRY_REJECTED')
                _need(type(ep['priority']) is int and 0<=ep['priority']<=100,'REGISTRY_REJECTED')
                endpoints.append(Endpoint(**ep))
            peers[node]=Peer(node,row['enrollment_id'],tuple(fps),tuple(roles),tuple(sorted(endpoints,key=lambda e:(e.transport!='lan',e.priority))),row['enabled'])
        return cls(doc['cluster_id'],doc['generation'],MappingProxyType(peers),hashlib.sha256(_canonical(doc)).hexdigest())

    def peer(self,node):
        _need(node in self._peers and self._peers[node].enabled,'PEER_NOT_ADMITTED')
        return self._peers[node]

    def authenticate(self,tls,expected=None):
        _need(tls.selected_alpn_protocol()=='unified-lan-v1','AUTH_REJECTED')
        cert=tls.getpeercert();der=tls.getpeercert(binary_form=True)
        _need(type(cert) is dict and type(der) is bytes and bool(der),'AUTH_REJECTED')
        pin=hashlib.sha256(der).hexdigest()
        uris=[v for k,v in cert.get('subjectAltName',()) if k=='URI']
        matches=[p.node_id for p in self._peers.values() if p.enabled and pin in p.fingerprints
                 and uris==['urn:unified:'+self.cluster_id+':'+p.node_id]]
        _need(len(matches)==1 and (expected is None or matches[0]==expected),'AUTH_REJECTED')
        return matches[0]


def tls_context(ca,cert,key,*,server=False):
    purpose=ssl.Purpose.CLIENT_AUTH if server else ssl.Purpose.SERVER_AUTH
    ctx=ssl.create_default_context(purpose=purpose,cafile=str(ca))
    ctx.check_hostname=False
    ctx.verify_mode=ssl.CERT_REQUIRED
    ctx.minimum_version=ssl.TLSVersion.TLSv1_2
    ctx.options|=ssl.OP_NO_COMPRESSION
    ctx.load_cert_chain(str(cert),str(key))
    ctx.set_alpn_protocols(['unified-lan-v1'])
    return ctx


class ReconnectPolicy:
    def __init__(self,seed=None): self.random=random.Random(seed)
    def delay(self,attempt):
        _need(type(attempt) is int and attempt>=0)
        return self.random.uniform(0,min(30,.25*2**min(attempt,10)))
    def retryable(self,code): return code in ('DISCONNECTED','DEADLINE','CONNECTING')


class _Memory:
    def __init__(self): self.used=0;self.lock=threading.Lock()
    def take(self,n):
        with self.lock:
            if self.used+n>MAX_NODE_BYTES:return False
            self.used+=n;return True
    def release(self,n):
        with self.lock:
            self.used-=n
            assert self.used>=0


def _read_exact(sock,n,deadline,on_idle=None):
    out=bytearray()
    while len(out)<n:
        remaining=deadline-time.monotonic()
        if remaining<=0 and not out and on_idle is not None and on_idle():
            deadline=time.monotonic()+IDLE_TIMEOUT;remaining=IDLE_TIMEOUT
        _need(remaining>0,'DEADLINE')
        sock.settimeout(min(remaining,.25))
        try: chunk=sock.recv(n-len(out))
        except socket.timeout: continue
        _need(bool(chunk),'DISCONNECTED');out.extend(chunk)
    return bytes(out)


def _read_frame(sock,budget,peer,deadline,on_idle=None):
    hsize,size=_PREFIX.unpack(_read_exact(sock,_PREFIX.size,deadline,on_idle))
    _need(1<=hsize<=MAX_CONTROL and 0<=size<=MAX_FRAME,'FRAME_BOUNDS')
    body_deadline=time.monotonic()+5 if on_idle is not None else min(deadline,time.monotonic()+5)
    header=_json(_read_exact(sock,hsize,body_deadline))
    _need(type(header) is dict and set(header)=={'kind','stream','traffic_class','message_id','value'},'PROTOCOL_REJECTED')
    _need(type(header['traffic_class']) is str and header['traffic_class'] in _ROLES and type(header['stream']) is int and 0<=header['stream']<=MAX_STREAMS)
    _need(header['kind'] in ('HELLO','OPEN','CREDIT','APP','PING','PONG') and type(header['value']) is int and 0<=header['value']<2**63)
    _need(_uuid(header['message_id']))
    _need(header['traffic_class']!='control' or size<=MAX_CONTROL,'FRAME_BOUNDS')
    _need(header['kind'] not in ('OPEN','CREDIT','PING','PONG') or size==0,'FRAME_BOUNDS')
    budget.wait_take('rx',peer,header['traffic_class'],_PREFIX.size+hsize+size,deadline=body_deadline)
    payload=_read_exact(sock,size,body_deadline)
    return header,payload


def _write_frame(sock,lock,budget,peer,kind,stream,traffic_class,payload,value,deadline,cancel=None,message_id=None):
    header=_canonical(dict(kind=kind,stream=stream,traffic_class=traffic_class,message_id=message_id or str(uuid.uuid4()),value=value))
    _need(len(header)<=MAX_CONTROL and len(payload)<=MAX_FRAME,'FRAME_BOUNDS')
    raw=_PREFIX.pack(len(header),len(payload))+header+payload
    budget.wait_take('tx',peer,traffic_class,len(raw),deadline=deadline,cancel=cancel)
    with lock:
        _need(time.monotonic()<deadline,'DEADLINE')
        # SSL socket timeouts are configured by reader too; non-overlapping
        # channels keep payload writes serialized, each send has a total bound.
        offset=0
        while offset<len(raw):
            _need(time.monotonic()<deadline,'DELIVERY_UNKNOWN')
            if cancel is not None and cancel.is_set(): raise TransportError('DELIVERY_UNKNOWN')
            try: sent=sock.send(raw[offset:])
            except socket.timeout: continue
            _need(sent>0,'DELIVERY_UNKNOWN');offset+=sent


@dataclass(frozen=True)
class Delivery:
    peer_id: str
    stream_id: int
    traffic_class: str
    message_id: str
    payload: bytes


class Connection:
    def __init__(self,owner,peer,nonce,channels):
        self.owner,self.peer_id,self.nonce=owner,peer,nonce
        self.admitted_peer=owner.registry.peer(peer);self.admitted_local=owner.registry.peer(owner.node_id)
        self.channels=channels;self.locks={k:threading.Lock() for k in channels}
        self.cv=threading.Condition(threading.RLock());self.closed=False;self.error=None
        self.closed_event=threading.Event();self.created_at=time.monotonic()
        self.last_rx=self.created_at
        self.outgoing=deque();self.incoming=deque();self.queued_bytes=0
        self.tx_streams={};self.rx_streams={};self.reserved=0;self.control_held=0
        self.threads=[]
        for name in ('control','data'):
            thread=threading.Thread(target=self._reader,args=(name,),daemon=True)
            self.threads.append(thread);thread.start()
        for control_only in (True,False):
            thread=threading.Thread(target=self._sender,args=(control_only,),daemon=True);self.threads.append(thread);thread.start()
        thread=threading.Thread(target=self._heartbeat,daemon=True);self.threads.append(thread);thread.start()

    def _heartbeat(self):
        try:
            while not self.closed_event.wait(HEARTBEAT_INTERVAL):
                self._emit('PING',0,'control')
        except (OSError,ValueError) as exc:self.close(str(exc))

    def _current(self):
        _need(not self.closed,'DISCONNECTED')
        registry=self.owner.registry
        _need(registry.peer(self.peer_id)==self.admitted_peer and registry.peer(self.owner.node_id)==self.admitted_local,'POLICY_REVOKED')

    def _emit(self,kind,stream,cls,payload=b'',value=0,*,deadline=None,cancel=None,message_id=None):
        self._current();channel='data' if kind=='APP' and cls!='control' else 'control'
        _write_frame(self.channels[channel],self.locks[channel],self.owner.budget,self.peer_id,
                     kind,stream,cls,payload,value,deadline or time.monotonic()+5,cancel,message_id)

    def send(self,payload,traffic_class='live',*,stream_id=None,deadline=None,cancel=None):
        _need(type(payload) is bytes and 1<=len(payload)<=(MAX_CONTROL if traffic_class=='control' else MAX_FRAME),'FRAME_BOUNDS')
        _need(traffic_class in _ROLES and _ROLES[traffic_class] in self.owner.registry.peer(self.owner.node_id).roles,'CLASS_NOT_ADMITTED')
        stream=0 if traffic_class=='control' else (stream_id or (1 if traffic_class=='live' else 2))
        _need(type(stream) is int and ((traffic_class=='control' and stream==0) or 1<=stream<=MAX_STREAMS))
        deadline=time.monotonic()+5 if deadline is None else deadline
        _need(type(deadline) in (int,float) and math.isfinite(deadline) and deadline>time.monotonic(),'DEADLINE')
        if cancel is not None and cancel.is_set():raise TransportError('CANCELLED')
        job=dict(payload=payload,cls=traffic_class,stream=stream,deadline=deadline,cancel=cancel,
                 done=threading.Event(),error=None,started=False,id=str(uuid.uuid4()))
        with self.cv:
            self._current()
            prior=self.tx_streams.get(stream)
            _need(prior is None or prior['cls']==traffic_class,'STREAM_CLASS_CHANGED')
            while len(self.outgoing)>=MAX_QUEUE or self.queued_bytes+len(payload)>MAX_PEER_BYTES or not self.owner.memory.take(len(payload)):
                if cancel is not None and cancel.is_set():raise TransportError('CANCELLED')
                _need(time.monotonic()<deadline,'OVERLOADED')
                self.cv.wait(.01);self._current()
            # Capacity wait releases cv; another sender may have opened this
            # stream in the meantime. Never replace its cumulative credit state.
            prior=self.tx_streams.get(stream)
            if prior is not None and prior['cls']!=traffic_class:
                self.owner.memory.release(len(payload));raise TransportError('STREAM_CLASS_CHANGED')
            self.outgoing.append(job);self.queued_bytes+=len(payload)
            if stream:
                if prior is None:self.tx_streams[stream]=dict(cls=traffic_class,grant=0,sent=0,opened=False)
            self.cv.notify_all()
        while not job['done'].wait(.01):
            if time.monotonic()>=deadline or cancel is not None and cancel.is_set():
                with self.cv:
                    job['error']='DELIVERY_UNKNOWN' if job['started'] else ('CANCELLED' if cancel is not None and cancel.is_set() else 'DEADLINE')
                    self.cv.notify_all()
                # Worker owns release even if this caller times out.
                raise TransportError(job['error'])
        if job['error']:raise TransportError(job['error'])
        return job['id']

    def _sender(self,control_only):
        try:
            while True:
                with self.cv:
                    if self.closed:return
                    job=None;open_stream=None
                    candidates=(j for j in self.outgoing if (j['cls']=='control')==control_only)
                    for candidate in sorted(candidates,key=lambda j:('control','live','bulk').index(j['cls'])):
                        if candidate['error'] or time.monotonic()>=candidate['deadline'] or candidate['cancel'] is not None and candidate['cancel'].is_set():
                            job=candidate;break
                        stream=self.tx_streams.get(candidate['stream'])
                        if stream and not stream['opened']:
                            stream['opened']=True;open_stream=(candidate['stream'],stream['cls']);break
                        if stream and stream['sent']+len(candidate['payload'])>stream['grant']:continue
                        job=candidate;break
                    if open_stream is None and job is None:self.cv.wait(.01);continue
                    if job:
                        self.outgoing.remove(job)
                        if job['cancel'] is not None and job['cancel'].is_set():job['error']='CANCELLED'
                        if not job['error'] and time.monotonic()<job['deadline']:
                            job['started']=True
                            if job['stream']:self.tx_streams[job['stream']]['sent']+=len(job['payload'])
                        else:job['error']=job['error'] or 'DEADLINE'
                if open_stream:
                    self._emit('OPEN',open_stream[0],'control',value={'live':1,'bulk':2}[open_stream[1]])
                    continue
                try:
                    if not job['error']:
                        self._emit('APP',job['stream'],job['cls'],job['payload'],deadline=job['deadline'],cancel=job['cancel'],message_id=job['id'])
                except (OSError,ValueError) as exc:
                    job['error']='DELIVERY_UNKNOWN';self.close(str(exc))
                finally:
                    with self.cv:
                        self.queued_bytes-=len(job['payload']);self.owner.memory.release(len(job['payload']))
                        job['done'].set();self.cv.notify_all()
        except (OSError,ValueError) as exc:self.close(str(exc))

    def _reader(self,channel):
        try:
            while not self.closed:
                h,payload=_read_frame(self.channels[channel],self.owner.budget,self.peer_id,time.monotonic()+IDLE_TIMEOUT,
                                      on_idle=lambda:time.monotonic()-self.last_rx<IDLE_TIMEOUT)
                self.last_rx=time.monotonic()
                self._current();kind=h['kind'];stream=h['stream'];cls=h['traffic_class']
                if kind in ('PING','PONG'):
                    _need(channel=='control' and cls=='control' and stream==0 and h['value']==0 and not payload)
                    if kind=='PING':self._emit('PONG',0,'control')
                elif kind=='OPEN':
                    _need(channel=='control' and cls=='control' and not payload and 1<=stream<=MAX_STREAMS and h['value'] in (1,2))
                    stream_class='live' if h['value']==1 else 'bulk'
                    _need(_ROLES[stream_class] in self.owner.registry.peer(self.peer_id).roles,'CLASS_NOT_ADMITTED')
                    with self.cv:
                        self._current()
                        _need(stream not in self.rx_streams and len(self.rx_streams)<MAX_STREAMS)
                        _need(self.owner.memory.take(WINDOW),'OVERLOADED')
                        self.reserved+=WINDOW;self.rx_streams[stream]=dict(cls=stream_class,grant=WINDOW,received=0)
                    self._emit('CREDIT',stream,'control',value=WINDOW)
                elif kind=='CREDIT':
                    _need(channel=='control' and cls=='control' and not payload)
                    with self.cv:
                        self._current()
                        s=self.tx_streams.get(stream);_need(s is not None)
                        if h['value']>s['grant']:
                            _need(h['value']-s['sent']<=WINDOW,'CREDIT_BOUNDS')
                            s['grant']=h['value']
                        self.cv.notify_all()
                else:
                    _need(kind=='APP' and h['value']==0 and len(payload)>0)
                    _need(_ROLES[cls] in self.owner.registry.peer(self.peer_id).roles,'CLASS_NOT_ADMITTED')
                    with self.cv:
                        self._current()
                        _need(len(self.incoming)<MAX_QUEUE,'OVERLOADED')
                        if channel=='control':
                            _need(cls=='control' and stream==0 and len(payload)<=MAX_CONTROL)
                            _need(self.control_held+len(payload)<=65536 and self.owner.memory.take(len(payload)),'OVERLOADED')
                            self.control_held+=len(payload)
                        else:
                            s=self.rx_streams.get(stream)
                            _need(s is not None and s['cls']==cls and s['received']+len(payload)<=s['grant'],'CREDIT_BOUNDS')
                            s['received']+=len(payload)
                        self.incoming.append(Delivery(self.peer_id,stream,cls,h['message_id'],payload));self.cv.notify_all()
        except (OSError,ValueError) as exc:self.close(str(exc))

    def receive(self,*,deadline=None,cancel=None):
        deadline=time.monotonic()+5 if deadline is None else deadline
        with self.cv:
            while not self.incoming:
                self._current()
                if cancel is not None and cancel.is_set():raise TransportError('CANCELLED')
                _need(time.monotonic()<deadline,'DEADLINE');self.cv.wait(.01)
            self._current()
            delivery=min(self.incoming,key=lambda d:('control','live','bulk').index(d.traffic_class))
            self.incoming.remove(delivery)
            if delivery.stream_id:
                stream=self.rx_streams[delivery.stream_id];stream['grant']+=len(delivery.payload);grant=stream['grant']
            else:
                self.control_held-=len(delivery.payload);self.owner.memory.release(len(delivery.payload));grant=None
        if grant is not None:self._emit('CREDIT',delivery.stream_id,'control',value=grant)
        return delivery

    def close(self,reason='CLOSED'):
        with self.cv:
            if self.closed:return
            self.closed=True;self.error=reason;self.closed_event.set()
            for job in self.outgoing:
                job['error']='DISCONNECTED';job['done'].set()
                self.owner.memory.release(len(job['payload']));self.queued_bytes-=len(job['payload'])
            self.outgoing.clear();self.incoming.clear()
            self.owner.memory.release(self.reserved+self.control_held);self.reserved=self.control_held=0
            self.cv.notify_all()
        for sock in self.channels.values():
            try:sock.shutdown(socket.SHUT_RDWR)
            except OSError:pass
            sock.close()


class LanTransport:
    @classmethod
    def runtime(cls,*args,**kwargs):
        raise TransportError('NATIVE_RUNTIME_ADMISSION_REQUIRED')

    @classmethod
    def isolated(cls,node,registry,*,client_context,server_context,budget):
        return cls(node,registry,client_context,server_context,budget)

    def __init__(self,node,registry,client_context,server_context,budget):
        _need(isinstance(registry,PeerRegistry) and isinstance(budget,NodeBudget) and budget.node==node)
        registry.peer(node)
        for ctx in (client_context,server_context):
            _need(isinstance(ctx,ssl.SSLContext) and ctx.verify_mode==ssl.CERT_REQUIRED and ctx.minimum_version>=ssl.TLSVersion.TLSv1_2,'TLS_POLICY_REJECTED')
        self.node_id,self.registry,self.client_context,self.server_context,self.budget=node,registry,client_context,server_context,budget
        self.memory=_Memory();self.lock=threading.RLock();self.connecting=set();self.connections={}
        self.auth_failures={};self.retry_counts={}
        self.attempts=threading.BoundedSemaphore(2);self.listener=None;self.accept_lock=threading.Lock()

    def listen(self,address='127.0.0.1',port=0):
        _need(ipaddress.ip_address(address).is_loopback,'ISOLATION_BOUNDARY')
        _need(self.listener is None)
        sock=socket.socket(socket.AF_INET6 if ':' in address else socket.AF_INET,socket.SOCK_STREAM)
        sock.bind((address,port));sock.listen(12);self.listener=sock
        return sock.getsockname()[1]

    def update_registry(self,new):
        _need(isinstance(new,PeerRegistry) and new.cluster_id==self.registry.cluster_id and new.generation>self.registry.generation,'REGISTRY_ROLLBACK')
        with self.lock:
            old=self.registry;self.registry=new
            for peer,c in self.connections.items():
                if old._peers.get(peer)!=new._peers.get(peer) or old._peers.get(self.node_id)!=new._peers.get(self.node_id):c.close('POLICY_REVOKED')

    def _hello(self,tls,peer,channel,nonce,deadline,*,receive_first=False):
        def send():
            payload=_canonical(dict(node=self.node_id,peer=peer,channel=channel,nonce=nonce,version=1))
            _write_frame(tls,threading.Lock(),self.budget,peer,'HELLO',0,'control',payload,0,deadline)
        if not receive_first:send()
        header,raw=_read_frame(tls,self.budget,peer,deadline)
        doc=_json(raw)
        _need(header['kind']=='HELLO' and header['stream']==0 and header['traffic_class']=='control' and header['value']==0 and len(raw)<=MAX_CONTROL)
        _need(doc==dict(node=peer,peer=self.node_id,channel=channel,nonce=nonce,version=1),'SESSION_BINDING_REJECTED')
        if receive_first:send()

    def connect(self,peer,*,deadline=None,cancel=None):
        deadline=time.monotonic()+5 if deadline is None else deadline
        _need(type(deadline) in (int,float) and math.isfinite(deadline),'DEADLINE')
        deadline=min(deadline,time.monotonic()+5)
        with self.lock:
            old=self.connections.get(peer)
            if old is not None and not old.closed:return old
            _need(self.auth_failures.get(peer)!=self.registry.digest,'AUTH_REJECTED')
            _need(peer!=self.node_id and peer not in self.connecting,'CONNECTING')
            entry=self.registry.peer(peer)
            admitted=self.registry
            _need(len([c for c in self.connections.values() if not c.closed])<5,'CONNECTION_LIMIT')
            self.connecting.add(peer)
        channels={};raw=None;acquired=False
        try:
            acquired=self.attempts.acquire(timeout=max(0,deadline-time.monotonic()))
            _need(acquired,'DEADLINE');nonce=str(uuid.uuid4())
            ep=entry.endpoints[0]
            _need(ipaddress.ip_address(ep.address).is_loopback,'ISOLATION_BOUNDARY')
            for name in ('control','data'):
                if cancel is not None and cancel.is_set():raise TransportError('CANCELLED')
                _need(time.monotonic()<deadline,'DEADLINE')
                raw=socket.create_connection((ep.address,ep.port),timeout=max(.001,deadline-time.monotonic()))
                tls=self.client_context.wrap_socket(raw,server_hostname=None);raw=None
                channels[name]=tls;admitted.authenticate(tls,peer)
                self._hello(tls,peer,name,nonce,deadline)
            with self.lock:
                _need(self.registry.digest==admitted.digest,'POLICY_REVOKED')
                for tls in channels.values():self.registry.authenticate(tls,peer)
                connection=Connection(self,peer,nonce,channels);self.connections[peer]=connection
            return connection
        except ssl.SSLError as exc:
            self.auth_failures[peer]=self.registry.digest
            raise TransportError('AUTH_REJECTED') from exc
        except TransportError as exc:
            if str(exc)=='AUTH_REJECTED':self.auth_failures[peer]=self.registry.digest
            raise
        except (OSError,BudgetError) as exc:
            raise TransportError('DISCONNECTED') from exc
        finally:
            with self.lock:self.connecting.discard(peer)
            if acquired:self.attempts.release()
            if peer not in self.connections or self.connections[peer].channels is not channels:
                for sock in channels.values():sock.close()
            if raw is not None:raw.close()

    def accept(self,*,deadline=None):
        _need(self.listener is not None)
        deadline=time.monotonic()+5 if deadline is None else deadline
        channels={};identity=None;nonce=None;raw=None
        with self.accept_lock:
            with self.lock:admitted=self.registry
            try:
                for expected in ('control','data'):
                    self.listener.settimeout(max(.001,deadline-time.monotonic()))
                    raw,_=self.listener.accept();raw.settimeout(max(.001,deadline-time.monotonic()))
                    tls=self.server_context.wrap_socket(raw,server_side=True);raw=None
                    channels[expected]=tls;peer=admitted.authenticate(tls)
                    h,payload=_read_frame(tls,self.budget,peer,deadline);hello=_json(payload)
                    _need(type(hello) is dict and set(hello)=={'node','peer','channel','nonce','version'})
                    _need(h['kind']=='HELLO' and h['traffic_class']=='control' and h['stream']==0 and h['value']==0)
                    _need(hello['node']==peer and hello['peer']==self.node_id and hello['channel']==expected and hello['version']==1 and _uuid(hello['nonce']),'SESSION_BINDING_REJECTED')
                    if identity is None:identity,nonce=peer,hello['nonce']
                    _need(identity==peer and nonce==hello['nonce'],'SESSION_BINDING_REJECTED')
                    reply=_canonical(dict(node=self.node_id,peer=peer,channel=expected,nonce=nonce,version=1))
                    _write_frame(tls,threading.Lock(),self.budget,peer,'HELLO',0,'control',reply,0,deadline)
                with self.lock:
                    _need(self.registry.digest==admitted.digest,'POLICY_REVOKED')
                    for tls in channels.values():self.registry.authenticate(tls,identity)
                    _need(identity not in self.connections or self.connections[identity].closed,'DUPLICATE_CONNECTION')
                    _need(len([c for c in self.connections.values() if not c.closed])<5,'CONNECTION_LIMIT')
                    connection=Connection(self,identity,nonce,channels);self.connections[identity]=connection
                return connection
            except ssl.SSLError as exc:raise TransportError('AUTH_REJECTED') from exc
            except (OSError,BudgetError) as exc:raise TransportError('DISCONNECTED') from exc
            finally:
                if identity not in self.connections or self.connections[identity].channels is not channels:
                    for sock in channels.values():sock.close()
                if raw is not None:raw.close()

    def connect_with_retry(self,peer,*,deadline,cancel=None,policy=None):
        policy=policy or ReconnectPolicy();attempt=self.retry_counts.get(peer,0)
        old=self.connections.get(peer)
        if old is not None and time.monotonic()-old.created_at>=60:attempt=0
        while time.monotonic()<deadline:
            try:return self.connect(peer,deadline=min(deadline,time.monotonic()+5),cancel=cancel)
            except TransportError as exc:
                if not policy.retryable(str(exc)):raise
                wait=min(policy.delay(attempt),max(0,deadline-time.monotonic()));attempt+=1;self.retry_counts[peer]=attempt
                if cancel is not None:
                    if cancel.wait(wait):raise TransportError('CANCELLED')
                else:time.sleep(wait)
        raise TransportError('DEADLINE')

    def close(self):
        if self.listener is not None:self.listener.close();self.listener=None
        for connection in list(self.connections.values()):connection.close()
