"""Read-only loopback bootstrap WSGI view over the existing progress journal.

No listener, browser launcher, installer controller, or handoff actuator. The
hosting server must enforce HTTP framing and reject unframed GET request bodies;
this application never reads request bodies or exposes mutation routes.
"""
import json
import re
from .installation_progress import InstallationProgress

_HTML='''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Unified installation progress</title><link rel="stylesheet" href="/bootstrap.css"><script src="/bootstrap.js" defer></script></head>
<body><main><p class="eyebrow">UNIFIED SYSTEM / LAB SIMULATION</p><h1>Installation progress</h1><p>This view reads local installation receipts. It does not install or start modules.</p>
<section aria-live="polite"><h2 id="status">Loading source</h2><p id="identity"></p><p id="phase"></p><p id="timestamp"></p><p id="counts"></p><progress id="progress" hidden max="100"></progress><p id="qualification">Installed: NOT_PROVEN / Readiness: NOT_PROVEN</p><p id="handoff">Terminan handoff is not configured or verified by this view.</p></section>
<section><h2>Controls</h2><p id="disabled-reason">Continue, Retry and Stop require an authenticated installer controller; none is connected.</p><div class="actions"><button disabled aria-describedby="disabled-reason">Continue</button><button disabled aria-describedby="disabled-reason">Retry</button><button disabled aria-describedby="disabled-reason">Stop</button></div></section>
<section><h2>Read-only diagnostics</h2><div class="actions"><button id="export">Export diagnostics</button><button id="view-error">View error</button></div><pre id="error" aria-live="polite">No source diagnostics loaded.</pre></section></main></body></html>'''

_JS='''"use strict";
(() => {
  let current = null;
  let unavailable = {status: "UNAVAILABLE", error_code: "SOURCE_UNAVAILABLE", authority: false};
  const element = id => document.getElementById(id);
  const text = (id, value) => { element(id).textContent = value; };
  function render(data) {
    current = data.status === "AVAILABLE" ? data.snapshot : null;
    const bar = element("progress");
    bar.hidden = true;
    bar.removeAttribute("value");
    text("counts", "No measured progress counts available.");
    if (!current) {
      text("status", "UNAVAILABLE"); text("identity", "Source unavailable");
      text("phase", "Phase unavailable"); text("timestamp", "Timestamp unavailable");
      text("error", "SOURCE_UNAVAILABLE"); return;
    }
    text("status", "Local receipts available");
    text("identity", "Installation " + current.installation_id + " / Node " + current.node_id);
    text("timestamp", "UTC milliseconds: " + (current.last_timestamp_ms === null ? "not recorded" : current.last_timestamp_ms) + " / Sequence " + current.sequence);
    const last = current.events.length ? current.events[current.events.length - 1] : null;
    text("phase", last ? last.phase + " / " + last.outcome : "No phase receipt recorded");
    text("error", last ? last.error_code : "NONE");
    if (last && Object.prototype.hasOwnProperty.call(last, "percentage")) {
      text("counts", last.done + " / " + last.total + " (" + last.percentage + "%)");
      bar.value = last.percentage; bar.hidden = false;
    }
  }
  async function refresh() {
    try {
      const response = await fetch("/api/v1/installation", {cache: "no-store", credentials: "omit", redirect: "error"});
      const data = await response.json();
      if (!response.ok || data.status !== "AVAILABLE") { render(unavailable); }
      else { render(data); }
    } catch (_) { render(unavailable); }
    window.setTimeout(refresh, 2000);
  }
  element("view-error").addEventListener("click", () => {
    const last = current && current.events.length ? current.events[current.events.length - 1] : null;
    text("error", current ? (last ? last.error_code : "NONE") : "SOURCE_UNAVAILABLE");
  });
  element("export").addEventListener("click", () => {
    const diagnostics = current ? {status: "AVAILABLE", snapshot: current} : unavailable;
    const url = URL.createObjectURL(new Blob([JSON.stringify(diagnostics, null, 2)], {type: "application/json"}));
    const link = document.createElement("a"); link.href = url; link.download = "unified-installation-diagnostics.json";
    document.body.appendChild(link); link.click(); link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  refresh();
})();'''

