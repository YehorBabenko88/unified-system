"""Bounded explicit LAN Mux fragmentation; never logical admission authority.

New record negotiation is separate from legacy APP. Headers are bindings only;
A2 must supply committed connection/stream admission before channel construction.
"""
from dataclasses import dataclass
import hashlib
import struct
import uuid
from .lan_transport import TransportError, _uuid

HEADER=struct.Struct('!4sBBH16s16sQ16s16s32sIIII32s')
CHUNK_SIZE=65536-HEADER.size
MESSAGE_LIMITS={1:16384,2:133120,3:133128,4:2097152}


class MuxError(TransportError):
    pass


def _need(value,code='MUX_FRAGMENT_REJECTED'):
    if not value:raise MuxError(code)


def _id(value):
    _need(_uuid(value),'MUX_BINDING_REJECTED')
    return uuid.UUID(value).bytes


@dataclass(frozen=True)
class MuxBinding:
    connection_id: str
    epoch: int
    stream_attempt_id: str
    profile_sha256: str

    def __post_init__(self):
        _id(self.connection_id);_id(self.stream_attempt_id)
        _need(type(self.epoch) is int and 1<=self.epoch<2**63,'MUX_BINDING_REJECTED')
        _need(type(self.profile_sha256) is str and len(self.profile_sha256)==64
              and all(c in '0123456789abcdef' for c in self.profile_sha256),'MUX_BINDING_REJECTED')


@dataclass(frozen=True)
class Fragment:
    kind: int
    transfer_id: str
    total: int
    index: int
    count: int
    digest: bytes
    chunk: bytes


def _shape(kind,total,index,count,chunk_length):
    _need(type(kind) is int and kind in MESSAGE_LIMITS)
    _need(type(total) is int and 1<=total<=MESSAGE_LIMITS[kind],'MUX_MESSAGE_BOUNDS')
    expected_count=(total+CHUNK_SIZE-1)//CHUNK_SIZE
    _need(type(count) is int and count==expected_count)
    _need(type(index) is int and 0<=index<count)
    expected_length=min(CHUNK_SIZE,total-index*CHUNK_SIZE)
    _need(type(chunk_length) is int and chunk_length==expected_length)


def encode_fragment(binding,nonce,transfer_id,kind,total,index,digest,chunk):
    _need(type(binding) is MuxBinding)
    _need(type(chunk) is bytes and type(digest) is bytes and len(digest)==32)
    count=(total+CHUNK_SIZE-1)//CHUNK_SIZE if type(total) is int else 0
    _shape(kind,total,index,count,len(chunk))
    raw=HEADER.pack(b'MXF1',1,kind,0,_id(nonce),_id(binding.connection_id),binding.epoch,
                    _id(binding.stream_attempt_id),_id(transfer_id),bytes.fromhex(binding.profile_sha256),
                    total,index,count,len(chunk),digest)+chunk
    _need(len(raw)<=65536)
    return raw


def decode_fragment(raw,binding,nonce,expected_kinds):
    _need(type(binding) is MuxBinding)
    _need(type(raw) is bytes and HEADER.size<len(raw)<=65536)
    _need(type(expected_kinds) in (set,frozenset) and bool(expected_kinds)
          and all(type(k) is int and k in MESSAGE_LIMITS for k in expected_kinds),'MUX_KIND_POLICY_REJECTED')
    (magic,version,kind,flags,session,connection,epoch,attempt,transfer,profile,
     total,index,count,chunk_length,digest)=HEADER.unpack(raw[:HEADER.size])
    _need(magic==b'MXF1' and version==1 and flags==0 and kind in expected_kinds)
    _need(session==_id(nonce) and connection==_id(binding.connection_id) and epoch==binding.epoch
          and attempt==_id(binding.stream_attempt_id) and profile==bytes.fromhex(binding.profile_sha256),'MUX_BINDING_REJECTED')
    _shape(kind,total,index,count,chunk_length)
    _need(len(raw)==HEADER.size+chunk_length)
    transfer_id=str(uuid.UUID(bytes=transfer));_id(transfer_id)
    return Fragment(kind,transfer_id,total,index,count,digest,raw[HEADER.size:])

import time


@dataclass(frozen=True)
class MuxMessage:
    kind: int
    transfer_id: str
    payload: bytes


