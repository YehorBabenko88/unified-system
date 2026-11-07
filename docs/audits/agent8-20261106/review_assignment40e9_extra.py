import pathlib,subprocess
r=pathlib.Path.cwd();repo=r/'work/review-assignment40e9';o=r/'outputs/phase72'
s='''import asyncio,sys,pathlib,threading,json,uuid,copy,hashlib
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
root=pathlib.Path.cwd();sys.path[:0]=[str(root),str(root/'tests/coordination/assignment_v1')]
from grid.coordination import ConsulConfig,ConsulSessionAuthority
from grid.authority_assignment_v1 import AssignmentAuthority,AssignmentUnavailable,parse_runtime_policy
from grid.authority_runtime_v1 import canonical
from test_runtime_policy import policy
import jsonschema
calls=[]
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_PUT(self):
  body=self.rfile.read(int(self.headers.get('Content-Length','0')));calls.append(dict(path=self.path,body=json.loads(body)))
  self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length','2');self.end_headers();self.wfile.write(b'{}')
server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever);thread.start()
async def run():
 a=ConsulSessionAuthority(ConsulConfig(endpoints=('http://127.0.0.1:'+str(server.server_port),),namespace='unified/'+str(uuid.uuid4()),isolated_lab=True))
 try:
  b=AssignmentAuthority(a,str(uuid.uuid4()))
  try:await b._transaction([{'KV':{'Verb':'check-not-exists','Key':'a8-inert-probe'}}]);raise AssertionError('HTTP200EMPTY_ACCEPTED')
  except AssignmentUnavailable as e:assert str(e)=='NATIVE_TRANSACTION_OUTCOME_UNKNOWN'
  before=len(calls)
  class Provider:
   async def require_current(self,*a):raise AssertionError('UNAPPROVED_PROVIDER_CALLED')
   async def verify_records(self,*a):raise AssertionError('UNAPPROVED_PROVIDER_CALLED')
  b=AssignmentAuthority(a,str(uuid.uuid4()),native_provider=Provider())
  for operation in ['execute','reconcile']:
   try:
    if operation=='execute':await b.execute(b'{}',context=object(),leader=None)
    else:await b.reconcile(b'{}',context=object())
    raise AssertionError('PUBLIC_GRANTED')
   except AssignmentUnavailable:pass
  assert len(calls)==before
 finally:await a.close()
try:asyncio.run(run())
finally:server.shutdown();server.server_close();thread.join(3)
assert len(calls)==1 and not thread.is_alive()
schema=json.loads((root/'docs/coordination/assignment-v1/runtime-actor-policy-review2.schema.json').read_bytes());v=jsonschema.Draft202012Validator(schema);jsonschema.Draft202012Validator.check_schema(schema)
accepted=policy();accepted['revision']=str(2**63-1);assert v.is_valid(accepted) and parse_runtime_policy(canonical(accepted))==accepted
n=0
for revision in ['0','00','01','-1',str(2**63),'1\\n',True,1]:
 changed=dict(accepted,revision=revision);assert not v.is_valid(changed)
 try:parse_runtime_policy(canonical(changed));raise AssertionError('BAD_REVISION')
 except ValueError:pass
 n+=1
print(json.dumps(dict(actual_HTTP_200_empty_dict_refused=True,actual_HTTP_requests=calls,provider_method_shape_public_execute_and_reconcile_denied_without_IO=True,u63_max_accepted=True,negative_revisions=n,owned_server_stopped=True,scope='RAW_SUBSTRATE_AND_UNTRUSTED_POLICY_ONLY_NO_ASSIGNMENT_GRANT'),indent=2))
'''
(o/'extra-executed.py').write_text(s,encoding='utf-8');p=subprocess.run([str(r/'work/mux-independent-env/Scripts/python.exe'),'-I','-B','-c',s],cwd=repo,capture_output=True,timeout=60);(o/'extra.stdout.json').write_bytes(p.stdout);(o/'extra.stderr.log').write_bytes(p.stderr);assert p.returncode==0,p.stderr.decode(errors='replace');print(p.stdout.decode())
