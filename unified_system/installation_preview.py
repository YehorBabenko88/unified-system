"""Explicit, short-lived loopback preview host; inert on import/default CLI.

This is a preview of actual local journal receipts, not an installer wizard or
controller. HTTP/1.0 closes after one request. Unframed trailing bytes cannot be
reliably detected without blocking: they are discarded when the socket closes.
"""
import argparse
import io
import json
import math
import socket
import threading
import time
from wsgiref.simple_server import WSGIServer, WSGIRequestHandler, ServerHandler
from .installation_progress import InstallationProgress
from .installation_ui import InstallationBootstrapApp

MAX_HEADER_BYTES=8192
MAX_HEADER_LINE=2048
MAX_HEADER_COUNT=32


def _limits(progress,port,duration,request_timeout):
    if type(progress) is not InstallationProgress or type(port) is not int or not 0<=port<=65535:
        raise ValueError('invalid preview configuration')
    for value,upper in ((duration,300),(request_timeout,2)):
        if type(value) not in (int,float) or not math.isfinite(value) or not 0<value<=upper:
            raise ValueError('invalid preview limits')


class _Server(WSGIServer):
    request_queue_size=1


class _Handler(WSGIRequestHandler):
    protocol_version='HTTP/1.0'
    def log_message(self,*args):pass
    def log_error(self,*args):pass
    def get_stderr(self):return io.StringIO()
    def setup(self):
        super().setup()
        self._input=b''
        self._request_deadline=min(self.server.deadline,time.monotonic()+self.server.request_timeout)
        self.server.preview._accepted(self.connection)
        remaining=max(0.001,self.server.deadline-time.monotonic())
        self.connection.settimeout(min(self.server.request_timeout,remaining))
    def finish(self):
        try:super().finish()
        finally:self.server.preview._finished(self.connection)
    def _reject(self,code):
        labels={400:'Bad Request',431:'Request Header Fields Too Large'}
        body=b'REQUEST_REJECTED\n'
        self.wfile.write(('HTTP/1.0 '+str(code)+' '+labels[code]+'\r\nConnection: close\r\nContent-Type: text/plain\r\nContent-Length: '+str(len(body))+"\r\nCache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\nContent-Security-Policy: default-src 'none'; frame-ancestors 'none'\r\nReferrer-Policy: no-referrer\r\n\r\n").encode('ascii')+body)
    def send_error(self,code,message=None,explain=None):self._reject(400)
    def _line(self):
        # Poll the raw socket: on Windows shutdown need not immediately wake a
        # timeout-mode buffered read. Never retry a timed-out makefile reader.
        while True:
            remaining=self._request_deadline-time.monotonic()
            if self.server.preview._stop.is_set() or remaining<=0:raise TimeoutError()
            newline=self._input.find(b'\n')
            if newline>=0 or len(self._input)>MAX_HEADER_LINE:
                size=min(newline+1 if newline>=0 else len(self._input),MAX_HEADER_LINE+1)
                line,self._input=self._input[:size],self._input[size:]
                return line
            self.connection.settimeout(min(0.05,remaining))
            try:chunk=self.connection.recv(512)
            except socket.timeout:continue
            if not chunk:
                line,self._input=self._input,b''
                return line
            self._input+=chunk
    def handle(self):
        try:
            self.raw_requestline=self._line()
            if len(self.raw_requestline)>MAX_HEADER_LINE:self._reject(431);return
            if not self.raw_requestline:return
            total=len(self.raw_requestline);lines=[];names=[]
            while True:
                line=self._line();total+=len(line)
                if len(line)>MAX_HEADER_LINE or total>MAX_HEADER_BYTES or len(lines)>MAX_HEADER_COUNT:
                    self._reject(431);return
                if line==b'\r\n':lines.append(line);break
                if len(lines)>=MAX_HEADER_COUNT:self._reject(431);return
                if not line or not line.endswith(b'\r\n') or line[:1] in (b' ',b'\t') or b':' not in line:
                    self._reject(400);return
                name,value=line[:-2].split(b':',1)
                if any(c<32 and c!=9 or c==127 for c in value):self._reject(400);return
                if not name or any(c not in b"!#$%&'*+-.^_`|~0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ" for c in name):
                    self._reject(400);return
                name=name.lower();names.append(name)
                if name in (b'transfer-encoding',b'expect') or (name==b'content-length' and value.strip()!=b'0'):
                    self._reject(400);return
                if name in (b'host',b'content-length') and names.count(name)>1:self._reject(400);return
                lines.append(line)
            if names.count(b'host')!=1:self._reject(400);return
            stream=self.rfile
            try:
                self.rfile=io.BytesIO(b''.join(lines))
                if not self.parse_request():return
            finally:self.rfile=stream
            self.close_connection=True
            remaining=self.server.deadline-time.monotonic()
            if remaining<=0:return
            self.connection.settimeout(min(self.server.request_timeout,remaining))
            handler=ServerHandler(self.rfile,self.wfile,self.get_stderr(),self.get_environ(),multithread=False)
            handler.request_handler=self
            handler.run(self.server.get_app())
        except (TimeoutError,ConnectionError,OSError):
            # No raw request, URL, body or exception diagnostics are logged.
            return


