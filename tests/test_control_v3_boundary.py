"""Experimental source/loopback fixture tests, never native/Consul admission."""
import io
import json
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from unified_system.control_v3_boundary import ControlV3App, parse_request, BoundaryError
from tests.control_v3.fixture_server import fixture_server, FixtureComposition

ROOT='/control/experimental/v3/'
UUID='11111111-1111-4111-8111-111111111111'
QUERY='scope=CONTROL&dataset_id=~&source_id=~&partition_id=~'


def environ(method='GET',path=ROOT+'snapshot',query=QUERY,body=b'',**extra):
    e=dict(REQUEST_METHOD=method,PATH_INFO=path,QUERY_STRING=query,CONTENT_LENGTH=str(len(body)),
           **{'wsgi.input':io.BytesIO(body)})
    e.update(extra);return e


def call(app,e):
    captured=[]
    body=b''.join(app(e,lambda s,h:captured.append((int(s[:3]),dict(h)))))
    status,headers=captured[0]
    return status,headers,json.loads(body) if body else None


class ControlV3Tests(unittest.TestCase):
    def test_default_app_no_activation_arguments(self):
        for kwargs in ({'provider':True},{'principal':{'actor_id':'operator'}},{'testing':True}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(TypeError):ControlV3App(**kwargs)

    def test_default_missing_identity_503_even_forged_headers(self):
        e=environ(HTTP_AUTHORIZATION='Bearer forged',HTTP_X_PRINCIPAL='administrator',
                  HTTP_X_AUTHORITY='true',REMOTE_USER='Administrator')
        status,_,value=call(ControlV3App(),e)
        self.assertEqual((status,value['code']),(503,'AUTHENTICATION_UNAVAILABLE'))
        self.assertNotIn('resources',value)

    def test_capabilities_constant_no_node_or_live(self):
        status,_,v=call(ControlV3App(),environ(path=ROOT+'capabilities',query=''))
        self.assertEqual(status,200);self.assertFalse(v['native_admission'])
        self.assertFalse(v['snapshots_available']);self.assertNotIn('nodes',v)

    def test_final_and_v1_namespaces_are_not_experimental_aliases(self):
        for path in ('/control/v3/snapshot','/control/v1/snapshot'):
            with self.subTest(path=path):self.assertEqual(call(ControlV3App(),environ(path=path,query=''))[0],404)

    def test_canonical_selector_shapes(self):
        for q in (QUERY,f'scope=DATASET&dataset_id={UUID}&source_id=~&partition_id=~',
                  f'scope=DATASET&dataset_id={UUID}&source_id=bybit&partition_id=~',
                  f'scope=DATASET&dataset_id={UUID}&source_id=bybit&partition_id=p1'):
            with self.subTest(q=q):self.assertEqual(parse_request(environ(query=q)).route,'snapshot')

    def test_selector_null_literal_is_not_null_token(self):
        q=f'scope=DATASET&dataset_id={UUID}&source_id=null&partition_id=~'
        self.assertEqual(parse_request(environ(query=q)).selector.source_id,'null')

    def test_ambiguous_selector_rejected_before_provider(self):
        for q in (QUERY+'&scope=CONTROL',QUERY.replace('~','%7E',1),QUERY.replace('source_id=~','source_id='),
                  QUERY.replace('&',';'),QUERY.replace('source_id=~&partition_id=~','partition_id=~&source_id=~'),
                  f'scope=DATASET&dataset_id={UUID}&source_id=~&partition_id=p1'):
            with self.subTest(q=q):self.assertEqual(call(ControlV3App(),environ(query=q))[0],400)

    def test_bad_framing_never_reads_body(self):
        class Fail:
            def read(self,n):raise AssertionError('must reject before body')
        for extra in ({'HTTP_TRANSFER_ENCODING':'chunked'},{'CONTENT_LENGTH':'00'},
                      {'CONTENT_LENGTH':'1,1'},{'CONTENT_LENGTH':'16385'},
                      {'wsgi.input_terminated':True}):
            with self.subTest(extra=extra):
                e=environ(**extra);e['wsgi.input']=Fail()
                self.assertEqual(call(ControlV3App(),e)[0],400)

    def test_get_body_and_encoded_raw_path_denied(self):
        self.assertEqual(call(ControlV3App(),environ(body=b'x'))[0],400)
        self.assertEqual(call(ControlV3App(),environ(RAW_URI=ROOT+'%73napshot?'+QUERY))[0],400)

    def test_epoch_and_stream_identity_canonical(self):
        base=environ(path=ROOT+'events',query='cursor=abc',HTTP_X_EXPECTED_CONNECTION_EPOCH='1',
            HTTP_X_EXPECTED_SEQUENCE='1',HTTP_X_STREAM_ATTEMPT_ID=UUID)
        self.assertEqual(parse_request(base).expected_epoch,'1')
        for value in ('0','01','-1','9223372036854775808','true'):
            with self.subTest(value=value):
                e=dict(base,HTTP_X_EXPECTED_CONNECTION_EPOCH=value)
                self.assertEqual(call(ControlV3App(),e)[0],400)

    def test_empty_delete_digest_binds_target_method_epoch(self):
        def p(target=UUID,epoch='1',method='DELETE'):
            return parse_request(environ(method=method,path=ROOT+'connections/'+target,query='',
                HTTP_X_REQUEST_ID=UUID,HTTP_IDEMPOTENCY_KEY='same',HTTP_X_EXPECTED_CONNECTION_EPOCH=epoch))
        self.assertNotEqual(p().command_digest,p(epoch='2').command_digest)
        self.assertNotEqual(p().command_digest,p(target='22222222-2222-4222-8222-222222222222').command_digest)

    def test_valid_post_and_delete_parse_but_never_admit(self):
        body=json.dumps(dict(schema='unified.control-open.experimental.v3',request_id=UUID,
            role='OPERATOR_CONTROL',app_instance_id=UUID,enrollment_revision='1'),sort_keys=True,separators=(',',':')).encode()
        for e in (environ(method='POST',path=ROOT+'connections',query='',body=body,CONTENT_TYPE='application/json',
                    HTTP_X_REQUEST_ID=UUID,HTTP_IDEMPOTENCY_KEY='same'),
                  environ(method='DELETE',path=ROOT+'connections/'+UUID,query='',HTTP_X_REQUEST_ID=UUID,
                    HTTP_IDEMPOTENCY_KEY='same',HTTP_X_EXPECTED_CONNECTION_EPOCH='1')):
            with self.subTest(method=e['REQUEST_METHOD']):
                status,_,v=call(ControlV3App(),e);self.assertEqual((status,v['code']),(503,'ADMISSION_UNAVAILABLE'))

    def test_duplicate_noncanonical_or_mismatched_post_denied(self):
        for body in (b'{"request_id":"x","request_id":"x"}',b' {}',b'{"schema":"unknown"}'):
            with self.subTest(body=body):
                self.assertEqual(call(ControlV3App(),environ(method='POST',path=ROOT+'connections',query='',body=body,
                    CONTENT_TYPE='application/json',HTTP_X_REQUEST_ID=UUID,HTTP_IDEMPOTENCY_KEY='same'))[0],400)

    def test_wrong_method_and_head_body(self):
        s,h,_=call(ControlV3App(),environ(method='POST',path=ROOT+'snapshot'))
        self.assertEqual(s,405);self.assertEqual(h['Allow'],'GET')
        s,h,b=call(ControlV3App(),environ(method='HEAD',path=ROOT+'capabilities',query=''))
        self.assertEqual(s,405);self.assertIsNone(b)

    def test_real_loopback_default_http_503(self):
        with fixture_server(ControlV3App()) as url:
            with self.assertRaises(HTTPError) as error:urlopen(url+ROOT+'snapshot?'+QUERY,timeout=2)
            self.assertEqual(error.exception.code,503)

    def test_real_loopback_synthetic_snapshot_is_untrusted(self):
        with fixture_server(FixtureComposition()) as url:
            with urlopen(url+ROOT+'snapshot?'+QUERY,timeout=2) as response:
                data=json.load(response)
                self.assertEqual(response.headers['X-Evidence-Class'],'SYNTHETIC_LOOPBACK_FIXTURE')
                self.assertEqual(data['trust'],'UNTRUSTED_PROVIDER_CLAIM');self.assertFalse(data['native_admission'])
                self.assertEqual(data['resources'][0]['node_id'],'PC3')

    def test_denied_identity_is_401(self):
        self.assertEqual(call(FixtureComposition(identity_denied=True),environ())[0],401)

    def test_missing_authority_is_503(self):
        s,_,v=call(FixtureComposition(authority_missing=True),environ())
        self.assertEqual((s,v['code']),(503,'AUTHORITY_UNAVAILABLE'))

    def test_identity_revoked_during_read_discloses_no_resources(self):
        s,_,v=call(FixtureComposition(revoke_during_read=True),environ())
        self.assertEqual(s,401);self.assertNotIn('resources',v)

    def test_cross_view_or_scope_claim_rejected(self):
        for mode in ('wrong_view','wrong_scope','bad_root','oversize'):
            with self.subTest(mode=mode):
                self.assertEqual(call(FixtureComposition(mode=mode),environ())[0],503)

    def test_real_loopback_finite_sse_fixture_has_exact_framing(self):
        with fixture_server(FixtureComposition()) as url:
            req=Request(url+ROOT+'events?cursor=fixture_cursor',headers={'X-Expected-Connection-Epoch':'1',
                'X-Expected-Sequence':'1','X-Stream-Attempt-ID':UUID})
            with urlopen(req,timeout=2) as response:
                b=response.read();self.assertEqual(response.headers['Content-Type'],'text/event-stream')
                self.assertTrue(b.startswith(b'data: {'));self.assertTrue(b.endswith(b'\n\n'))
                self.assertNotIn(b'event:',b);self.assertIn(b'UNTRUSTED_PROVIDER_CLAIM',b)

    def test_outer_event_gap_or_epoch_view_mismatch_rejected_atomically(self):
        e=environ(path=ROOT+'events',query='cursor=fixture_cursor',HTTP_X_EXPECTED_CONNECTION_EPOCH='1',
            HTTP_X_EXPECTED_SEQUENCE='1',HTTP_X_STREAM_ATTEMPT_ID=UUID)
        for mode in ('event_gap','event_epoch','wrong_view','event_liveness_authority'):
            with self.subTest(mode=mode):
                s,h,v=call(FixtureComposition(mode=mode),dict(e));self.assertEqual(s,503)
                self.assertEqual(h['Content-Type'],'application/json');self.assertNotIn('resources',v)

    def test_identity_provider_exception_returns_bounded_503(self):
        fixture=FixtureComposition()
        def fail(request):raise RuntimeError('secret internal fixture detail')
        fixture.resolve=fail
        status,_,value=call(fixture,environ())
        self.assertEqual((status,value['code']),(503,'AUTHENTICATION_UNAVAILABLE'))
        self.assertNotIn('secret',json.dumps(value))

    def test_body_stream_io_failure_is_400(self):
        class Fail:
            def read(self,n):raise OSError('closed body')
        e=environ(method='POST',path=ROOT+'connections',query='',body=b'{}',CONTENT_TYPE='application/json',
            HTTP_X_REQUEST_ID=UUID,HTTP_IDEMPOTENCY_KEY='same');e['wsgi.input']=Fail()
        self.assertEqual(call(ControlV3App(),e)[0],400)

    def test_short_body_is_400(self):
        e=environ(method='POST',path=ROOT+'connections',query='',body=b'{}',CONTENT_TYPE='application/json',
            HTTP_X_REQUEST_ID=UUID,HTTP_IDEMPOTENCY_KEY='same');e['CONTENT_LENGTH']='3'
        self.assertEqual(call(ControlV3App(),e)[0],400)

    def test_provider_failure_reason_cannot_inject_error_abi(self):
        from unified_system.control_v3_read_adapter import ReadFailure
        fixture=FixtureComposition()
        def fail(context,selector):raise ReadFailure('secret_unregistered_error')
        fixture.snapshot=fail
        status,_,value=call(fixture,environ())
        self.assertEqual((status,value['code']),(503,'AUTHORITY_UNAVAILABLE'))

    def test_dict_boolean_provider_is_not_typed_dependency(self):
        from unified_system.control_v3_read_adapter import ControlReadAdapter
        for provider in (True,{},False):
            with self.subTest(provider=provider):
                with self.assertRaises(ValueError):ControlReadAdapter(identity=provider)

    def test_liveness_connection_id_cannot_hide_nested_authority(self):
        fixture=FixtureComposition();original=fixture.events
        def events(context,request):
            frames=original(context,request)
            frames[1]['payload']['connection_id']={'authority':'CURRENT','resources':['secret']}
            return frames
        fixture.events=events
        e=environ(path=ROOT+'events',query='cursor=fixture_cursor',HTTP_X_EXPECTED_CONNECTION_EPOCH='1',
            HTTP_X_EXPECTED_SEQUENCE='1',HTTP_X_STREAM_ATTEMPT_ID=UUID)
        self.assertEqual(call(fixture,e)[0],503)

    def test_aggregate_payload_work_bounded_before_serialization(self):
        import sys
        from unified_system.control_v3_read_adapter import bounded,ReadFailure
        value='x'
        for _ in range(6):value=[value]*5
        calls=0;previous=sys.gettrace()
        def trace(frame,event,arg):
            nonlocal calls
            if event=='call' and frame.f_code.co_name=='walk' and frame.f_code.co_filename.endswith('control_v3_read_adapter.py'):
                calls+=1
                if calls>4096:raise AssertionError('validation exceeded aggregate node budget')
            return trace
        try:
            sys.settrace(trace)
            with self.assertRaises(ReadFailure):bounded(value,128)
        finally:sys.settrace(previous)
        self.assertLessEqual(calls,4096)

    def test_identity_revalidation_exception_is_bounded_503(self):
        fixture=FixtureComposition();original=fixture.resolve;calls=0
        def resolve(request):
            nonlocal calls
            calls+=1
            if calls==2:raise TimeoutError('native bridge unavailable')
            return original(request)
        fixture.resolve=resolve
        status,headers,value=call(fixture,environ())
        self.assertEqual((status,value['code']),(503,'AUTHENTICATION_UNAVAILABLE'))
        self.assertEqual(headers['Cache-Control'],'no-store')


if __name__=='__main__':unittest.main()
