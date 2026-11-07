import unittest
import asyncio
from unified_system.control_mux.http_api import ControlMuxApp, ControlMuxRuntime
from unified_system.control_mux.commands import RawRequest
from unified_system.control_mux.codec import decode, validate
class DefaultClosedTests(unittest.TestCase):
    def test_missing_native_provider_never_reads_body_or_authority(self):
        class Bomb:
            def read(self,*args):raise AssertionError('unadmitted body read')
        for method,path in [('POST','/control/v3/connections'),('GET','/control/v3/commands/11111111-1111-4111-8111-111111111111')]:
            response=[]
            result=ControlMuxApp()({'REQUEST_METHOD':method,'PATH_INFO':path,'wsgi.input':Bomb()},lambda status,headers:response.append((status,headers)))
            self.assertTrue(response[0][0].startswith('503 '))
            self.assertIn(b'AUTHENTICATION_UNAVAILABLE',b''.join(result))
    def test_error_envelope_and_head(self):
        for method in ('GET','HEAD'):
            response=[]
            result=b''.join(ControlMuxApp()({'REQUEST_METHOD':method},lambda status,headers:response.append((status,dict(headers)))))
            if method=='HEAD':self.assertEqual(result,b'')
            else:
                value=validate('error_v3',decode(result))
                self.assertEqual(value['reason'],'PROVIDER_UNAVAILABLE')
            self.assertGreater(int(response[0][1]['Content-Length']),0)
    def test_head_has_no_body(self):
        result=ControlMuxApp()({'REQUEST_METHOD':'HEAD'},lambda *args:None)
        self.assertEqual(b''.join(result),b'')
    def test_async_runtime_missing_native_provider_closed(self):
        request=RawRequest('POST','/control/v3/connections',(),b'not-json',object())
        result=asyncio.run(ControlMuxRuntime().handle(request))
        self.assertEqual(result.status,503)
        self.assertEqual(validate('error_v3',decode(result.body))['code'],'AUTHENTICATION_UNAVAILABLE')
if __name__=='__main__':unittest.main()