class InstallationPreview:
    """One request; watchdogs bound owned network sockets, not Python CPU work.

    Accepted sockets have <=2s hard network deadlines. A separate lifetime
    watchdog closes the listener and accepted socket within <=300s. Source
    SQLite/read computation is synchronous and is not forcibly terminated.
    """
    def __init__(self,progress,*,port=0,duration=60,request_timeout=0.5):
        _limits(progress,port,duration,request_timeout)
        self.progress=progress;self.port=port;self.duration=duration;self.request_timeout=request_timeout
        self.address=None;self.authority=None;self._server=None;self._thread=None;self._stop=threading.Event()
        self._lock=threading.Lock();self._active=None;self._request_timer=None;self._lifetime_timer=None
    @property
    def running(self):return self._thread is not None and self._thread.is_alive()
    def start(self):
        if self._thread is not None:raise ValueError('preview already started')
        # Source must still be admitted before any socket is bound.
        self.progress.snapshot()
        server=_Server(('127.0.0.1',self.port),_Handler)
        try:
            self.address=('127.0.0.1',server.server_port);self.authority='127.0.0.1:'+str(server.server_port)
            server.set_app(InstallationBootstrapApp(self.progress,self.authority))
            server.timeout=0.05;server.request_timeout=self.request_timeout;server.deadline=time.monotonic()+self.duration
            self._server=server;server.preview=self
            self._thread=threading.Thread(target=self._run,name='unified-installation-preview',daemon=True)
            self._lifetime_timer=threading.Timer(self.duration,self._expire)
            self._lifetime_timer.daemon=True
            self._thread.start();self._lifetime_timer.start()
        except BaseException:server.server_close();raise
        return self
    @staticmethod
    def _shutdown(connection):
        if connection is not None:
            try:connection.shutdown(socket.SHUT_RDWR)
            except OSError:pass
    def _accepted(self,connection):
        with self._lock:
            self._active=connection
            remaining=self._server.deadline-time.monotonic()
            if self._stop.is_set() or remaining<=0:
                self._shutdown(connection);return
            timer=threading.Timer(min(self.request_timeout,remaining),self._interrupt,args=(connection,))
            timer.daemon=True;self._request_timer=timer;timer.start()
    def _interrupt(self,connection):
        with self._lock:
            if self._active is connection:self._shutdown(connection)
    def _finished(self,connection):
        with self._lock:
            if self._active is not connection:return
            self._active=None;timer=self._request_timer;self._request_timer=None
        if timer is not None:
            timer.cancel()
            if timer is not threading.current_thread():timer.join()
    def _expire(self):
        self._stop.set()
        with self._lock:
            self._shutdown(self._active)
            if self._server is not None:self._server.server_close()
    def _run(self):
        try:
            while not self._stop.is_set() and time.monotonic()<self._server.deadline:
                self._server.handle_request()
        except (OSError,ValueError):
            if not self._stop.is_set():raise
        finally:
            self._server.server_close()
            if self._lifetime_timer is not None:self._lifetime_timer.cancel()
    def close(self):
        self._expire()
        if self._lifetime_timer is not None:
            self._lifetime_timer.cancel()
            if self._lifetime_timer is not threading.current_thread():self._lifetime_timer.join()
        if self._thread is not None:self._thread.join(self.request_timeout+1)
        if self.running:raise RuntimeError('preview shutdown incomplete')
    def __enter__(self):return self.start()
    def __exit__(self,*args):self.close()


def preview_plan(progress,*,port=0,duration=60):
    _limits(progress,port,duration,0.5)
    snapshot=progress.snapshot()
    return dict(schema='unified.installation-preview-plan.v1',mode='PLAN_ONLY',computer=socket.gethostname(),
        journal=str(progress.path),installation_id=snapshot['installation_id'],node_id=snapshot['node_id'],
        release_manifest_sha256=snapshot['release_manifest_sha256'],host='127.0.0.1',port=port,duration_seconds=duration,
        listener_started=False,required_owner_confirmation=True,installation_authority=False,existing_services_touched=False,existing_databases_modified=False,
        new_resources=['one temporary loopback listener when explicitly served'],
        missing=['installer wizard','authenticated installer controller','verified Terminan handoff'],
        rollback='Shutdown preview thread and close temporary loopback socket; journal remains read-only and preserved.')


def main(argv=None):
    parser=argparse.ArgumentParser(description='Read-only installation preview; default emits plan without a listener.')
    parser.add_argument('--journal',required=True);parser.add_argument('--installation-id',required=True)
    parser.add_argument('--node-id',required=True);parser.add_argument('--release-manifest-sha256',required=True)
    parser.add_argument('--port',type=int,default=0);parser.add_argument('--duration',type=float,default=60)
    parser.add_argument('--serve',action='store_true')
    args=parser.parse_args(argv)
    try:
        progress=InstallationProgress.open(args.journal,args.installation_id,args.node_id,args.release_manifest_sha256)
        plan=preview_plan(progress,port=args.port,duration=args.duration)
        print(json.dumps(plan,sort_keys=True))
        if args.serve:
            with InstallationPreview(progress,port=args.port,duration=args.duration) as host:
                print(json.dumps({'mode':'READ_ONLY_PREVIEW','host':host.authority,'installation_authority':False}),flush=True)
                while host.running:host._thread.join(0.1)
    except (ValueError,OSError):
        print(json.dumps({'status':'UNAVAILABLE','error_code':'PREVIEW_REJECTED'}));return 1
    return 0


if __name__=='__main__':raise SystemExit(main())
