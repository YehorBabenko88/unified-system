"""Pure read-only WSGI dashboard; no listener is created at import."""
import html
import json
import re
from .model import need
from .sources import REPOSITORIES

CSS = b'''body{margin:0;background:#101820;color:#e4edf5;font:15px system-ui,sans-serif}
header,main{max-width:1400px;margin:auto;padding:24px}header{border-bottom:1px solid #364553}
h1{font-size:28px;margin:0 0 12px}h2{font-size:21px;padding-top:14px}nav a{color:#9bd3f5;margin-right:18px}
section{margin-bottom:28px}table{border-collapse:collapse;width:100%;background:#162330}
td,th{padding:9px 12px;text-align:left;border-bottom:1px solid #304251;vertical-align:top}
th{font-size:12px;letter-spacing:.05em;text-transform:uppercase;color:#99acbc}
code{font:12px ui-monospace,monospace;overflow-wrap:anywhere}.PASS{color:#84d4a0}.FAIL{color:#ff9696}
.BLOCKED{color:#f5bf72}.STALE{color:#d8b2f2}.UNKNOWN{color:#9aabb9}.note{color:#a8b8c6}
.nodes{display:grid;grid-template-columns:repeat(auto-fit,minmax(390px,1fr));gap:18px}
small{font-size:11px;color:#9aabb9}p{line-height:1.55}a{color:#9bd3f5}'''


def esc(value): return html.escape(str(value), quote=True)


def status_cell(row):
    state = row.get('status', 'UNKNOWN')
    return '<span class="' + esc(state) + '">' + esc(state) + '</span>'


def public_evidence_link(row):
    subject = row.get('subject'); field = row.get('field')
    if type(subject) is not str or field not in ('RUN_STATUS','PR_STATUS'): return ''
    repository, separator, identifier = subject.rpartition('#')
    if not separator or repository not in REPOSITORIES or not re.fullmatch('[1-9][0-9]{0,14}',identifier): return ''
    route = 'actions/runs/' if field == 'RUN_STATUS' else 'pull/'
    url = 'https://github.com/'+repository+'/'+route+identifier
    return '<br><a rel="noreferrer" href="'+url+'">Public evidence</a>'


def rows_table(rows):
    parts = ['<table><tr><th>Subject / field</th><th>Status</th><th>Observation / last success</th><th>Evidence / source version</th></tr>']
    for row in rows:
        evidence = row.get('evidence') or {}
        value = json.dumps(row.get('value'), sort_keys=True) if row.get('value') is not None else ''
        parts.append('<tr><td>' + esc(row.get('subject', '')) + '<br><code>' + esc(row.get('field', '')) +
            '</code><br>' + esc(value) + '</td><td>' + status_cell(row) + '<br><small>' + esc(row.get('mode', '')) +
            '</small></td><td><small>' + esc(row.get('observed_at') or 'Not observed') + '<br>Last success: ' +
            esc(row.get('last_successful_observation') or 'None') + '</small></td><td><small>' +
            esc(evidence.get('source', 'None')) + '</small><br><code>' + esc(evidence.get('sha256', '')) +
            '<br>' + esc(row.get('source_version') or '') + '</code>' + public_evidence_link(row) + '</td></tr>')
    if not rows: parts.append('<tr><td colspan="4">UNKNOWN — no admitted observation</td></tr>')
    return ''.join(parts) + '</table>'


