import unittest
from unified_system.control_mux.http_api import ControlMuxApp
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
if __name__=='__main__':unittest.main()
