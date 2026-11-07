"""Bounded own-loopback TLS front, pending actual identity/owner composition.

No caller/provider injection, store, research engine, credentials or activation
flag. TLS peer chain validation alone is NOT Gateway principal authorization.
Only public static capabilities are served; resource routes remain closed.
"""
import json
import re
import socket
import ssl
import threading
import time

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
        label={200:'OK',400:'Bad Request',404:'Not Found',503:'Service Unavailable'}[status]
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
