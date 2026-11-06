"""Synthetic test composition ONLY; owned ephemeral loopback plain HTTP."""
from contextlib import contextmanager
from dataclasses import asdict
import threading
from wsgiref.simple_server import make_server,WSGIRequestHandler

from unified_system.control_v3_boundary import handle_request
from unified_system.control_v3_read_adapter import ControlReadAdapter,ReadContext


class FixtureComposition:
    def __init__(self,identity_denied=False,authority_missing=False,revoke_during_read=False,mode=None):
        self.denied=identity_denied;self.revoke=revoke_during_read;self.mode=mode
        self.adapter=ControlReadAdapter(self,None if authority_missing else self)

    def resolve(self,request):
        return None if self.denied else ReadContext('fixture_actor','fixture_session','fixture_view','1')

    def snapshot(self,context,selector):
        result=dict(scope=asdict(selector),view_id=context.view_id,revision='1',cursor='fixture_cursor',
            state_root='1'*64,resources=[{'node_id':'PC3','state':'IDLE'}])
        if self.mode=='wrong_view':result['view_id']='other_view'
        if self.mode=='wrong_scope':result['scope']['source_id']='unrequested'
        if self.mode=='bad_root':result['state_root']='not-a-root'
        if self.mode=='oversize':result['resources']=[{'payload':'x'*65536}]
        if self.revoke:self.denied=True
        return result

    def events(self,context,request):
        frames=[dict(epoch='1',sequence='1',view_id=context.view_id,kind='DATA',payload={'node_id':'PC3'}),
                dict(epoch='1',sequence='2',view_id=context.view_id,kind='LIVENESS',payload={'connection_id':'fixture'})]
        if self.mode=='event_gap':frames[1]['sequence']='3'
        if self.mode=='event_epoch':frames[0]['epoch']='2'
        if self.mode=='wrong_view':frames[1]['view_id']='other'
        if self.mode=='event_liveness_authority':frames[1]['payload']['authority']='CURRENT'
        return frames

    def __call__(self,environ,start_response):
        def start(status,headers):return start_response(status,headers+[('X-Evidence-Class','SYNTHETIC_LOOPBACK_FIXTURE')])
        return handle_request(environ,start,self.adapter)


class QuietHandler(WSGIRequestHandler):
    def get_environ(self):
        e=super().get_environ();e['RAW_URI']=self.path;return e
    def log_message(self,*args):pass


@contextmanager
def fixture_server(app):
    server=make_server('127.0.0.1',0,app,handler_class=QuietHandler)
    thread=threading.Thread(target=lambda:server.serve_forever(poll_interval=.01),daemon=True)
    thread.start()
    try:yield 'http://127.0.0.1:'+str(server.server_port)
    finally:
        server.shutdown();thread.join(timeout=3);server.server_close()
        if thread.is_alive():raise AssertionError('owned fixture server failed to stop')
