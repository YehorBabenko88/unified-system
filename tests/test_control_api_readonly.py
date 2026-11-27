"""P0 boundary tests: real WSGI responses, no server or production fixtures."""
import json
import unittest
from unittest.mock import patch

from unified_system.control_api_readonly import ControlAPIReadOnlyApp


class UnreadableBody:
    def read(self, *args):
        raise AssertionError('P0 must never read request bodies')


class ControlAPITest(unittest.TestCase):
    def request(self, method='GET', path='/control/v1/capabilities', **extra):
        environ = {'REQUEST_METHOD': method, 'PATH_INFO': path,
                   'QUERY_STRING': '', 'CONTENT_LENGTH': '',
                   'wsgi.input': UnreadableBody()}
        environ.update(extra)
        captured = []
        def start_response(status, headers):
            captured.append((status, dict(headers)))
        chunks = list(ControlAPIReadOnlyApp()(environ, start_response))
        self.assertEqual(len(captured), 1)
        self.assertTrue(all(type(chunk) is bytes for chunk in chunks))
        body = b''.join(chunks)
        status, headers = captured[0]
        self.assertLessEqual(len(body), 4096)
        self.assertEqual(headers['Content-Length'], str(len(body)))
        self.assertEqual(headers['Content-Type'], 'application/json')
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
        return int(status[:3]), headers, json.loads(body)

    def test_public_capabilities_never_claim_admitted_runtime(self):
        status, _, value = self.request()
        self.assertEqual(status, 200)
        self.assertEqual(value, {
            'schema': 'unified.control-capabilities.v1', 'api_version': 1,
            'profile': 'DENY_ONLY', 'authentication_available': False,
            'authority_reads_available': False, 'mutations_available': False,
            'snapshots_available': False, 'events_available': False})

    def test_all_protected_reads_are_unavailable_not_empty_success(self):
        for path in ('/control/v1/snapshot', '/control/v1/events',
                     '/control/v1/datasets/dataset-1/snapshot',
                     '/control/v1/datasets/dataset-1/events',
                     '/control/v1/commands/00000000-0000-4000-8000-000000000001'):
            with self.subTest(path=path):
                status, _, value = self.request(path=path)
                self.assertEqual(status, 503)
                self.assertEqual(value['code'], 'AUTHENTICATION_UNAVAILABLE')
                self.assertNotIn('resources', value)
                self.assertNotIn('cursor', value)

    def test_every_effect_route_stays_denied(self):
        for method, path, code in (
            ('POST', '/control/v1/commands', 'SAFETY_GATE_CLOSED'),
            ('POST', '/control/v1/sessions', 'AUTHENTICATION_UNAVAILABLE'),
            ('POST', '/control/v1/reauth', 'AUTHENTICATION_UNAVAILABLE'),
            ('POST', '/control/v1/confirmations', 'SAFETY_GATE_CLOSED'),
            ('DELETE', '/control/v1/sessions/current', 'AUTHENTICATION_UNAVAILABLE')):
            with self.subTest(path=path):
                status, _, value = self.request(method, path)
                self.assertEqual((status, value['code']), (503, code))

    def test_claimed_principal_cookie_and_truthy_flags_do_not_authenticate(self):
        with patch.dict('os.environ', {'CONTROL_API_ENABLED': 'true', 'ROLE': 'SystemOwner'}):
            status, _, value = self.request(path='/control/v1/snapshot',
                HTTP_AUTHORIZATION='Bearer secret-value', REMOTE_USER='Administrator',
                HTTP_X_ROLE='SystemOwner', HTTP_COOKIE='session=secret-value')
        self.assertEqual((status, value['code']), (503, 'AUTHENTICATION_UNAVAILABLE'))
        self.assertNotIn('secret-value', json.dumps(value))
        self.assertNotIn('Administrator', json.dumps(value))

    def test_no_provider_or_backend_activation_constructor(self):
        for name in ('provider', 'backend', 'verifier', 'enabled'):
            with self.subTest(name=name), self.assertRaises(TypeError):
                ControlAPIReadOnlyApp(**{name: True})

    def test_wrong_method_returns_allow_without_activation(self):
        status, headers, value = self.request('POST')
        self.assertEqual((status, value['code']), (405, 'METHOD_NOT_ALLOWED'))
        self.assertEqual(headers['Allow'], 'GET')

    def test_unknown_route_does_not_look_like_missing_auth(self):
        status, _, value = self.request(path='/control/v1/unknown')
        self.assertEqual((status, value['code']), (404, 'NOT_FOUND'))

    def test_queries_are_not_treated_as_implemented_resume_or_barrier(self):
        for path, query in (('/control/v1/capabilities', 'enabled=true'),
                            ('/control/v1/events', 'cursor=secret-cursor'),
                            ('/control/v1/datasets/d/snapshot', 'metadata_revision=1')):
            with self.subTest(path=path):
                status, _, value = self.request(path=path, QUERY_STRING=query)
                self.assertEqual((status, value['code']), (400, 'INVALID_REQUEST'))
                self.assertNotIn(query, json.dumps(value))

    def test_nonempty_and_ambiguous_body_framing_denied_without_read(self):
        for extra in ({'CONTENT_LENGTH': '1'}, {'CONTENT_LENGTH': '-1'},
                      {'CONTENT_LENGTH': '0,0'}, {'CONTENT_LENGTH': ' 0'},
                      {'CONTENT_LENGTH': '00'}, {'CONTENT_LENGTH': 'x'},
                      {'HTTP_TRANSFER_ENCODING': 'chunked'}):
            with self.subTest(extra=extra):
                status, _, value = self.request(**extra)
                self.assertEqual((status, value['code']), (400, 'INVALID_REQUEST'))

    def test_oversize_body_claim_rejected_before_buffering(self):
        status, _, value = self.request(CONTENT_LENGTH='32769')
        self.assertEqual((status, value['code']), (400, 'INVALID_REQUEST'))
        status, _, _ = self.request(CONTENT_LENGTH='9' * 10000)
        self.assertEqual(status, 400)

    def test_malformed_wsgi_fields_fail_closed(self):
        for extra in ({'PATH_INFO': None}, {'REQUEST_METHOD': None},
                      {'QUERY_STRING': None}, {'CONTENT_LENGTH': 0}):
            with self.subTest(extra=extra):
                status, _, value = self.request(**extra)
                self.assertEqual((status, value['code']), (400, 'INVALID_REQUEST'))

    def test_encoded_traversal_slashes_unicode_and_long_paths_are_invalid(self):
        for path in ('/control/v1/datasets/../snapshot',
                     '/control/v1/datasets/x%2Fy/snapshot',
                     '/control/v1/datasets/x\\y/snapshot',
                     '/control/v1/datasets/тест/snapshot',
                     '/control/v1/snapshot\x00', '/' + 'a' * 2048):
            with self.subTest(path=path):
                status, _, value = self.request(path=path)
                self.assertEqual((status, value['code']), (400, 'INVALID_REQUEST'))

    def test_error_envelope_has_no_fabricated_authority_or_request_identity(self):
        _, _, value = self.request(path='/control/v1/snapshot')
        self.assertEqual(value, {'schema': 'unified.control-error.p0.v1',
            'code': 'AUTHENTICATION_UNAVAILABLE', 'retryable': False,
            'request_id': None})

    def test_mutating_returned_json_cannot_enable_later_requests(self):
        _, _, value = self.request()
        value['mutations_available'] = True
        status, _, result = self.request('POST', '/control/v1/commands')
        self.assertEqual((status, result['code']), (503, 'SAFETY_GATE_CLOSED'))

    def test_boundary_does_not_open_files_sockets_or_read_system_time(self):
        with patch('builtins.open', side_effect=AssertionError('file access')), \
             patch('socket.socket', side_effect=AssertionError('socket access')), \
             patch('time.time', side_effect=AssertionError('clock access')):
            status, _, _ = self.request()
            denied, _, _ = self.request('POST', '/control/v1/commands')
        self.assertEqual((status, denied), (200, 503))

    def test_head_errors_never_send_a_response_body(self):
        for path, expected in (('/control/v1/capabilities', 405),
                               ('/control/v1/unknown', 404),
                               ('/control/v1/%bad', 400)):
            with self.subTest(path=path):
                captured = []
                response = ControlAPIReadOnlyApp()(
                    {'REQUEST_METHOD': 'HEAD', 'PATH_INFO': path},
                    lambda status, headers: captured.append((status, dict(headers))))
                self.assertEqual(int(captured[0][0][:3]), expected)
                self.assertEqual(b''.join(response), b'')
                self.assertEqual(captured[0][1]['Cache-Control'], 'no-store')
                self.assertLessEqual(int(captured[0][1]['Content-Length']), 4096)


if __name__ == '__main__':
    unittest.main()
