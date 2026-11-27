"""Inert source migration tests; audit-denied sockets/process/native calls."""
import ast,hashlib,importlib,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
import base64,types
from contextlib import contextmanager

class Audit:
 depth=0
 def __call__(self,event,args):
  if self.depth and (event.startswith('socket.') or event in ('subprocess.Popen','os.system','os.startfile','os.posix_spawn','os.fork') or event.startswith('ctypes.')):
   raise AssertionError('FORBIDDEN_NATIVE_EFFECT:'+event)
 def __enter__(self):self.depth+=1;return self
 def __exit__(self,*args):self.depth-=1
audit=Audit();sys.addaudithook(audit)

def complete(coroutine):
 try:coroutine.send(None)
 except StopIteration as done:return done.value
 finally:coroutine.close()
 raise AssertionError('unexpected asynchronous yield in inert fake')

@contextmanager
def inert_crypto_imports():
 """Import shape only; every crypto operation refuses, never fake validation."""
 names=['cryptography','cryptography.x509','cryptography.exceptions','cryptography.hazmat','cryptography.hazmat.primitives','cryptography.hazmat.primitives.hashes','cryptography.x509.oid']
 modules={name:types.ModuleType(name) for name in names}
 for module in modules.values():module.__path__=[]
 def forbidden(*args,**kwargs):raise AssertionError('CRYPTO_OPERATION_NOT_QUALIFIED')
 modules['cryptography'].x509=modules['cryptography.x509']
 modules['cryptography.exceptions'].InvalidSignature=type('InvalidSignature',(Exception,),{})
 modules['cryptography.exceptions'].UnsupportedAlgorithm=type('UnsupportedAlgorithm',(Exception,),{})
 modules['cryptography.hazmat.primitives'].hashes=modules['cryptography.hazmat.primitives.hashes']
 modules['cryptography.hazmat.primitives.hashes'].SHA256=forbidden
 modules['cryptography.x509'].load_der_x509_certificate=forbidden
 modules['cryptography.x509'].ExtensionNotFound=type('ExtensionNotFound',(Exception,),{})
 modules['cryptography.x509.oid'].ExtendedKeyUsageOID=types.SimpleNamespace(CLIENT_AUTH='client',SERVER_AUTH='server')
 with patch.dict(sys.modules,modules):yield