class Reassembler:
    """Single ordered transfer; reserve peak bytes in the EXISTING node pool."""
    def __init__(self,binding,nonce,memory,expected_kinds,*,clock=time.monotonic):
        _need(type(binding) is MuxBinding);_id(nonce)
        _need(type(expected_kinds) in (set,frozenset) and expected_kinds
              and all(type(k) is int and k in MESSAGE_LIMITS for k in expected_kinds))
        self.binding,self.nonce,self.memory,self.expected_kinds=binding,nonce,memory,frozenset(expected_kinds)
        self.clock=clock;self.closed=False;self.active=None;self.buffer=None;self.completed=None
        self.next_index=0;self.deadline=None;self.reserved=0

    def close(self):
        self.closed=True;self.active=None;self.buffer=None;self.completed=None;self.deadline=None
        if self.reserved:self.memory.release(self.reserved);self.reserved=0

    def check_deadline(self):
        _need(not self.closed,'MUX_CLOSED')
        if self.deadline is not None and self.clock()>=self.deadline:
            self.close();raise MuxError('MUX_ASSEMBLY_DEADLINE')

    def push(self,raw):
        try:
            self.check_deadline();_need(self.completed is None,'MUX_QUEUE_FULL')
            part=decode_fragment(raw,self.binding,self.nonce,self.expected_kinds)
            identity=(part.kind,part.transfer_id,part.total,part.count,part.digest)
            if self.active is None:
                _need(part.index==0)
                _need(self.memory.take(2*part.total),'MUX_MEMORY_LIMIT')
                self.reserved=2*part.total
                self.active=identity;self.deadline=self.clock()+(60 if part.kind==4 else 10)
                self.buffer=bytearray(part.total);self.next_index=0
            _need(identity==self.active and part.index==self.next_index)
            offset=part.index*CHUNK_SIZE;self.buffer[offset:offset+len(part.chunk)]=part.chunk
            self.next_index+=1
            if self.next_index==part.count:
                _need(hashlib.sha256(self.buffer).digest()==part.digest,'MUX_MESSAGE_HASH_REJECTED')
                self.completed=MuxMessage(part.kind,part.transfer_id,bytes(self.buffer))
                self.active=None;self.buffer=None;self.deadline=None
        except (TransportError,MemoryError):
            self.close();raise

    def pop(self):
        self.check_deadline()
        if self.completed is None:return None
        result=self.completed;self.completed=None
        self.memory.release(self.reserved);self.reserved=0
        return result

import math
import threading
from .lan_transport import Connection, MUX_PROTOCOL


