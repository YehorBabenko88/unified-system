"""Exercise only the owned loopback static preview handler; no backend/API routes."""
import http.client,importlib.util,json,pathlib,threading
from http.server import ThreadingHTTPServer
ROOT=pathlib.Path(__file__).resolve().parents[1];source=ROOT/'work/review6-sync'
spec=importlib.util.spec_from_file_location('auditor_sync_preview',source/'terminan/sync/serve.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
server=ThreadingHTTPServer(('127.0.0.1',0),module.Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();port=server.server_port
cases=[]
try:
    for name,method,path,headers,expected in [
      ('asset','GET','/sync.html',{},200),('unknown_api','GET','/api/control',{},404),
      ('path_traversal','GET','/sync/../../README.md',{},404),('mutation','POST','/api/command',{},501),
      ('foreign_host','GET','/sync.html',{'Host':'evil.example'},403),
      ('foreign_origin','GET','/sync.html',{'Origin':'https://evil.example'},403)]:
        con=http.client.HTTPConnection('127.0.0.1',port,timeout=3);con.request(method,path,headers=headers);response=con.getresponse();body=response.read();actual=response.status
        if name=='asset':assert "connect-src 'none'" in response.getheader('Content-Security-Policy') and response.getheader('Cache-Control')=='no-store'
        con.close();assert actual==expected,(name,actual);cases.append({'case':name,'expected':expected,'actual':actual})
finally:server.shutdown();server.server_close();thread.join(5)
assert not thread.is_alive()
(ROOT/'outputs/phase7/static-server-review.json').write_text(json.dumps({'head':'166b85e888d7d0ade24bd945761ad501a94e060c','scope':'OWNED_LOOPBACK_STATIC_HANDLER_ONLY','cases':cases,'server_stopped':True,'runtime_api':'ABSENT','physical':'BLOCKED'},indent=2));print(json.dumps(cases))
