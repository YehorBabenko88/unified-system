"""Bounded own-loopback TLS front, pending actual identity/owner composition.

No caller/provider injection, store, research engine, credentials or activation
flag. TLS peer chain validation alone is NOT Gateway principal authorization.
Only public static capabilities are served; resource routes remain closed.
"""
import json
import re
import socket
import ssl
import sqlite3
import threading
import time
import hashlib
import importlib.util
import pathlib
import subprocess
import sys
from datetime import datetime, timezone

from .intelligence_gateway import catalog


class DisposableGatewayFront:
    """Explicit temporary listener, fixed localhost/ephemeral port, no service.

    Root owns the SSLContext/cert/key lifecycle. This object does not prove the
    loaded server leaf, SAN/EKU/fingerprint or A2 registry commissioning. Those
    checks must be integrated before any authenticated resource route opens.
    """
    def __init__(self, *, server_ssl_context):
        if (type(server_ssl_context) is not ssl.SSLContext
                or server_ssl_context.protocol != ssl.PROTOCOL_TLS_SERVER
                or server_ssl_context.verify_mode != ssl.CERT_REQUIRED
                or server_ssl_context.minimum_version < ssl.TLSVersion.TLSv1_2):
            raise ValueError('DISPOSABLE_TLS_CONTEXT_REQUIRED')
        self._context = server_ssl_context
        self._stop = threading.Event()
        self._slots = threading.BoundedSemaphore(4)
        self._lock = threading.Lock()
        self._workers = set()
        self._listener = None
        self._thread = None
        self._started = False
        self.address = None
        self._manifest_composition = None

    def start(self):
        if self._started or self._stop.is_set():
            raise RuntimeError('FRONT_NOT_RESTARTABLE')
        self._started = True
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            listener.bind(('127.0.0.1', 0))
            listener.listen(4)
            listener.settimeout(0.1)
            self.address = listener.getsockname()
            self._listener = listener
            self._thread = threading.Thread(target=self._accept, name='gateway-disposable-accept', daemon=True)
            self._thread.start()
        except BaseException:
            listener.close()
            raise

    def _accept(self):
        while not self._stop.is_set():
            try:
                raw, _ = self._listener.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            if not self._slots.acquire(blocking=False):
                raw.close()
                continue
            worker = threading.Thread(target=self._worker, args=(raw,), name='gateway-disposable-peer', daemon=True)
            with self._lock:
                self._workers.add(worker)
            try:
                worker.start()
            except BaseException:
                with self._lock:
                    self._workers.discard(worker)
                self._slots.release()
                raw.close()
                return

    def _worker(self, raw):
        deadline = time.monotonic()+2
        peer = None
        try:
            raw.settimeout(2)
            peer = self._context.wrap_socket(raw, server_side=True, do_handshake_on_connect=False)
            peer.do_handshake()
            header = bytearray()
            while not header.endswith(b'\r\n\r\n'):
                remaining = deadline-time.monotonic()
                if remaining <= 0:
                    return
                peer.settimeout(remaining)
                if len(header) >= 8192:
                    self._respond(peer, 400, {'code':'INVALID_REQUEST'}, head=header.startswith(b'HEAD '))
                    return
                part = peer.recv(1)
                if not part:
                    return
                header.extend(part)
            status, body, head = self._route(bytes(header))
            if (status == 503 and self._manifest_composition is not None
                    and any(bytes(header).startswith(b'POST '+p+b' HTTP/1.1\r\n')
                            for p in (b'/intelligence/v1/manifest',b'/intelligence/v1/query'))):
                status, encoded = self._manifest_composition.exchange(peer, bytes(header), deadline)
                remaining = deadline-time.monotonic()
                if remaining > 0:
                    peer.settimeout(remaining)
                    self._respond_bytes(peer, status, encoded)
                return
            remaining = deadline-time.monotonic()
            if remaining <= 0:
                return
            peer.settimeout(remaining)
            self._respond(peer, status, body, head=head)
        except (OSError, ValueError, ssl.SSLError):
            # Do not reflect or retain peer headers, certificate or payload.
            pass
        finally:
            if peer is not None:
                peer.close()
            raw.close()
            with self._lock:
                self._workers.discard(threading.current_thread())
            self._slots.release()

    def _route(self, raw):
        head = raw.startswith(b'HEAD ')
        try:
            lines = raw[:-4].split(b'\r\n')
            if not 2 <= len(lines) <= 33:
                raise ValueError()
            method, path, version = lines[0].decode('ascii').split(' ')
            if method not in ('GET','HEAD','POST') or version != 'HTTP/1.1':
                raise ValueError()
            if not re.fullmatch(r'/[A-Za-z0-9/_-]{1,127}', path) or '..' in path:
                raise ValueError()
            headers = {}
            for line in lines[1:]:
                name, value = line.split(b':', 1)
                if not re.fullmatch(rb'[A-Za-z0-9-]{1,64}', name):
                    raise ValueError()
                key = name.decode('ascii').lower()
                value = value.strip(b' ')
                if key in headers or len(value)>4096 or any(c<32 or c>126 for c in value):
                    raise ValueError()
                headers[key] = value
            if headers.get('host') != ('127.0.0.1:'+str(self.address[1])).encode('ascii'):
                raise ValueError()
            if 'transfer-encoding' in headers:
                raise ValueError()
            length = headers.get('content-length',b'0')
            if not re.fullmatch(rb'0|[1-9][0-9]{0,4}',length) or int(length)>32768:
                raise ValueError()
            if path == '/intelligence/v1/capabilities':
                if int(length) != 0 or method not in ('GET','HEAD'):
                    raise ValueError()
                if self._manifest_composition is not None:
                    tool=('unified.query_market_data' if self._manifest_composition.query_adapter is not None
                          else 'unified.get_dataset_manifest')
                    return 200,dict(schema='unified.gateway.runtime-capabilities.v1',mode='DISPOSABLE_ONLY',
                        client_interface='OWN_LOOPBACK_HTTPS',configured_read_tools=[tool],
                        all_other_tools='BLOCKED',requires_current_principal_and_tool_scope=True,
                        native_human_authentication=False,production_runtime=False),method=='HEAD'
                return 200, catalog(), method=='HEAD'
            if path in ('/intelligence/v1/query','/intelligence/v1/manifest','/intelligence/v1/research-jobs'):
                # No body read, context creation or owner IO without actual A2
                # identity + exact owner request schema/source admission.
                return 503, {'code':'CLIENT_ADMISSION_UNAVAILABLE'}, method=='HEAD'
            return 404, {'code':'NOT_FOUND'}, method=='HEAD'
        except (ValueError, UnicodeError):
            return 400, {'code':'INVALID_REQUEST'}, head

    @staticmethod
    def _respond(peer, status, value, *, head=False):
        body=json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')
        DisposableGatewayFront._respond_bytes(peer, status, body, head=head)

    @staticmethod
    def _respond_bytes(peer, status, body, *, head=False):
        if type(body) is not bytes or len(body)>32768:
            raise ValueError('BOUNDED_GATEWAY_RESPONSE_REQUIRED')
        label={200:'OK',400:'Bad Request',401:'Unauthorized',403:'Forbidden',404:'Not Found',503:'Service Unavailable'}[status]
        header=(f'HTTP/1.1 {status} {label}\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\n'
                'Connection: close\r\nCache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\n\r\n').encode('ascii')
        peer.sendall(header+(b'' if head else body))

    def is_alive(self):
        with self._lock:
            return bool((self._thread and self._thread.is_alive()) or self._workers)

    def close(self):
        self._stop.set()
        if self._listener is not None:
            self._listener.close()
        if self._thread is not None:
            self._thread.join(3)
        with self._lock:
            workers = tuple(self._workers)
        for worker in workers:
            worker.join(3)
        if self.is_alive():
            raise RuntimeError('OWNED_FRONT_CLEANUP_UNCONFIRMED')


