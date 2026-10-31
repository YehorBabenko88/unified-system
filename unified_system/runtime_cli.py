"""Prepare-only runtime CLI with an explicit disposable hosted Windows test lane.

This CLI is not a production trust bridge. Publisher signature, enrollment and
fenced rollout permits belong to Grid deployment_agent. Config contents cannot
authorize themselves. Actual legacy module functional adapters are still needed;
process liveness and a listening port never synthesize readiness.
"""
import argparse
import copy
import hashlib
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import math
import os
from pathlib import Path
import re
import signal
import socket
import sys
import tempfile
import threading
import time
from urllib.parse import urlsplit

from .module_catalog import MODULE_IDS
from .runtime import ModuleSpec,RuntimeSupervisor
from .runtime_process import ProcessDriver,_safe_path

LIMIT=1048576
ERROR='RUNTIME_CLI_REJECTED'


def need(ok):
    if not ok:raise ValueError(ERROR)


def validate_config(c):
    need(type(c) is dict and set(c)=={'schema','node_id','release_id','release_sha256',
        'state_root','snapshot_path','http_port','tick_seconds','specs','programs'})
    need(c['schema'] in ('unified.runtime.config.v1','unified.runtime.config.v2'))
    builtin=c['schema']=='unified.runtime.config.v2'
    need(type(c['node_id']) is str and re.fullmatch('[A-Za-z0-9_-]{1,64}',c['node_id']) and c['node_id'].upper() not in ('ADMINIT','LS5','PC4'))
    need(type(c['release_id']) is str and re.fullmatch('[A-Za-z0-9_.:-]{1,128}',c['release_id']))
    need(type(c['release_sha256']) is str and re.fullmatch('[0-9a-f]{64}',c['release_sha256']))
    need(type(c['http_port']) is int and 0<=c['http_port']<=65535)
    need(type(c['tick_seconds']) in (int,float) and math.isfinite(c['tick_seconds']) and .05<=c['tick_seconds']<=5)
    for key in ('state_root','snapshot_path'):need(type(c[key]) is str and Path(c[key]).is_absolute())
    need(type(c['specs']) is list and len(c['specs'])==6)
    specs={}
    from .runtime import _valid
    for item in c['specs']:
        need(type(item) is dict and set(item)=={'module_id','version','api_major','dependencies','start_timeout'})
        spec=ModuleSpec(**item);_valid(spec)
        need(spec.module_id not in specs);specs[spec.module_id]=spec
    need(set(specs)==MODULE_IDS);RuntimeSupervisor._order(specs)
    expected=MODULE_IDS-{'unified-system'} if builtin else MODULE_IDS
    need(type(c['programs']) is dict and set(c['programs'])==expected)
    if builtin:need(c['http_port']>0 and c['tick_seconds']<=.25)
    for p in c['programs'].values():
        need(type(p) is dict and {'argv','cwd','health_url','executable_sha256','file_pins'}<=set(p)<= {'argv','cwd','health_url','executable_sha256','file_pins','env','ca_file','external_file_pins'})
        argv=p['argv'];need(type(argv) is list and 1<=len(argv)<=32)
        need(all(type(x) is str and 0<len(x)<=4096 and '\0' not in x for x in argv))
        need(not any(x.casefold() in ('-c','-command','-encodedcommand','/c','-e') for x in argv[1:]))
        need(Path(argv[0]).is_absolute() and type(p['cwd']) is str and Path(p['cwd']).is_absolute())
        need(type(p['executable_sha256']) is str and re.fullmatch('[0-9a-f]{64}',p['executable_sha256']))
        pins=p['file_pins'];need(type(pins) is dict and 1<=len(pins)<=10000)
        for file,pin in pins.items():
            need(type(file) is str and file and not Path(file).is_absolute() and '..' not in Path(file).parts and ':' not in file and '\\' not in file)
            need(type(pin) is str and re.fullmatch('[0-9a-f]{64}',pin))
        external=p.get('external_file_pins',{})
        need(type(external) is dict and len(external)<=64)
        for file,pin in external.items():
            need(type(file) is str and len(file)<=4096 and Path(file).is_absolute())
            _safe_path(file)
            need(type(pin) is str and re.fullmatch('[a-f0-9]{64}',pin))
        url=urlsplit(p['health_url'])
        need(url.scheme in ('http','https') and url.hostname in ('127.0.0.1','::1') and url.port is not None and not url.username and not url.password and not url.query and not url.fragment)
        if 'env' in p:
            need(type(p['env']) is dict and len(p['env'])<=64)
            for key,value in p['env'].items():need(type(key) is str and re.fullmatch('[A-Za-z_][A-Za-z0-9_]{0,63}',key) and type(value) is str and len(value)<=8192 and '\0' not in value)
        if 'ca_file' in p:need(type(p['ca_file']) is str and Path(p['ca_file']).is_absolute())
    return c