def render(snapshot, *, source_head=None):
    need(source_head is None or (type(source_head) is str and re.fullmatch('[a-f0-9]{40}',source_head)),
         'OBSERVER_CODE_SOURCE_PIN')
    sections = (('overview', 'Overview'), ('computers', 'Computers'), ('services', 'Services'),
        ('market_data', 'Market Data'), ('development', 'Development'), ('ci', 'CI'),
        ('acceptance', 'Acceptance'), ('events', 'Events'))
    parts = ['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        '<title>Unified Observer Dashboard</title><link rel="stylesheet" href="/app.css"></head><body><header>',
        '<h1>Unified Observer Dashboard</h1><p class="note">Read-only observations · Automatic repair disabled · No execution or trading authority</p><nav>']
    parts.extend('<a href="#' + key + '">' + title + '</a>' for key, title in sections)
    parts.append('</nav></header><main><section id="overview"><h2>Overview</h2><p>Last evidence update: <code>' +
        esc(snapshot.get('updated_at') or 'Never') + '</code></p><p class="note">Historical PASS is not current ONLINE. Synthetic evidence is not physical acceptance. LOCAL_UNATTESTED is not committed publication.</p>')
    parts.append('<p>Notification queue: <code>' + esc(json.dumps(snapshot.get('notifications', {}), sort_keys=True)) + '</code></p></section>')
    if source_head is not None:
        parts.append('<p><a rel="noreferrer" href="https://github.com/YehorBabenko88/unified-system/blob/' +
            source_head + '/unified_system/observer/dashboard.py">Immutable Observer code source</a></p>')
    parts.append('<section id="computers"><h2>Computers</h2><div class="nodes">')
    for node, fields in snapshot.get('computers', {}).items():
        rows = [dict(value, subject=node, field=field) for field, value in fields.items()]
        parts.append('<article><h3>' + esc(node) + '</h3>' + rows_table(rows) + '</article>')
    parts.append('</div></section>')
    for key, title in sections[2:-1]:
        note = '<p class="note">Bounded reported runs and PRs; this is not full-matrix CI qualification.</p>' if key == 'ci' else ''
        parts.append('<section id="' + key + '"><h2>' + title + '</h2>' + note + rows_table(snapshot.get(key, [])) + '</section>')
    parts.append('<section id="events"><h2>Events</h2><table><tr><th>Event</th><th>Subject</th><th>Status</th><th>Observed</th><th>Delivery</th><th>Transport</th></tr>')
    for row in snapshot.get('events', []):
        parts.append('<tr>' + ''.join('<td>' + esc(row.get(k, '')) + '</td>' for k in
            ('kind', 'subject', 'status', 'observed_at', 'delivery', 'transport')) + '</tr>')
    parts.append('</table></section></main></body></html>')
    return ''.join(parts).encode('utf-8')


class ObserverApp:
    def __init__(self, provider, *, source_head=None):
        self.provider, self.source_head = provider, source_head

    def __call__(self, environ, start_response):
        method, path = environ.get('REQUEST_METHOD'), environ.get('PATH_INFO')
        status, content_type = 200, 'application/json; charset=utf-8'
        if method != 'GET': status, body = 405, b'{"error":"METHOD_NOT_ALLOWED"}'
        elif environ.get('QUERY_STRING') or environ.get('CONTENT_LENGTH') not in (None, '', '0'):
            status, body = 400, b'{"error":"QUERY_OR_BODY_NOT_SUPPORTED"}'
        elif path == '/app.css': body, content_type = CSS, 'text/css; charset=utf-8'
        elif path == '/healthz':
            try:
                snapshot = self.provider()
                if snapshot.get('read_only') is not True: raise ValueError('STATE_UNAVAILABLE')
                body = b'{"observer":"AVAILABLE","read_only":true,"node_health":"NOT_ASSERTED"}'
            except Exception:
                status, body = 503, b'{"observer":"UNAVAILABLE","read_only":true}'
        elif path in ('/', '/api/status'):
            try:
                snapshot = self.provider()
                if path == '/': body, content_type = render(snapshot, source_head=self.source_head), 'text/html; charset=utf-8'
                else: body = json.dumps(snapshot, sort_keys=True, allow_nan=False).encode('utf-8')
                if len(body) > 1048576: raise ValueError('RESPONSE_BOUND')
            except Exception:
                status, body = 503, b'{"error":"OBSERVER_STATE_UNAVAILABLE"}'
        else: status, body = 404, b'{"error":"NOT_FOUND"}'
        labels = {200:'OK', 400:'Bad Request', 404:'Not Found', 405:'Method Not Allowed', 503:'Service Unavailable'}
        headers = [('Content-Type', content_type), ('Content-Length', str(len(body))), ('Cache-Control', 'no-store'),
                   ('X-Content-Type-Options', 'nosniff'), ('Content-Security-Policy',
                    "default-src 'none'; style-src 'self'; frame-ancestors 'none'; base-uri 'none'")]
        if status == 405: headers.append(('Allow', 'GET'))
        start_response(str(status) + ' ' + labels[status], headers)
        return [body]
