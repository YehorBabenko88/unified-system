import pathlib,subprocess
r=pathlib.Path.cwd();repo=r/'work/review-tlsfront37b3';o=r/'outputs/phase83'
s='''import pathlib,sys,socket,ssl,time,json
sys.path[:0]=[str(pathlib.Path.cwd()),str(pathlib.Path.cwd()/'tests'),str(pathlib.Path.cwd()/'tests/gateway_runtime')]
from test_front import FrontTests
from unified_system.gateway_runtime_composition import DisposableGatewayFront
FrontTests.setUpClass();case=FrontTests();case.setUp();checks=0
try:
 host=('127.0.0.1:'+str(case.front.address[1])).encode()
 def exchange(raw,wronguri=False):
  if wronguri:
   c=ssl.create_default_context(cafile=str(case.pki.root/'ca.pem'));c.check_hostname=False;c.load_cert_chain(str(case.pki.root/'wronguri.pem'),str(case.pki.root/'wronguri.key'));s=c.wrap_socket(socket.create_connection(case.front.address,timeout=1),server_hostname='localhost')
  else:s=case.connection()
  with s:
   s.settimeout(1);s.sendall(raw);parts=[]
   while data:=s.recv(8192):parts.append(data)
   return b''.join(parts)
 for method,path,extra in [(b'HEAD',b'/intelligence/v1/query',b'Content-Length: 32768\\r\\nAuthorization: ADMIN\\r\\n'),(b'HEAD',b'/unknown',b''),(b'HEAD',b'/intelligence/v1/capabilities',b'X-Padding: '+b'x'*8200+b'\\r\\n')]:
  raw=exchange(method+b' '+path+b' HTTP/1.1\\r\\nHost: '+host+b'\\r\\n'+extra+b'\\r\\n');headers,body=raw.split(b'\\r\\n\\r\\n',1);assert body==b'';checks+=1
 # Chain-valid but wrong identity URI is not Gateway authentication; protected route still503.
 raw=exchange(b'POST /intelligence/v1/query HTTP/1.1\\r\\nHost: '+host+b'\\r\\nContent-Length: 32768\\r\\n\\r\\n',wronguri=True);assert raw.startswith(b'HTTP/1.1 503') and b'CLIENT_ADMISSION_UNAVAILABLE' in raw;checks+=1
 for extra in [b'Content-Length: 0\\r\\ncontent-length: 0\\r\\n',b'Content-Length: +1\\r\\n',b'Content-Length: 01\\r\\n',b'Content-Length: 32769\\r\\n',b'X: a\\tb\\r\\n',b'Transfer-Encoding: identity\\r\\n',b''.join(b'X-'+str(i).encode()+b': a\\r\\n' for i in range(32))]:
  raw=exchange(b'GET /intelligence/v1/capabilities HTTP/1.1\\r\\nHost: '+host+b'\\r\\n'+extra+b'\\r\\n');assert raw.startswith(b'HTTP/1.1 400');checks+=1
 # Saturate only this disposable front with four own incomplete TLS handshakes.
 held=[socket.create_connection(case.front.address,timeout=1) for _ in range(4)]
 try:
  end=time.monotonic()+1
  while time.monotonic()<end:
   with case.front._lock:n=len(case.front._workers)
   if n==4:break
   time.sleep(.005)
  assert n==4
  with case.front._lock:owned_threads=tuple(case.front._workers)
  fifth=socket.create_connection(case.front.address,timeout=1)
  with fifth:
   fifth.settimeout(1)
   try:assert fifth.recv(1)==b''
   except ConnectionResetError:pass
  with case.front._lock:assert len(case.front._workers)<=4
  started=time.monotonic();case.front.close();elapsed=time.monotonic()-started;assert not case.front.is_alive() and elapsed<4
 finally:
  for sock in held:sock.close()
 assert not case.front.is_alive() and all(not t.is_alive() for t in owned_threads)
 try:
  probe=socket.create_connection(case.front.address,timeout=.3);probe.close();raise AssertionError('CLOSED_LISTENER_ACCEPTED')
 except (ConnectionRefusedError,TimeoutError):pass
 print(json.dumps(dict(scope='OWN_LOOPBACK_TLS_FRONT_ONLY_NO_CLIENT_IDENTITY',extra_HTTP_HEAD_chain_boundary_cases=checks,saturation_own_incomplete_TLS_clients=4,fifth_refused_before_worker=True,max_workers=4,shutdown_no_live_workers=True,retained_thread_objects_stopped=True,listener_connection_not_established_after_close=True,shutdown_seconds=round(elapsed,3),protected_without_body_and_wrongURI_chain='503_NO_AUTHENTICATION',no_owner_store_or_engine_invoked=True),indent=2))
finally:case.doCleanups();FrontTests.doClassCleanups();FrontTests.pki.doClassCleanups()
'''
(o/'extra-executed.py').write_text(s,encoding='utf-8');p=subprocess.run([str(r/'work/audit-venv/Scripts/python.exe'),'-I','-S','-B','-c',s],cwd=repo,capture_output=True,timeout=45);(o/'extra.stdout.json').write_bytes(p.stdout);(o/'extra.stderr.log').write_bytes(p.stderr);assert p.returncode==0,p.stderr;print(p.stdout.decode())