def read_config(path):
    path=_safe_path(path)
    with path.open('rb') as f:raw=f.read(LIMIT+1)
    need(0<len(raw)<=LIMIT)
    def unique(pairs):
        out={}
        for key,value in pairs:need(key not in out);out[key]=value
        return out
    c=json.loads(raw.decode('utf-8'),object_pairs_hook=unique,parse_constant=lambda _:need(False))
    return validate_config(c),raw


def assert_ephemeral(c,config_path,*,env=None,platform=None,hostname=None):
    env=os.environ if env is None else env
    platform=sys.platform if platform is None else platform
    host=(hostname or socket.gethostname()).split('.')[0].upper()
    need(host not in ('ADMINIT','LS5','PC4') and c['node_id'].upper() not in ('ADMINIT','LS5','PC4'))
    need(platform=='win32' and env.get('GITHUB_ACTIONS')=='true' and env.get('RUNNER_ENVIRONMENT')=='github-hosted' and env.get('RUNNER_OS')=='Windows')
    need(bool(env.get('RUNNER_TEMP')));temp=_safe_path(env['RUNNER_TEMP']).resolve(strict=True)
    paths=[config_path,c['state_root'],c['snapshot_path']]
    for p in c['programs'].values():
        paths.extend((p['cwd'],p['argv'][0]))
        paths.extend(str(Path(p['cwd'])/file) for file in p['file_pins'])
        paths.extend(p.get('external_file_pins',{}))
        if 'ca_file' in p:paths.append(p['ca_file'])
    for path in paths:
        path=_safe_path(path).resolve()
        need(temp in path.parents)
    # Mutable journal/public output must stay outside all immutable module trees.
    for p in c['programs'].values():
        code=_safe_path(p['cwd']).resolve()
        for key in ('state_root','snapshot_path'):
            out=_safe_path(c[key]).resolve();need(out!=code and code not in out.parents)
    return True


class SnapshotView:
    def __init__(self):self.lock=threading.Lock();self.value={'schema':'unified.runtime.unavailable.v1','state':'UNAVAILABLE','physical':'NOT_RUN'}
    def set(self,value):
        data=json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
        need(len(data)<=LIMIT)
        with self.lock:self.value=json.loads(data)
    def get(self):
        with self.lock:return copy.deepcopy(self.value)


def status_server(view,*,port):
    class Handler(BaseHTTPRequestHandler):
        def setup(self):super().setup();self.connection.settimeout(2)
        def log_message(self,*args):pass
        def do_GET(self):
            if self.headers.get('Origin') or self.headers.get('Host')!='127.0.0.1:'+str(self.server.server_address[1]):self.send_error(403);return
            if self.path!='/internal/v2/runtime':self.send_error(404);return
            data=json.dumps(view.get(),sort_keys=True,separators=(',',':'),allow_nan=False).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)))
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(data)
        def denied(self):self.send_error(405);self.close_connection=True
        do_POST=do_PUT=do_DELETE=do_PATCH=do_HEAD=do_OPTIONS=denied
    class StatusServer(ThreadingHTTPServer):
        daemon_threads=True
        block_on_close=False
        request_queue_size=4
        allow_reuse_address=os.name!='nt'
        max_active_requests=4
        def __init__(self,*a,**kw):
            self.slots=threading.BoundedSemaphore(self.max_active_requests)
            self.worker_lock=threading.Lock();self.workers={}
            super().__init__(*a,**kw)
        def process_request(self,request,address):
            if not self.slots.acquire(blocking=False):
                self.shutdown_request(request);return
            try:super().process_request(request,address)
            except BaseException:self.slots.release();raise
        def process_request_thread(self,request,address):
            worker=threading.current_thread()
            with self.worker_lock:self.workers[worker]=request
            def expire():
                try:request.shutdown(socket.SHUT_RDWR)
                except OSError:pass
            deadline=threading.Timer(1.,expire);deadline.daemon=True;deadline.start()
            try:super().process_request_thread(request,address)
            finally:
                deadline.cancel();deadline.join()
                with self.worker_lock:self.workers.pop(worker,None)
                self.slots.release()
        def server_close(self):
            super().server_close()
            with self.worker_lock:workers=list(self.workers.items())
            for _,request in workers:
                try:request.shutdown(socket.SHUT_RDWR)
                except OSError:pass
            end=time.monotonic()+2
            for worker,_ in workers:worker.join(max(0,end-time.monotonic()))
    return StatusServer(('127.0.0.1',port),Handler)


