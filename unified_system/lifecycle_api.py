"""Additive read-only lifecycle WSGI boundary; no listener or mutating route."""
import json
from .lifecycle import validate, canonical

class ReadOnlyLifecycleApp:
    def __init__(self,provider=None):self.provider=provider
    def __call__(self,environ,start_response):
        data={'schema':'unified.lifecycle.v1','api_version':{'major':1,'minor':0},'producer':'unified-system',
              'mode':'PLAN_ONLY','status':'UNAVAILABLE','reason':'LIFECYCLE_UNAVAILABLE',
              'execution_authorized':False,'trading_authorized':False,'physical_acceptance':'NOT_RUN'}
        status=503
        if environ.get('REQUEST_METHOD')!='GET':status=405;data['reason']='METHOD_NOT_ALLOWED'
        elif environ.get('PATH_INFO')!='/internal/v1/lifecycle':status=404;data['reason']='NOT_FOUND'
        elif environ.get('QUERY_STRING'):status=400;data['reason']='QUERY_NOT_SUPPORTED'
        else:
            try:
                snapshot=self.provider() if self.provider else None
                if not isinstance(snapshot,dict):raise ValueError()
                core={k:v for k,v in snapshot.items() if k not in ('recovery','fleet')}
                validate(core)
                if snapshot.get('recovery') not in ('NONE','REVALIDATION_REQUIRED'):raise ValueError()
                if len(canonical(snapshot).encode())>1048576:raise ValueError()
                data=json.loads(canonical(snapshot));data['status']='AVAILABLE';status=200
            except Exception:pass
        body=json.dumps(data,sort_keys=True,allow_nan=False).encode()
        reason={200:'OK',400:'Bad Request',404:'Not Found',405:'Method Not Allowed',503:'Service Unavailable'}
        headers=[('Content-Type','application/json'),('Content-Length',str(len(body))),('Cache-Control','no-store'),('X-Content-Type-Options','nosniff')]
        if status==405:headers.append(('Allow','GET'))
        start_response(str(status)+' '+reason[status],headers)
        return [body]
