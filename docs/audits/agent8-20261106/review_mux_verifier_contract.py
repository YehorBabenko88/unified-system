"""Additional synthetic record/provider contract tests; not native authentication."""
import asyncio,hashlib,json,pathlib,subprocess,sys,types,uuid
r=pathlib.Path(__file__).resolve().parents[1];src=r/'work/review-mux-3d48763-run2';out=r/'outputs/phase45'
raw=subprocess.check_output(['git','--no-replace-objects','-C',str(src),'show','cc286bce5e51e3670bd8a6cdfd3b663307268703:unified_system/security_identity_records.py'])
assert hashlib.sha256(raw).hexdigest()=='0d6b413b5654c0ff26c00bbbdcc6a47329e56dd9b8cb1cd838df8896477972cd'
sys.path.insert(0,str(src));m=types.ModuleType('unified_system.security_identity_records');sys.modules[m.__name__]=m;exec(compile(raw,'<pinned-root>', 'exec'),m.__dict__)
from unified_system.control_mux.commands import AdmittedContext,NativeAdmissionProvider
from unified_system.control_mux.consul_store import MuxAuthority,_Record
from unified_system.control_mux.codec import encode
ids=[str(uuid.uuid4()) for _ in range(7)];cluster,actor,session,enrollment,policy,node,generation=ids;b=m.IdentityBinding(cluster,actor,session,enrollment,policy,node)
c=AdmittedContext(cluster,actor,session,actor,'OPERATOR_CONTROL','fixture','1',frozenset({'OPEN_CONNECTION'}),b)
records={}
for kind in ('principal','session','enrollment','policy'):
 d=dict(schema='unified.security.identity-record.v1',kind=kind,cluster_id=cluster,principal_id=actor,state='ACTIVE',revision='1')
 if kind=='principal':d.update(node_id=node,sid='S-1-5-21-123')
 if kind=='session':d.update(session_id=session,enrollment_id=enrollment,policy_id=policy,native_logon_id='0000000000000001')
 if kind=='enrollment':d.update(enrollment_id=enrollment,node_id=node)
 if kind=='policy':d.update(policy_id=policy,role='OPERATOR_CONTROL',permissions=['OPEN_CONNECTION'])
 records[m.guard_keys(b)[kind]]=_Record(10+len(records),encode(d))
class Provider:
 def revalidate(self,c,op):return c
 def identity_binding(self,c):return b
 def verify_records(self,c,records):
  if self.mode=='raise':raise ValueError('NATIVE_REJECT')
  return self.mode
class Inherited(Provider,NativeAdmissionProvider):
 verify_records=NativeAdmissionProvider.verify_records
async def main():
 cases=[]
 for name,value,allowed in [('false',False,False),('true',True,False),('none',None,True),('error','raise',False),('inherited_protocol_stub','stub',False)]:
  p=Inherited() if name=='inherited_protocol_stub' else Provider();p.mode=value
  authority=types.SimpleNamespace(config=types.SimpleNamespace(namespace='unified/'+cluster));store=MuxAuthority(authority,generation,admission=p)
  async def read(key):return records[key]
  store._read=read
  try:checks=await store._identity(c,'OPEN_CONNECTION');ok=True;assert len(checks)==4
  except (ValueError,NotImplementedError):ok=False
  assert ok==allowed,name;cases.append(dict(name=name,expected_allowed=allowed,actual_allowed=ok))
 report=dict(scope='MODEL_SYNTHETIC_IDENTITY_RECORDS_NOT_NATIVE_AUTH',head='3d48763288a2ff2a4337000943a15f03a9ac45c1',cases=cases,skips=[],result='PASS',native_authentication=False)
 (out/'independent-verifier-contract.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
asyncio.run(main())