class _ManifestComposition:
    """Root-owned exact issuer/store/reader wiring, no client object injection."""
    def __init__(self, authority, sink, store, journal, realm_id, query_adapter=None):
        self.authority, self.sink, self.store = authority, sink, store
        self.journal, self.realm = journal, realm_id
        self.query_adapter = query_adapter
        self.lock = threading.Lock()
        self.flush('COMMISSIONED_DISPOSABLE_ONLY')

    def flush(self, stage):
        # Existing Journal is reused only within an owner-provisioned, private,
        # single-writer disposable root. This is not distributed commit evidence.
        path=self.journal.path
        info=path.lstat()
        if (path.is_symlink() or info.st_nlink!=1 or getattr(info,'st_file_attributes',0)&1024
                or info.st_size>4*1024*1024-65536
                or any(type(path)(str(path)+suffix).exists() for suffix in ('-wal','-shm','-journal'))):
            raise RuntimeError('AUDIT_ROOT_UNAVAILABLE')
        records=self.journal.read()
        if len(records)>=4096 or any(type(r['receipt']) is not dict
                or r['receipt'].get('schema')!='unified.gateway.audit-batch.v1'
                or r['receipt'].get('realm_id')!=self.realm for r in records):
            raise RuntimeError('AUDIT_SCOPE_UNAVAILABLE')
        events=self.sink.drain()
        receipt=dict(schema='unified.gateway.audit-batch.v1',realm_id=self.realm,
            observed_at_utc=datetime.now(timezone.utc).isoformat(),stage=stage,events=list(events),
            evidence_scope='LOCAL_DISPOSABLE_AUDIT_NOT_CONSENSUS')
        if len(json.dumps(receipt).encode())>65536:
            raise RuntimeError('AUDIT_BATCH_EXCEEDED')
        self.journal.append('OBSERVING',receipt,expected_sequence=len(records))

    def exchange(self, peer, header, deadline):
        from .gateway_identity import GatewayIdentityDenied, GatewayIdentityUnavailable
        def error(status,code):
            return status,json.dumps({'code':code},separators=(',',':')).encode('ascii')
        remaining=deadline-time.monotonic()
        if remaining<=0 or not self.lock.acquire(timeout=max(0,remaining)):
            return error(503,'REQUEST_DEADLINE_EXCEEDED')
        try:
            values={line.split(b':',1)[0].lower():line.split(b':',1)[1].strip()
                    for line in header[:-4].split(b'\r\n')[1:]}
            is_query=header.startswith(b'POST /intelligence/v1/query ')
            if is_query and self.query_adapter is None:
                return error(503,'QUERY_ADAPTER_UNAVAILABLE')
            if not is_query and self.query_adapter is not None:
                return error(503,'MANIFEST_ADAPTER_NOT_COMMISSIONED')
            if (values.get(b'content-type')!=b'application/json' or b'expect' in values
                    or b'content-encoding' in values or b'content-length' not in values):
                return error(400,'INVALID_REQUEST')
            length=int(values[b'content-length'])
            if not 0<length<=(32768 if is_query else 16384):
                return error(400,'INVALID_REQUEST')
            try:
                context=self.authority.authenticate_connection(peer)
                self.flush('AUTHENTICATED_BEFORE_BODY')
            except GatewayIdentityDenied:
                self.flush('AUTHENTICATION_DENIED')
                return error(401,'UNAUTHENTICATED')
            body=bytearray()
            while len(body)<length:
                remaining=deadline-time.monotonic()
                if remaining<=0:
                    return error(503,'REQUEST_DEADLINE_EXCEEDED')
                peer.settimeout(remaining)
                part=peer.recv(min(4096,length-len(body)))
                if not part:
                    return error(400,'INCOMPLETE_REQUEST')
                body.extend(part)
            raw=bytes(body)
            if is_query:
                return self.query(context,raw)
            try:
                from .storage.gateway_disclosure import (prepare_manifest_request,
                    get_dataset_manifest, DisclosureInvalid, DisclosureUnavailable)
            except ImportError:
                return error(503,'DISCLOSURE_ADAPTER_UNAVAILABLE')
            try:
                prepared=prepare_manifest_request(raw)
                capability=self.authority.authorize_read(context,tool_name='unified.get_dataset_manifest',
                    request_bytes=raw,binding=prepared.binding,owned_store=self.store)
                self.flush('ISSUED_BEFORE_OWNER_IO')
                result=get_dataset_manifest(raw,owner_read_capability=capability,
                    expected_identity_authority=self.authority,pinned_owned_store=self.store)
                if type(result) is not bytes or not 0<len(result)<=32768:
                    raise RuntimeError('OWNER_RESPONSE_UNAVAILABLE')
                self.flush('OWNER_READ_BEFORE_RESPONSE')
                return 200,result
            except DisclosureInvalid:
                self.flush('INVALID_OWNER_REQUEST')
                return error(400,'INVALID_REQUEST')
            except GatewayIdentityDenied:
                self.flush('READ_DENIED')
                return error(403,'READ_DENIED')
            except DisclosureUnavailable:
                self.flush('OWNER_READ_UNAVAILABLE')
                return error(503,'DISCLOSURE_UNAVAILABLE')
        except (GatewayIdentityUnavailable,RuntimeError,OSError,ValueError,TypeError,KeyError,sqlite3.Error):
            try:
                self.flush('REQUEST_FAILED_NO_OUTPUT')
            except (RuntimeError,OSError,ValueError,TypeError,KeyError,sqlite3.Error):
                pass
            return error(503,'AUDIT_OR_OWNER_UNAVAILABLE')
        finally:
            self.lock.release()

    def query(self, context, raw):
        from .gateway_identity import GatewayIdentityDenied
        adapter=self.query_adapter
        try:
            request=adapter.prepare_query(raw).as_dict()
            binding=dict(schema='unified.gateway.read-binding.v1-review2',dataset_id=request['dataset_id'],
                dataset_revision=request['dataset_revision'],manifest_sha256=request['knowledge_cut']['manifest_sha256'],
                schema_sha256=request['data_schema_sha256'],consumer_id=request['consumer_context']['consumer_id'],
                view_id=request['consumer_context']['view_id'])
            capability=self.authority.authorize_read(context,tool_name='unified.query_market_data',
                request_bytes=raw,binding=binding,owned_store=self.store)
            self.flush('QUERY_ISSUED_BEFORE_OWNER_IO')
            result=adapter.query_market_data(raw,owner_read_capability=capability,
                expected_identity_authority=self.authority,pinned_owned_store=self.store)
            if type(result) is not dict or result.get('status')!='SYNTHETIC_QUERY_RESULT':
                raise RuntimeError('ACTUAL_QUERY_NOT_EXECUTED')
            owner_bytes=json.dumps(result,sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')
            envelope=dict(schema='unified.gateway.query-disclosure.v1',status='SYNTHETIC_QUERY_RESULT',
                owner_result=result,owner_result_sha256=hashlib.sha256(owner_bytes).hexdigest(),
                units={'price':'quote-per-base','volume':'base','turnover':'quote'},
                units_status='DECLARED_SYNTHETIC_ROW_PROFILE',artifact_published=False)
            encoded=json.dumps(envelope,sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')
            if len(encoded)>32768:
                raise RuntimeError('GATEWAY_VIEW_RESPONSE_BUDGET_EXCEEDED')
            self.flush('QUERY_BEFORE_RESPONSE')
            return 200,encoded
        except GatewayIdentityDenied:
            self.flush('QUERY_DENIED')
            return 403,b'{"code":"READ_DENIED"}'
        except adapter.QueryFormatError:
            self.flush('QUERY_FORMAT_OR_CONTENT_REFUSED')
            return 400,b'{"code":"QUERY_FORMAT_OR_CONTENT_REFUSED"}'


def commission_disposable_manifest_front(*,server_ssl_context,profile,pinned_owned_store,
        audit_journal,commissioning_client_context):
    """Explicit own-stand factory. No production, Windows or service admission.

    Root provisions actual TLS material and store/journal objects, never a JSON
    request. A real pinned server-leaf probe completes before any route opens.
    The selected reader is the fixed owner module, never a callback parameter.
    """
    try:
        from .storage.gateway_disclosure import get_dataset_manifest
    except ImportError:
        raise RuntimeError('MANIFEST_ADAPTER_NOT_PACKAGED') from None
    return _commission_front(server_ssl_context=server_ssl_context,profile=profile,
        pinned_owned_store=pinned_owned_store,audit_journal=audit_journal,
        commissioning_client_context=commissioning_client_context)


def _commission_front(*,server_ssl_context,profile,pinned_owned_store,
        audit_journal,commissioning_client_context,query_adapter=None):
    from .gateway_identity import DisposableIdentityAuthority,GatewayAuditSink
    from .storage.object_store import ObjectStore
    from .journal import Journal
    if (type(pinned_owned_store) is not ObjectStore or type(audit_journal) is not Journal
            or type(commissioning_client_context) is not ssl.SSLContext
            or commissioning_client_context.verify_mode!=ssl.CERT_REQUIRED
            or not commissioning_client_context.check_hostname):
        raise ValueError('COMMISSIONING_OBJECTS_UNAVAILABLE')
    sink=GatewayAuditSink(max_events=128)
    issuer=DisposableIdentityAuthority(server_ssl_context=server_ssl_context,profile=profile,audit_sink=sink)
    front=DisposableGatewayFront(server_ssl_context=server_ssl_context)
    front.start()
    try:
        with commissioning_client_context.wrap_socket(socket.create_connection(front.address,timeout=2),
                server_hostname='127.0.0.1') as peer:
            if peer.getpeercert(binary_form=True)!=profile['server_certificate_der']:
                raise RuntimeError('ACTUAL_SERVER_LEAF_PIN_MISMATCH')
            request=(f'GET /intelligence/v1/capabilities HTTP/1.1\r\nHost: 127.0.0.1:{front.address[1]}\r\n\r\n').encode('ascii')
            peer.sendall(request)
            response=bytearray()
            while part:=peer.recv(4096):
                response.extend(part)
                if len(response)>16384:
                    raise RuntimeError('COMMISSIONING_PROBE_EXCEEDED')
            if not response.startswith(b'HTTP/1.1 200 '):
                raise RuntimeError('COMMISSIONING_PROBE_UNAVAILABLE')
        front._manifest_composition=_ManifestComposition(issuer,sink,pinned_owned_store,audit_journal,profile['realm_id'],query_adapter)
        return front
    except BaseException:
        front.close()
        raise


def commission_disposable_query_front(*,server_ssl_context,profile,pinned_owned_store,
        audit_journal,commissioning_client_context,query_source_root):
    """Own-stand source provisioning, not a path/version/callback in HTTP input.

    Only the reviewed Grid module is read from a fixed immutable Git revision and
    checked by its SHA256 before evaluation. This does not admit whole Grid or
    production packaging. Existing A2/A4 canonical classes remain in Unified.
    """
    git='C:/Program Files/Git/cmd/git.exe' if sys.platform=='win32' else '/usr/bin/git'
    raw=subprocess.check_output([git,'--no-replace-objects','-C',str(pathlib.Path(query_source_root)),
        'show','f19f7feee0f63da34a20607a8cae59191180aa7c:grid/gateway_query.py'],timeout=15)
    if hashlib.sha256(raw).hexdigest()!='1186062afaf7d87609acf934a8cf2f55405f7786bdc0f76516956ff89424b9cd':
        raise RuntimeError('GRID_QUERY_SOURCE_PIN_MISMATCH')
    name='_unified_owned_grid_query_f19f7fee'
    if name in sys.modules:
        raise RuntimeError('GRID_QUERY_NAMESPACE_OCCUPIED')
    module=importlib.util.module_from_spec(importlib.util.spec_from_loader(name,loader=None))
    sys.modules[name]=module
    try:
        exec(compile(raw,'<owned-grid-query-f19f7fee>','exec'),module.__dict__)
        return _commission_front(server_ssl_context=server_ssl_context,profile=profile,
            pinned_owned_store=pinned_owned_store,audit_journal=audit_journal,
            commissioning_client_context=commissioning_client_context,query_adapter=module)
    finally:
        if sys.modules.get(name) is module:
            del sys.modules[name]