def write_snapshot(path,snapshot):
    path=_safe_path(path)
    need(not path.exists() or path.stat().st_nlink==1)
    data=(json.dumps(snapshot,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode();need(len(data)<=LIMIT)
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,temp=tempfile.mkstemp(prefix='.runtime-',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        _safe_path(path);os.replace(temp,path)
    finally:
        try:Path(temp).unlink()
        except FileNotFoundError:pass


def make_runtime(c,authorize):
    root=Path(c['state_root'])
    driver=ProcessDriver(root/'private-processes',c['programs'],authorize=authorize)
    if c['schema']=='unified.runtime.config.v2':
        from .runtime_builtin import BuiltinRuntimeDriver
        driver=BuiltinRuntimeDriver(driver,journal_path=root/'runtime.sqlite',snapshot_path=c['snapshot_path'],
            http_port=c['http_port'],node_id=c['node_id'],release_id=c['release_id'],
            release_sha256=c['release_sha256'],authorize=authorize)
    return RuntimeSupervisor(root/'runtime.sqlite',driver,[ModuleSpec(**x) for x in c['specs']],
        release_id=c['release_id'],release_sha256=c['release_sha256'],node_id=c['node_id'])


def run_runtime(c,runtime,*,stop_event):
    view=SnapshotView();view.set(runtime.snapshot())
    server=status_server(view,port=c['http_port'])
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    def publish():
        snapshot=runtime.snapshot();view.set(snapshot);write_snapshot(c['snapshot_path'],snapshot)
        from .runtime_builtin import BuiltinRuntimeDriver
        driver=getattr(runtime,'driver',None)
        if isinstance(driver,BuiltinRuntimeDriver):driver.published(snapshot)
    try:
        publish()
        runtime.start()
        while not stop_event.is_set():
            runtime.tick();publish()
            stop_event.wait(c['tick_seconds'])
    finally:
        try:
            try:runtime.stop(administrative=True)
            finally:
                publish()
        finally:server.shutdown();server.server_close();thread.join(3)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',required=True);parser.add_argument('--config-sha256')
    parser.add_argument('--scope',choices=('prepare','ephemeral-ci'),default='prepare');parser.add_argument('--execute',action='store_true')
    args=parser.parse_args(argv)
    try:
        c,raw=read_config(args.config)
        if not args.execute:
            print('PREPARE_ONLY; modules=6; processes=NOT_STARTED; physical=NOT_AUTHORIZED; production_trust_bridge=UNSUPPORTED')
            return 0
        need(args.scope=='ephemeral-ci')
        need(type(args.config_sha256) is str and re.fullmatch('[0-9a-f]{64}',args.config_sha256) and hashlib.sha256(raw).hexdigest()==args.config_sha256)
        assert_ephemeral(c,args.config)
        def authorize(action,module):
            # Re-evaluate actual execution scope before every process start.
            return action=='start' and module in MODULE_IDS and assert_ephemeral(c,args.config)
        runtime=make_runtime(c,authorize);stop=threading.Event()
        previous={}
        try:
            for sig in (signal.SIGINT,signal.SIGTERM):previous[sig]=signal.signal(sig,lambda *_:stop.set())
            run_runtime(c,runtime,stop_event=stop)
        finally:
            for sig,handler in previous.items():signal.signal(sig,handler)
        return 0
    except Exception:
        print('BLOCKED: '+ERROR+'; physical=NOT_AUTHORIZED',file=sys.stderr);return 1


if __name__=='__main__':raise SystemExit(main())
