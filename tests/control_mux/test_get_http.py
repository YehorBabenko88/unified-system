import asyncio,unittest
from unified_system.control_mux.commands import RawRequest,NativeAdmissionError
from unified_system.control_mux.http_api import ControlMuxRuntime
from unified_system.control_mux.codec import decode
ORIGINAL='11111111-1111-4111-8111-111111111111'
QUERY='22222222-2222-4222-8222-222222222222'
class DenyNativeParsingProbe:
    # Unit parser probe; never authenticates or returns a context/receipt.
    def __init__(self):self.operations=[]
    def resolve(self,request,operation):
        self.operations.append(operation);raise NativeAdmissionError('UNAUTHENTICATED')
class GetParsingTests(unittest.TestCase):
    def request(self,method='GET',headers=None,body=b''):
        return RawRequest(method,'/control/v3/commands/'+ORIGINAL,tuple(headers or [(b'X-Request-ID',QUERY.encode())]),body,object())
    def handle(self,request):
        self.native=DenyNativeParsingProbe();return asyncio.run(ControlMuxRuntime(admission=self.native).handle(request))
    def test_missing_native_provider_closed_before_request_fields(self):
        response=asyncio.run(ControlMuxRuntime().handle(self.request(body=object())))
        self.assertEqual(response.status,503);self.assertEqual(decode(response.body)['code'],'AUTHENTICATION_UNAVAILABLE')
    def test_get_uses_only_existing_get_command_operation(self):
        response=self.handle(self.request());self.assertEqual(response.status,401)
        self.assertEqual(self.native.operations,['GET_COMMAND'])
    def test_original_query_uuid_alias_rejected(self):
        self.assertEqual(self.handle(self.request(headers=[(b'X-Request-ID',ORIGINAL.encode())])).status,400)
        self.assertEqual(self.native.operations,[])
    def test_nonempty_or_ambiguous_get_framing_rejected(self):
        for headers,body in [([(b'X-Request-ID',QUERY.encode()),(b'Content-Length',b'1')],b'x'), ([(b'X-Request-ID',QUERY.encode()),(b'Content-Type',b'application/json')],b''), ([(b'X-Request-ID',QUERY.encode()),(b'Content-Length',b'00')],b'')]:
            self.assertEqual(self.handle(self.request(headers=headers,body=body)).status,400)
            self.assertEqual(self.native.operations,[])
    def test_get_command_only_headers_rejected(self):
        for header in (b'Idempotency-Key',b'X-Expected-Connection-Epoch',b'X-Expected-Subscription-Epoch'):
            self.assertEqual(self.handle(self.request(headers=[(b'X-Request-ID',QUERY.encode()),(header,b'1')])).status,400)
    def test_wrong_method_has_get_allow(self):
        response=self.handle(self.request(method='POST'));self.assertEqual(response.status,405)
        self.assertEqual(dict(response.headers)['Allow'],'GET');self.assertEqual(self.native.operations,[])
    def test_typed_get_native_errors_preserve_cause_and_query(self):
        for kind,status,code in [('UNAUTHENTICATED',401,'UNAUTHENTICATED'),('SESSION_EXPIRED',401,'SESSION_EXPIRED'),('FORBIDDEN',403,'FORBIDDEN'),('UNAVAILABLE',503,'AUTHENTICATION_UNAVAILABLE')]:
            class Probe:
                def resolve(self,*args):raise NativeAdmissionError(kind)
            response=asyncio.run(ControlMuxRuntime(admission=Probe()).handle(self.request()))
            self.assertEqual((response.status,decode(response.body)['code'],decode(response.body)['request_id']),(status,code,QUERY))
        class Untyped:
            def resolve(self,*args):raise PermissionError('SESSION_EXPIRED')
        response=asyncio.run(ControlMuxRuntime(admission=Untyped()).handle(self.request()))
        self.assertEqual(response.status,503);self.assertEqual(decode(response.body)['request_id'],QUERY)
    def test_unknown_native_metadata_types_and_wrong_returns_unavailable(self):
        for kind in (None,True,1,'OTHER',{'kind':'SESSION_EXPIRED'}):
            with self.assertRaises(ValueError):NativeAdmissionError(kind)
        class Derived(NativeAdmissionError):pass
        bad=NativeAdmissionError('SESSION_EXPIRED');bad.kind={'untrusted':'SESSION_EXPIRED'}
        foreign=RuntimeError('SESSION_EXPIRED');foreign.kind='SESSION_EXPIRED'
        for error in (Derived('SESSION_EXPIRED'),bad,foreign):
            class Probe:
                def resolve(self,*args):raise error
            response=asyncio.run(ControlMuxRuntime(admission=Probe()).handle(self.request()))
            self.assertEqual(response.status,503);self.assertEqual(decode(response.body)['request_id'],QUERY)
        class Wrong:
            def resolve(self,*args):return object()
        self.assertEqual(asyncio.run(ControlMuxRuntime(admission=Wrong()).handle(self.request())).status,503)
    def test_missing_provider_query_correlation_without_body_access(self):
        response=asyncio.run(ControlMuxRuntime().handle(self.request(body=object())))
        self.assertEqual((response.status,decode(response.body)['request_id']),(503,QUERY))
        response=asyncio.run(ControlMuxRuntime().handle(self.request(headers=[(b'X-Request-ID',b'bad')],body=object())))
        self.assertIsNone(decode(response.body)['request_id'])
    def test_duplicate_correlation_header_rejected(self):
        response=self.handle(self.request(headers=[(b'X-Request-ID',QUERY.encode()),(b'x-request-id',QUERY.encode())]))
        self.assertEqual(response.status,400);self.assertEqual(self.native.operations,[])
if __name__=='__main__':unittest.main()
