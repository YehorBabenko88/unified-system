"""Pure P0 WSGI denial boundary, not an admitted Control API service.

No listener, identity verifier, backend, clock or activation switch. The P0 error
profile is intentionally distinct from Terminan Sync v1 and carries no authority.
"""
import json
import re


_ROOT = '/control/v1/'
_ID = r'[A-Za-z0-9][A-Za-z0-9._:-]{0,127}'
_DATASET = re.compile(_ROOT + r'datasets/' + _ID + r'/(?:snapshot|events)\Z')
_COMMAND = re.compile(_ROOT + r'commands/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}'
                      r'-[0-9a-f]{4}-[0-9a-f]{12}\Z')
_ROUTES = {
    _ROOT + 'capabilities': ('GET', None),
    _ROOT + 'snapshot': ('GET', 'AUTHENTICATION_UNAVAILABLE'),
    _ROOT + 'events': ('GET', 'AUTHENTICATION_UNAVAILABLE'),
    _ROOT + 'commands': ('POST', 'SAFETY_GATE_CLOSED'),
    _ROOT + 'sessions': ('POST', 'AUTHENTICATION_UNAVAILABLE'),
    _ROOT + 'reauth': ('POST', 'AUTHENTICATION_UNAVAILABLE'),
    _ROOT + 'confirmations': ('POST', 'SAFETY_GATE_CLOSED'),
    _ROOT + 'sessions/current': ('DELETE', 'AUTHENTICATION_UNAVAILABLE'),
}
_LABELS = {200: 'OK', 400: 'Bad Request', 404: 'Not Found',
           405: 'Method Not Allowed', 503: 'Service Unavailable'}


class ControlAPIReadOnlyApp:
    """No-argument deny-only application; credentials cannot enable a backend."""

    def __call__(self, environ, start_response):
        method = environ.get('REQUEST_METHOD')
        path = environ.get('PATH_INFO')
        query = environ.get('QUERY_STRING', '')
        length = environ.get('CONTENT_LENGTH', '')
        # No enabled route consumes a request body. Reject framing without ever
        # reading wsgi.input, even for malformed JSON or a streaming request.
        valid = (
            type(method) is str and re.fullmatch(r'[A-Z]{1,16}', method)
            and type(path) is str and 0 < len(path) <= 2048
            and re.fullmatch(r'/[A-Za-z0-9/._:-]*', path)
            and not any(part in ('.', '..') for part in path.split('/'))
            and type(query) is str and not query
            and type(length) is str and length in ('', '0')
            and 'HTTP_TRANSFER_ENCODING' not in environ
        )
        status, code, allowed = 400, 'INVALID_REQUEST', None
        if valid:
            route = _ROUTES.get(path)
            if route is None and (_DATASET.fullmatch(path) or _COMMAND.fullmatch(path)):
                route = ('GET', 'AUTHENTICATION_UNAVAILABLE')
            if route is None:
                status, code = 404, 'NOT_FOUND'
            elif method != route[0]:
                status, code, allowed = 405, 'METHOD_NOT_ALLOWED', route[0]
            elif route[1] is None:
                status, code = 200, None
            else:
                status, code = 503, route[1]

        if status == 200:
            result = {
                'schema': 'unified.control-capabilities.v1', 'api_version': 1,
                'profile': 'DENY_ONLY', 'authentication_available': False,
                'authority_reads_available': False, 'mutations_available': False,
                'snapshots_available': False, 'events_available': False,
            }
        else:
            result = {'schema': 'unified.control-error.p0.v1', 'code': code,
                      'retryable': False, 'request_id': None}
        body = json.dumps(result, sort_keys=True, separators=(',', ':'),
                          allow_nan=False).encode('ascii')
        headers = [('Content-Type', 'application/json'),
                   ('Content-Length', str(len(body))),
                   ('Cache-Control', 'no-store'),
                   ('X-Content-Type-Options', 'nosniff')]
        if allowed is not None:
            headers.append(('Allow', allowed))
        start_response(str(status) + ' ' + _LABELS[status], headers)
        # HEAD preserves response metadata, but HTTP forbids response content
        # even when this method or path was denied.
        return [] if method == 'HEAD' else [body]