class RootAuthorityTests(unittest.TestCase):
 def test_root_modules_close_without_grid_imports(self):
  with audit,inert_crypto_imports():
   for name in ('consul_authority','authority_codec','research_authority'):
    module=importlib.import_module('unified_system.'+name)
    tree=ast.parse(Path(module.__file__).read_bytes())
    imports=[n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
    self.assertFalse(any(x and x.startswith('grid') for x in imports))
   broker=importlib.import_module('unified_system.gateway_research_identity')
   native=importlib.import_module('unified_system.gateway_native_negative')
   self.assertIs(broker.ConsulSessionAuthority,importlib.import_module('unified_system.consul_authority').ConsulSessionAuthority)
   actual=native._fixed_types()
   self.assertEqual(actual[0].__module__,'unified_system.consul_authority')
   self.assertEqual(actual[2].__module__,'unified_system.research_authority')
 def test_distinct_control_and_native_codecs_preserve_policy(self):
  from unified_system import consul_authority as control,authority_codec as native
  with audit:
   self.assertEqual(control.canonical({'token':3}),b'{"token":3}')
   self.assertEqual(native.canonical({'token':'3','flag':False}),b'{"flag":false,"token":"3"}')
   for bad in ({'token':3},{'token':3.0},{'x':'é'},{'x':[None]*33},{'x':'a'*16385}):
    with self.assertRaises(ValueError):native.canonical(bad)
   self.assertEqual(native.measure_native_plan([{'KV':{'Verb':'check-index','Key':'a','Index':3}}]).operations,1)
   for bad in ([],[{}]*65,[{'x':'a'*32769}]):
    with self.assertRaises(ValueError):native.measure_native_plan(bad)
 def test_core_does_not_include_grid_resource_factories(self):
  from unified_system import consul_authority as module
  self.assertFalse(hasattr(module,'floating_leader_guard'));self.assertFalse(hasattr(module,'coordinator_authority'))
 def test_source_mismatch_refuses_fixed_types(self):
  from unified_system import gateway_native_negative as native
  with audit,inert_crypto_imports(),patch.dict(native._PINS,{'unified_system.consul_authority':'0'*64}):
   with self.assertRaises(native.NativeNegativeDenied):native._fixed_types()

class LeaseControlTests(unittest.TestCase):
 def test_original_acquire_current_renew_release_never_deletes_fence(self):
  from unified_system import consul_authority as c
  sid='11111111-1111-4111-8111-111111111111';namespace='unified/22222222-2222-4222-8222-222222222222'
  raw=c.canonical({'owner':'node1','session_id':sid,'namespace':namespace})
  row={'Key':namespace+'/leader','Session':sid,'ModifyIndex':7,'Value':base64.b64encode(raw).decode()}
  values=[{'ID':sid},True,[row],[row],[{'ID':sid}],[row],True]
  class Client:
   def __init__(self):self.calls=[]
   async def request(self,method,path,**kwargs):
    self.calls.append((method,path,kwargs));value=values.pop(0)
    return types.SimpleNamespace(status_code=200,content=b'{}',json=lambda:value)
  async def wait(coroutine,timeout):return await coroutine
  client=Client();clock=[0.]
  authority=c.ConsulSessionAuthority(c.ConsulConfig(('http://127.0.0.1:1',),namespace,isolated_lab=True),client=client,clock=lambda:clock[0])
  with audit,patch.object(c.asyncio,'wait_for',wait):
   lease=complete(authority.acquire('node1'));self.assertEqual(lease.token,7)
   self.assertTrue(complete(authority.validate(lease)))
   clock[0]=5;self.assertTrue(complete(authority.renew(lease)))
   complete(authority.release(lease));self.assertFalse(complete(authority.validate(lease)))
  self.assertFalse(any(method=='DELETE' for method,_,_ in client.calls))
  self.assertTrue(client.calls[-1][1].endswith('/session/destroy/'+sid))
 def test_native_response_limits_conflict_and_missing_preserved(self):
  from unified_system import consul_authority as c
  class Client:
   response=None
   async def request(self,*args,**kwargs):return self.response
  async def wait(coroutine,timeout):return await coroutine
  client=Client();authority=c.ConsulSessionAuthority(c.ConsulConfig(('http://127.0.0.1:1',),'owned',isolated_lab=True),client=client)
  for status,content,error in [(409,b'{}',c.CoordinationLost),(200,b'x'*65537,c.CoordinationUnavailable)]:
   client.response=types.SimpleNamespace(status_code=status,content=content,json=lambda:{})
   with audit,patch.object(c.asyncio,'wait_for',wait),self.assertRaises(error):complete(authority._request('GET','/x'))
  client.response=types.SimpleNamespace(status_code=404,content=b'',json=lambda:None)
  with audit,patch.object(c.asyncio,'wait_for',wait):self.assertIsNone(complete(authority._request('GET','/x',missing_ok=True)))
 def test_lease_deadline_and_foreign_shape_refuse_without_request(self):
  from unified_system import consul_authority as c
  class Client:
   async def request(self,*a,**k):raise AssertionError('expired/foreign lease requested')
  a=c.ConsulSessionAuthority(c.ConsulConfig(('http://127.0.0.1:1',),'owned',isolated_lab=True),client=Client(),clock=lambda:20)
  lease=c.ConsulLease('x','session',7);a._sessions['session']=lease;a._deadlines['session']=10
  with audit:self.assertFalse(complete(a.validate(lease)));self.assertFalse(complete(a.validate({'session_id':'session'})))

class SnapshotTests(unittest.TestCase):
 def fixture(self):
  from unified_system import consul_authority as c,research_authority as r
  import httpx
  authority=object.__new__(c.ConsulSessionAuthority);authority.config=types.SimpleNamespace(namespace='unified/11111111-1111-4111-8111-111111111111')
  authority._owns_client=True;authority.client=object.__new__(httpx.AsyncClient);authority.client._transport=object.__new__(httpx.AsyncHTTPTransport)
  key=authority.config.namespace+'/runtime-v1/test'
  record={'KV':dict(Key=key,ModifyIndex=0,CreateIndex=0,Value=None)}
  response=dict(KnownLeader=True,ResultsFilteredByACLs=False,Results=[record])
  async def request(*args,**kwargs):return response
  authority._request=request
  return r,authority,r._ConsulSnapshot(authority,'22222222-2222-4222-8222-222222222222'),key,response
 def test_consistent_empty_snapshot_is_data_not_permission(self):
  r,a,s,key,response=self.fixture()
  with audit:
   rows=complete(s._read_snapshot((key,)));self.assertEqual(rows,(r.CapturedRecord(key,0,None,''),))
   self.assertFalse(hasattr(s,'execute'));self.assertFalse(hasattr(s,'reconcile'))
 def test_false_claims_wrong_indices_filtering_or_keys_refuse(self):
  for change in ({'KnownLeader':1},{'KnownLeader':False},{'ResultsFilteredByACLs':0},{'ResultsFilteredByACLs':True}):
   r,a,s,key,response=self.fixture();response.update(change)
   with audit,self.assertRaises(r.ResearchAuthorityUnavailable):complete(s._read_snapshot((key,)))
  r,a,s,key,response=self.fixture();response['Results'][0]['KV']['ModifyIndex']=True
  with audit,self.assertRaises(r.ResearchAuthorityUnavailable):complete(s._read_snapshot((key,)))
  for keys in ((),('outside/key',)):
   with audit,self.assertRaises(ValueError):complete(s._read_snapshot(keys))
 def test_negative_result_never_has_commit_or_effect_permission(self):
  from unified_system.research_authority import ResearchAdmissionResult
  result=ResearchAdmissionResult('UNKNOWN','JOB_RECONCILIATION_API_UNQUALIFIED','a'*64)
  self.assertEqual(result.commit_status,'NOT_ATTEMPTED');self.assertIs(result.effect_permitted,False)

class BrokerGuardTests(unittest.TestCase):
 def test_changed_generation_is_denied_before_profile_or_peer_work(self):
  with audit,inert_crypto_imports():
   m=importlib.import_module('unified_system.gateway_research_identity')
   broker=object.__new__(m.ResearchIdentityBroker);broker._namespace='unified/test';broker._generation='expected'
   calls=[]
   async def read(key):calls.append(key);return types.SimpleNamespace(raw=m.canonical({'generation':'foreign'}))
   broker._read=read
   with self.assertRaises(m.ResearchIdentityDenied):complete(broker._policy('f'*64,'service'))
   self.assertEqual(calls,['unified/test/commands/generation'])
 def test_context_peer_expiry_session_scope_and_raw_binding_remain_closed(self):
  with audit,inert_crypto_imports():
   m=importlib.import_module('unified_system.gateway_research_identity')
   broker=object.__new__(m.ResearchIdentityBroker);broker._authority=object();broker._invalid=set();broker._clock=lambda:(0,0)
   broker._peer=lambda sock:('fingerprint','service',100)
   context=object.__new__(m.ResearchPrincipalContext)
   broker._contexts={context:(object(),'fingerprint','service','session',100,'actor','policy','quota',100)}
   capture=object.__new__(m.ResearchIdentityCapture);snapshot=object()
   broker._captures={capture:(context,'READ_RESEARCH',hashlib.sha256(b'raw').digest(),snapshot,100,100)}
   self.assertIs(broker.require_capture(capture,expected_authority=broker._authority,scope='READ_RESEARCH',request_bytes=b'raw'),snapshot)
   for scope,raw in [('SUBMIT_RESEARCH',b'raw'),('READ_RESEARCH',b'changed')]:
    with self.assertRaises(m.ResearchIdentityDenied):broker.require_capture(capture,expected_authority=broker._authority,scope=scope,request_bytes=raw)
   broker._peer=lambda sock:('changed','service',100)
   with self.assertRaises(m.ResearchIdentityDenied):broker._context(context)
   broker._peer=lambda sock:('fingerprint','service',100);broker._invalid.add('session')
   with self.assertRaises(m.ResearchIdentityDenied):broker._context(context)
   broker._invalid.clear();broker._clock=lambda:(101,101)
   with self.assertRaises(m.ResearchIdentityDenied):broker._context(context)
 def test_hostile_native_metadata_and_false_client_shape_refuse(self):
  with audit,inert_crypto_imports():
   m=importlib.import_module('unified_system.gateway_research_identity')
   for raw in (b'{"x":true,"x":false}',b'{"x":1}',b'{"x":  "y"}',b'{} '):
    with self.assertRaises((m.ResearchIdentityDenied,ValueError)):m._decode(raw)
   from unified_system.consul_authority import ConsulConfig,ConsulSessionAuthority
   authority=ConsulSessionAuthority(ConsulConfig(('http://127.0.0.1:1',),'owned',isolated_lab=True),client=object())
   with self.assertRaises(m.ResearchIdentityUnavailable):m.ResearchIdentityBroker(authority=authority,generation='x',realm_id='x',profile_sha256='a'*64,server_ssl_context=None,server_certificate_der=b'',audit_sink=None)

class NegativeAndRetirementTests(unittest.TestCase):
 def test_negative_submit_lookup_never_upgrade_even_with_attempt_claim(self):
  from unified_system import research_authority as r
  obj=object.__new__(r.ResearchLabAuthority)
  class AttemptClaim:
   def __bool__(self):raise AssertionError('attempt claim evaluated')
  calls=[]
  async def observe(original,**kwargs):calls.append(kwargs['scope']);return r.CapturedRecord('job',0,None)
  obj._observe=observe
  with audit:
   result=complete(obj.submit(b'original',context=object(),leader=object(),owned_attempt=AttemptClaim()))
   self.assertEqual((result.outcome,result.commit_status,result.effect_permitted),('DENIED','NOT_ATTEMPTED',False))
   result=complete(obj.lookup(b'original',context=object()))
   self.assertEqual((result.outcome,result.commit_status,result.effect_permitted),('UNKNOWN','NOT_ATTEMPTED',False))
  self.assertEqual(calls,['SUBMIT_RESEARCH','READ_RESEARCH'])
 def test_invalidation_latches_and_attempts_retirement_even_if_audit_refuses(self):
  with audit,inert_crypto_imports():
   m=importlib.import_module('unified_system.gateway_research_identity')
   obj=object.__new__(m.ResearchIdentityBroker);ctx=object.__new__(m.ResearchPrincipalContext)
   obj._contexts={ctx:(None,None,None,'session')};obj._invalid=set();calls=[]
   def audit_failure(_):raise m.ResearchIdentityUnavailable('AUDIT_UNAVAILABLE')
   async def request(method,path):calls.append((method,path));self.assertIn('session',obj._invalid);return True
   obj._emit=audit_failure;obj._authority=types.SimpleNamespace(_request=request)
   with self.assertRaises(m.ResearchIdentityUnavailable):complete(obj.invalidate_context(ctx))
   self.assertEqual(calls,[('PUT','/v1/session/destroy/session')]);self.assertIn('session',obj._invalid)
 def test_wall_or_monotonic_rollback_latches_poison(self):
  with audit,inert_crypto_imports():
   m=importlib.import_module('unified_system.gateway_research_identity')
   obj=object.__new__(m.ResearchIdentityBroker);obj._closed=False;obj._poisoned=False
   obj._wall=obj._mono=0;obj._last_wall=obj._last_mono=10
   with patch.object(m,'_utc',return_value=9),patch.object(m.time,'monotonic',return_value=9):
    with self.assertRaises(m.ResearchIdentityUnavailable):obj._clock()
   self.assertTrue(obj._poisoned)
   with self.assertRaises(m.ResearchIdentityUnavailable):obj._clock()

class SourceParityTests(unittest.TestCase):
 def test_original_guard_method_ast_is_preserved_with_only_declared_ownership_edits(self):
  baseline=json.loads((Path(__file__).parent/'fixtures/root-authority-parity.json').read_text())
  root=Path(__file__).resolve().parents[2]
  with audit:
   for item in baseline['nodes']:
    tree=ast.parse((root/'unified_system'/item['target']).read_bytes())
    nodes=tree.body if item['cls'] is None else next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==item['cls']).body
    node=next(n for n in nodes if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==item['name'])
    # Python3.12 adds empty type_params; omit only that version-only AST field.
    for part in ast.walk(node):
     if hasattr(part,'type_params') and not part.type_params:del part.type_params
    self.assertEqual(hashlib.sha256(ast.dump(node,include_attributes=False).encode()).hexdigest(),item['expected_ast_sha256'],item['target']+':'+item['name'])
 def test_audit_denies_synthetic_socket_process_and_ctypes_events(self):
  for event in ('socket.connect','subprocess.Popen','ctypes.dlopen'):
   with audit,self.assertRaises(AssertionError):sys.audit(event,None)

class ConfigurationTests(unittest.TestCase):
 def test_original_config_bounds_and_secret_repr_remain(self):
  from unified_system.consul_authority import ConsulConfig,ConsulSessionAuthority
  with audit:
   cfg=ConsulConfig(('http://127.0.0.1:1',),'owned',acl_token='SECRET_TOKEN',client_key='SECRET_KEY',isolated_lab=True)
   self.assertNotIn('SECRET_TOKEN',repr(cfg));self.assertNotIn('SECRET_KEY',repr(cfg))
   for change in ({'ttl_seconds':True},{'ttl_seconds':9},{'ttl_seconds':3601},{'request_timeout':True},{'request_timeout':float('nan')},{'isolated_lab':1},{'endpoints':('http://127.0.0.1:1','http://127.0.0.1:1')}):
    from dataclasses import replace
    with self.assertRaises(ValueError):replace(cfg,**change)
   with self.assertRaises(ValueError):ConsulConfig(('http://remote:1',),'owned')
   with self.assertRaises(ValueError):ConsulConfig(('https://remote:1',),'owned')