_CSS='''body{margin:0;background:#101820;color:#e9f0f4;font:16px/1.6 system-ui,sans-serif}main{max-width:860px;margin:3rem auto;padding:0 1.5rem}h1{font-size:2.4rem;line-height:1.2}h2{font-size:1.2rem}.eyebrow{color:#8bd6cd;letter-spacing:.12em;font-size:.8rem}section{border:1px solid #41505b;border-radius:12px;padding:1.4rem;margin:1.4rem 0;background:#17232d}button{background:#284c5f;color:white;border:1px solid #8ca1ae;border-radius:6px;padding:.7rem 1rem;font:inherit;cursor:pointer}button:disabled{opacity:.5;cursor:not-allowed}.actions{display:flex;gap:.8rem;flex-wrap:wrap}pre{white-space:pre-wrap;overflow-wrap:anywhere}progress{width:100%;accent-color:#8bd6cd}button:focus-visible{outline:3px solid #8bd6cd;outline-offset:3px}'''

MAX_JSON_RESPONSE_BYTES=1024*1024


def _bounded_json(data):
    body=bytearray()
    for chunk in json.JSONEncoder(sort_keys=True,separators=(',',':'),allow_nan=False).iterencode(data):
        encoded=chunk.encode('utf-8')
        if len(body)+len(encoded)>MAX_JSON_RESPONSE_BYTES:
            raise ValueError('bootstrap response exceeds limit')
        body.extend(encoded)
    return bytes(body)


_CSP="default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'; object-src 'none'"


class InstallationBootstrapApp:
    def __init__(self,progress,host):
        if type(progress) is not InstallationProgress or type(host) is not str:
            raise ValueError('invalid bootstrap source or host')
        match=re.fullmatch(r'127\.0\.0\.1:([1-9][0-9]{0,4})',host)
        if match is None or int(match[1])>65535:raise ValueError('invalid bootstrap host')
        self.progress=progress
        self.host=host

    def __call__(self,environ,start_response):
        code=200;kind='application/json; charset=utf-8'
        data={'status':'UNAVAILABLE','error_code':'SOURCE_UNAVAILABLE','authority':False}
        if environ.get('REQUEST_METHOD')!='GET':code=405
        elif (environ.get('HTTP_HOST')!=self.host or environ.get('QUERY_STRING','') or
              'HTTP_ORIGIN' in environ or 'HTTP_TRANSFER_ENCODING' in environ or
              environ.get('CONTENT_LENGTH','') not in ('','0') or environ.get('wsgi.input_terminated')):code=400
        else:
            path=environ.get('PATH_INFO')
            if path=='/':data=_HTML;kind='text/html; charset=utf-8'
            elif path=='/bootstrap.js':data=_JS;kind='application/javascript; charset=utf-8'
            elif path=='/bootstrap.css':data=_CSS;kind='text/css; charset=utf-8'
            elif path=='/api/v1/installation':
                try:data={'status':'AVAILABLE','snapshot':InstallationProgress.snapshot(self.progress)}
                except Exception:code=503
            else:code=404
        if code not in (200,503):data={'status':'UNAVAILABLE','error_code':{400:'REQUEST_REJECTED',404:'NOT_FOUND',405:'METHOD_NOT_ALLOWED'}[code],'authority':False}
        try:
            body=data.encode('utf-8') if type(data) is str else _bounded_json(data)
        except (ValueError,TypeError,OverflowError):
            code=503
            body=_bounded_json({'status':'UNAVAILABLE','error_code':'SOURCE_UNAVAILABLE','authority':False})
        headers=[('Content-Type',kind),('Content-Length',str(len(body))),('Cache-Control','no-store'),
            ('X-Content-Type-Options','nosniff'),('Content-Security-Policy',_CSP),
            ('Referrer-Policy','no-referrer'),('X-Frame-Options','DENY')]
        if code==405:headers.append(('Allow','GET'))
        labels={200:'OK',400:'Bad Request',404:'Not Found',405:'Method Not Allowed',503:'Service Unavailable'}
        start_response(str(code)+' '+labels[code],headers)
        return [body]
