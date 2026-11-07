"""Control Mux WSGI composition boundary; native composition pending.
No environment activation, listener, fixture context or header identity fallback.
"""
from .codec import encode, validate

class ControlMuxApp:
    def __call__(self, environ, start_response):
        # Do not read an unadmitted body or expose authority/cluster information.
        body=encode(validate('error_v3',dict(schema='unified.control.error.v3',request_id=None,code='AUTHENTICATION_UNAVAILABLE',reason='PROVIDER_UNAVAILABLE',retryable=False,retry_after_ms=None,evidence_refs=[])))
        start_response('503 Service Unavailable',[
            ('Content-Type','application/json'),('Content-Length',str(len(body))),
            ('Cache-Control','no-store')])
        return [] if environ.get('REQUEST_METHOD')=='HEAD' else [body]