class LanMuxChannel:
    """Real negotiated socket adapter; isolated factory supplies NO A2 authority."""
    @classmethod
    def runtime(cls,*args,**kwargs):
        raise MuxError('NATIVE_MUX_ADMISSION_REQUIRED')

    @classmethod
    def isolated(cls,connection,binding,*,allowed_send_kinds,expected_receive_kinds):
        return cls(connection,binding,allowed_send_kinds,expected_receive_kinds)

    def __init__(self,connection,binding,allowed_send_kinds,expected_receive_kinds):
        _need(isinstance(connection,Connection) and connection.owner.application_protocol==MUX_PROTOCOL,'MUX_NOT_NEGOTIATED')
        _need(type(binding) is MuxBinding)
        _need(type(allowed_send_kinds) in (set,frozenset) and allowed_send_kinds
              and all(type(k) is int and k in MESSAGE_LIMITS for k in allowed_send_kinds),'MUX_KIND_POLICY_REJECTED')
        self.connection,self.binding=connection,binding
        self.allowed_send_kinds=frozenset(allowed_send_kinds)
        self.cv=threading.Condition(threading.RLock());self.send_lock=threading.Lock()
        self.closed=False;self.error=None;self.closed_event=threading.Event()
        self.rx=Reassembler(binding,connection.nonce,connection.owner.memory,expected_receive_kinds)
        with connection.cv:
            connection._current();_need(not hasattr(connection,'_mux_channel'),'MUX_WRAPPER_ALREADY_BOUND')
            connection._mux_channel=self
        self.thread=threading.Thread(target=self._reader,name='lan-mux-reassembly',daemon=True);self.thread.start()

    def _abort(self,reason):
        with self.cv:
            if self.closed:return
            self.closed=True;self.error=reason;self.rx.close();self.closed_event.set();self.cv.notify_all()
        self.connection.close(reason)

    def close(self):
        self._abort('MUX_CLOSED')
        if threading.current_thread() is not self.thread:self.thread.join(2)

    def _current(self):
        _need(not self.closed,self.error or 'MUX_CLOSED')
        self.connection._current()

    @staticmethod
    def _deadline(deadline,default):
        value=time.monotonic()+default if deadline is None else deadline
        _need(type(value) in (int,float) and math.isfinite(value) and value>time.monotonic(),'MUX_DEADLINE')
        return value

    def _reader(self):
        try:
            while True:
                with self.cv:
                    self._current()
                    while self.rx.completed is not None:
                        self.cv.wait(.01);self._current()
                    self.rx.check_deadline()
                    deadline=min(time.monotonic()+.1,self.rx.deadline or float('inf'))
                try:delivery=self.connection.receive_mux_fragment(deadline=deadline)
                except TransportError as exc:
                    if str(exc)=='DEADLINE':
                        with self.cv:self.rx.check_deadline()
                        continue
                    raise
                with self.cv:
                    self._current();self.rx.push(delivery.payload);self.cv.notify_all()
        except (TransportError,MemoryError) as exc:self._abort(str(exc) or 'MUX_MEMORY_LIMIT')

    def send(self,kind,payload,*,deadline=None,cancel=None):
        _need(type(kind) is int and kind in self.allowed_send_kinds,'MUX_KIND_POLICY_REJECTED')
        _need(type(payload) is bytes and 1<=len(payload)<=MESSAGE_LIMITS[kind],'MUX_MESSAGE_BOUNDS')
        deadline=self._deadline(deadline,60 if kind==4 else 10)
        if cancel is not None and cancel.is_set():raise MuxError('CANCELLED')
        acquired=False;reserved=False;attempted=False
        try:
            while not acquired:
                self._current()
                if cancel is not None and cancel.is_set():raise MuxError('CANCELLED')
                _need(time.monotonic()<deadline,'MUX_DEADLINE')
                acquired=self.send_lock.acquire(timeout=min(.01,max(0,deadline-time.monotonic())))
            self._current()
            while not reserved:
                if cancel is not None and cancel.is_set():raise MuxError('CANCELLED')
                _need(time.monotonic()<deadline,'MUX_MEMORY_DEADLINE')
                reserved=self.connection.owner.memory.take(len(payload))
                if not reserved:self.closed_event.wait(.01);self._current()
            digest=hashlib.sha256(payload).digest();transfer=str(uuid.uuid4())
            for index in range((len(payload)+CHUNK_SIZE-1)//CHUNK_SIZE):
                self._current()
                if cancel is not None and cancel.is_set():raise MuxError('CANCELLED')
                _need(time.monotonic()<deadline,'MUX_DEADLINE')
                chunk=payload[index*CHUNK_SIZE:(index+1)*CHUNK_SIZE]
                raw=encode_fragment(self.binding,self.connection.nonce,transfer,kind,len(payload),index,digest,chunk)
                attempted=True
                self.connection.send_mux_fragment(raw,deadline=deadline,cancel=cancel)
            return transfer
        except TransportError as exc:
            if attempted:
                self._abort('MUX_DELIVERY_UNKNOWN');raise MuxError('MUX_DELIVERY_UNKNOWN') from exc
            if isinstance(exc,MuxError):raise
            raise MuxError(str(exc)) from exc
        finally:
            if reserved:self.connection.owner.memory.release(len(payload))
            if acquired:self.send_lock.release()

    def receive(self,*,deadline=None,cancel=None):
        deadline=self._deadline(deadline,10)
        try:
            with self.cv:
                while True:
                    self._current()
                    if cancel is not None and cancel.is_set():raise MuxError('MUX_CANCELLED')
                    _need(time.monotonic()<deadline,'MUX_RECEIVE_DEADLINE')
                    result=self.rx.pop()
                    if result is not None:self.cv.notify_all();return result
                    self.cv.wait(min(.01,max(0,deadline-time.monotonic())))
        except TransportError as exc:
            self._abort(str(exc));raise MuxError(str(exc)) from exc
