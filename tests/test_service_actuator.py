"""Service actuators use real owned temp receipts and inert SCM boundaries."""
import copy,unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
from tests import test_installation_service as fixtures
from unified_system.installation_service import ServiceResource
from unified_system import service_actuator as actuator

class Handle:
 def __init__(self,proof):self.proof=copy.deepcopy(proof);self.calls=[];self.pending=[];self.changed=None
 def read(self):
  value=copy.deepcopy(self.proof)
  if self.pending:value['state']=self.pending.pop(0)
  if self.changed:value.update(self.changed)
  return value
 def metadata(self,plan):return self.read()
 def start(self):self.calls.append('START');self.proof['state']=4
 def stop(self):self.calls.append('STOP');self.proof['state']=1
class Native:
 def __init__(self,proof):self.handle=Handle(proof);self.opens=0;self.closes=0
 @contextmanager
 def open(self,plan,action):
  self.opens+=1
  try:yield self.handle
  finally:self.closes+=1

class ActuatorTests(unittest.TestCase):
 def setUp(self):
  self.fixture=fixtures.ServiceResourceTests('test_default_denial_precedes_mutation');self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
  self.resource=ServiceResource.create(self.fixture.plan(),self.fixture.backend,self.fixture.guard)
  self.record=self.resource.recorded();self.native=Native(self.record['proof']);self.permissions=[]
 def plan(self,action='START',**kwargs):return actuator.service_actuation_plan(self.resource,action,'owner-phase-1',**kwargs)
 def guard(self,action,pin):self.permissions.append((action,pin));return True
 def run_plan(self,plan,guard=None):return actuator.actuate_service(self.resource,plan,owner_phase=self.guard if guard is None else guard,native=self.native)
 def test_start_and_stop_same_handle_ack_never_readiness(self):
  start=self.run_plan(self.plan());self.assertEqual(self.native.handle.calls,['START']);self.assertEqual(start['service_state'],'RUNNING');self.assertEqual(start['readiness'],'NOT_PROVEN');self.assertIs(start['execution_authority'],False)
  stop=self.run_plan(self.plan('STOP'));self.assertEqual(self.native.handle.calls,['START','STOP']);self.assertEqual(stop['service_state'],'STOPPED');self.assertEqual(self.native.opens,self.native.closes)
 def test_missing_or_denied_phase_has_no_native_effect(self):
  for guard in (None,lambda *_:False,lambda *_:1):
   with self.assertRaises(actuator.ActuationBlocked):actuator.actuate_service(self.resource,self.plan(),owner_phase=guard,native=self.native)
  self.assertEqual(self.native.opens,0);self.assertEqual(self.native.handle.calls,[])
 def test_all_recorded_live_fingerprint_mismatches_block(self):
  for key,value in self.record['proof'].items():
   if key=='state':continue
   with self.subTest(field=key):
    self.native.handle.proof=copy.deepcopy(self.record['proof']);self.native.handle.proof[key]=value+1 if type(value) is int else value+'foreign'
    with self.assertRaises(actuator.ActuationBlocked):self.run_plan(self.plan())
  self.assertEqual(self.native.handle.calls,[])
 def test_wrong_host_or_tampered_plan_blocks_before_open(self):
  plan=self.plan();plan['service_name']='foreign'
  with self.assertRaises(actuator.ActuationBlocked):self.run_plan(plan)
  self.fixture.backend.host='FOREIGN'
  with self.assertRaises(actuator.ActuationBlocked):self.run_plan(self.plan())
  self.assertEqual(self.native.opens,0)
 def test_guard_mutation_cannot_redirect_plan(self):
  plan=self.plan()
  def guard(action,pin):plan['service_name']='foreign';return True
  result=self.run_plan(plan,guard);self.assertEqual(result['service_name'],self.record['plan']['service_name']);self.assertEqual(self.native.handle.calls,['START'])
 def test_second_same_handle_read_catches_last_moment_change(self):
  original=self.native.handle.metadata
  def change(plan):
   proof=original(plan);self.native.handle.changed={'binary_path':'foreign'};return proof
  self.native.handle.metadata=change
  with self.assertRaises(actuator.ActuationBlocked):self.run_plan(self.plan())
  self.assertEqual(self.native.handle.calls,[]);self.assertEqual(self.native.opens,1);self.assertEqual(self.native.closes,1)
 def test_phase_revoked_during_metadata_blocks_start_and_stop_before_effect(self):
  for action in ('START','STOP'):
   for revoked in (False,1):
    with self.subTest(action=action,revoked=revoked):
     self.native=Native(self.record['proof']);self.native.handle.proof['state']=1 if action=='START' else 4
     phase=[True];checks=[];original=self.native.handle.metadata
     def metadata(plan):
      proof=original(plan);phase[0]=revoked;return proof
     def guard(operation,pin):checks.append((operation,pin));return phase[0]
     self.native.handle.metadata=metadata
     plan=self.plan(action)
     with self.assertRaises(actuator.ActuationBlocked) as error:self.run_plan(plan,guard)
     self.assertEqual(error.exception.code,'SERVICE_ACTUATION_OWNER_REQUIRED');self.assertFalse(error.exception.effect_attempted)
     self.assertEqual(self.native.handle.calls,[]);self.assertEqual(len(checks),2)
     self.assertTrue(all(row==('SERVICE_'+action,plan['plan_sha256']) for row in checks));self.assertEqual(self.native.opens,self.native.closes)
 def test_already_target_state_is_observation_only(self):
  result=self.run_plan(self.plan('STOP'));self.assertEqual(result['outcome'],'ALREADY_TARGET');self.assertEqual(self.native.handle.calls,[])
 def test_pending_state_blocks_without_action(self):
  self.native.handle.proof['state']=2
  with self.assertRaises(actuator.ActuationBlocked):self.run_plan(self.plan())
  self.assertEqual(self.native.handle.calls,[])
 def test_corrupt_capsule_blocks_start_and_stop_without_kill(self):
  (Path(self.record['plan']['code'])/'runtime/nssm/nssm.exe').write_bytes(b'foreign')
  for action in ('START','STOP'):
   with self.assertRaises(actuator.ActuationBlocked):self.run_plan(self.plan(action))
  self.assertEqual(self.native.handle.calls,[])
 def test_poll_timeout_retains_uncertainty_without_rollback(self):
  def start():self.native.handle.calls.append('START');self.native.handle.proof['state']=2
  self.native.handle.start=start
  with patch.object(actuator.time,'monotonic',side_effect=[0,0,2]),patch.object(actuator.time,'sleep'):
   with self.assertRaises(actuator.ActuationBlocked) as error:self.run_plan(self.plan(timeout_seconds=1))
  self.assertTrue(error.exception.effect_accepted);self.assertEqual(error.exception.code,'SERVICE_ACTUATION_UNCERTAIN');self.assertEqual(self.native.handle.calls,['START']);self.assertEqual(self.native.closes,1)

 # Actual handle adapter tests use only an injected inert SCM API.
 def test_documented_handle_adapter_never_reopens_or_controls_foreign_handle(self):
  outer=self
  class API:
   def __init__(self):self.calls=[];self.state=1
   def manager(self):self.calls.append(('manager',));return 9
   def open(self,manager,name,action):self.calls.append(('open',manager,name,action));return 42
   def close(self,handle):self.calls.append(('close',handle))
   def read(self,handle):
    self.calls.append(('read',handle));return {key:value for key,value in dict(outer.record['proof'],state=self.state).items() if key in ('binary_path','account','start_type','sid_type','state')}
   def environment_absent(self,plan):return True
   def start(self,handle):self.calls.append(('start',handle));self.state=4
   def stop(self,handle):self.calls.append(('stop',handle));self.state=1
  api=API();native=actuator.WindowsServiceActuator(api=api)
  extra={key:value for key,value in self.record['proof'].items() if key not in ('binary_path','account','start_type','sid_type','state')}
  with patch.object(actuator,'readonly_metadata',return_value=extra):
   actuator.actuate_service(self.resource,self.plan(),owner_phase=self.guard,native=native)
  self.assertEqual(sum(row[0]=='open' for row in api.calls),1);self.assertIn(('start',42),api.calls)
  self.assertEqual(api.calls[-2:],[('close',42),('close',9)])
 def test_native_request_exception_preserves_attempt_uncertainty(self):
  def start():self.native.handle.calls.append('START');raise OSError('PRIVATE_SCM_FAILURE')
  self.native.handle.start=start
  with self.assertRaises(actuator.ActuationBlocked) as error:self.run_plan(self.plan())
  self.assertEqual(error.exception.code,'SERVICE_ACTUATION_UNCERTAIN');self.assertTrue(error.exception.effect_attempted);self.assertFalse(error.exception.effect_accepted);self.assertEqual(self.native.handle.calls,['START'])

 def test_phase_callback_host_or_capsule_mutation_blocks_before_action(self):
  def host_change(action,pin):self.fixture.backend.host='OTHER-PC';return True
  with self.assertRaises(actuator.ActuationBlocked):self.run_plan(self.plan(),host_change)
  self.assertEqual(self.native.opens,0)
 def test_stale_reviewed_actuator_pin_cannot_be_resealed_by_callback(self):
  plan=self.plan()
  with patch.object(actuator,'source_pin',return_value='f'*64):
   with self.assertRaises(actuator.ActuationBlocked):self.run_plan(plan)
  self.assertEqual(self.native.opens,0)
 def test_bool_state_or_unexpected_transition_blocks_without_automatic_stop(self):
  self.native.handle.proof['state']=True
  with self.assertRaises(actuator.ActuationBlocked):self.run_plan(self.plan())
  self.native.handle.proof=copy.deepcopy(self.record['proof'])
  def start():self.native.handle.calls.append('START');self.native.handle.proof['state']=1
  self.native.handle.start=start
  with self.assertRaises(actuator.ActuationBlocked) as error:self.run_plan(self.plan())
  self.assertTrue(error.exception.effect_accepted);self.assertEqual(self.native.handle.calls,['START'])

 def test_optional_scm_actions_triggers_and_environment_block_all_native_effects(self):
  extra={key:value for key,value in self.record['proof'].items() if key not in ('binary_path','account','start_type','sid_type','state')}
  for mode in ('restart','reboot','run-command','command-without-action','trigger','environment','noncrash','delayed','unavailable','bad-failure-pointer','bad-trigger-pointer','oversized','truncated','huge-failure-count','huge-trigger-count','environment-unavailable'):
   with self.subTest(mode=mode):
    api=native_api(mode);api.dll.binary=self.record['proof']['binary_path']
    with patch.object(actuator,'readonly_metadata',return_value=extra):
     with self.assertRaises(actuator.ActuationBlocked):actuator.actuate_service(self.resource,self.plan(),owner_phase=self.guard,native=actuator.WindowsServiceActuator(api=api))
    self.assertFalse(any(row[0] in ('START','STOP') for row in api.dll.calls))

 def test_environment_added_during_slow_metadata_is_rechecked_before_start(self):
  api=native_api();api.dll.binary=self.record['proof']['binary_path']
  extra={key:value for key,value in self.record['proof'].items() if key not in ('binary_path','account','start_type','sid_type','state')}
  def metadata(plan):api.dll.mode='environment';return extra
  with patch.object(actuator,'readonly_metadata',side_effect=metadata):
   with self.assertRaises(actuator.ActuationBlocked):actuator.actuate_service(self.resource,self.plan(),owner_phase=self.guard,native=actuator.WindowsServiceActuator(api=api))
  self.assertFalse(any(row[0] in ('START','STOP') for row in api.dll.calls))
  self.assertTrue(all(row[3] is None for row in api.dll.calls if row[0]=='registry-probe'))

class RegistryClosureTests(unittest.TestCase):
 def test_exact_raw_nssm_values_reject_unknown_hooks_environment_or_exit_overrides(self):
  plan=dict(python='C:/owned/python.exe',parameters='-I -S -B fixed.py',code='C:/owned/code')
  good={'values':{'Application':[plan['python'],2],'AppParameters':[plan['parameters'],2],'AppDirectory':[plan['code'],2]},'subkeys':{'AppExit':{'values':{'':['Exit',1]},'subkeys':{}}}}
  self.assertTrue(actuator.validate_nssm_registry(plan,good))
  for change in ('hook','environment','exit-override','expanded-value','wrong-kind'):
   snapshot=copy.deepcopy(good)
   if change=='hook':snapshot['subkeys']['AppEvents']={}
   elif change=='environment':snapshot['values']['AppEnvironmentExtra']=['PYTHONPATH=foreign',7]
   elif change=='exit-override':snapshot['subkeys']['AppExit']['values']['78']=['Restart',1]
   elif change=='expanded-value':snapshot['values']['Application']=['%COMSPEC%',2]
   else:snapshot['values']['Application'][1]=3
   with self.subTest(change=change):
    with self.assertRaises(actuator.ActuationBlocked):actuator.validate_nssm_registry(plan,snapshot)

 def test_registry_reader_uses_only_exact_readonly_namespace_and_closes_handles(self):
  from contextlib import contextmanager
  plan=dict(service_name='UnifiedLab_owned',python='C:/owned/python.exe',parameters='fixed',code='C:/owned/code')
  class Registry:
   HKEY_LOCAL_MACHINE='HKLM';KEY_READ=131097
   def __init__(self):self.calls=[]
   @contextmanager
   def OpenKey(self,parent,name,reserved,access):
    self.calls.append(('open',parent,name,access));key='exit' if name=='AppExit' else 'parameters'
    try:yield key
    finally:self.calls.append(('close',key))
   def QueryInfoKey(self,key):return (0,1,0) if key=='exit' else (1,3,0)
   def EnumKey(self,key,index):return 'AppExit'
   def EnumValue(self,key,index):
    return ('','Exit',1) if key=='exit' else [('Application',plan['python'],2),('AppParameters',plan['parameters'],2),('AppDirectory',plan['code'],2)][index]
  registry=Registry();actuator.nssm_registry_proof(plan,api=registry)
  self.assertEqual(registry.calls[0],('open','HKLM','SYSTEM\\CurrentControlSet\\Services\\UnifiedLab_owned\\Parameters',registry.KEY_READ))
  self.assertEqual(registry.calls[-2:],[('close','exit'),('close','parameters')])

class NativeDLL:
 def __init__(self,mode=None):self.mode=mode;self.calls=[];self.service_type=16;self.bad_pointer=False;self.foreign_dependency=False
 def OpenSCManagerW(self,*args):return 9
 def OpenServiceW(self,manager,name,access):self.calls.append(('open',name));return 44
 def CloseServiceHandle(self,handle):self.calls.append(('close',handle));return 1
 def StartServiceW(self,handle,*args):self.calls.append(('START',handle));return 1
 def ControlService(self,handle,*args):self.calls.append(('STOP',handle));return 1
 def QueryServiceConfigW(self,handle,buffer,size,needed):
  import ctypes
  self.handle=handle;ctypes.cast(needed,ctypes.POINTER(ctypes.c_uint32))[0]=1024
  if buffer is None:return 0
  record=actuator.CONFIG.from_buffer(buffer);record.type=self.service_type;record.start=3;record.error=1
  start=ctypes.addressof(buffer);binary=self.binary.encode('utf-16le')+b'\0\0';account='nt authority\\localservice'.encode('utf-16le')+b'\0\0'
  ctypes.memmove(start+256,binary,len(binary));ctypes.memmove(start+512,account,len(account))
  record.binary=1 if self.bad_pointer else start+256;record.account=start+512
  if self.foreign_dependency:
   raw='ForeignService'.encode('utf-16le')+b'\0\0\0\0';ctypes.memmove(start+768,raw,len(raw));record.dependencies=start+768
  return 1
 binary='"C:\\owned\\nssm.exe"'
 def QueryServiceConfig2W(self,handle,kind,buffer,size,needed):
  import ctypes
  if kind==5:ctypes.cast(buffer,ctypes.POINTER(ctypes.c_uint32))[0]=1;return 1
  if self.mode=='unavailable':return 0
  ctypes.cast(needed,ctypes.POINTER(ctypes.c_uint32))[0]=65537 if self.mode=='oversized' else 1 if self.mode=='truncated' else 1024
  if buffer is None:return 0
  if self.mode=='success-needed-zero':ctypes.cast(needed,ctypes.POINTER(ctypes.c_uint32))[0]=0
  if kind==2:
   record=actuator.FAILURE_ACTIONS.from_buffer(buffer)
   if self.mode in ('restart','reboot','run-command'):record.count=1;record.actions=ctypes.addressof(buffer)+512
   if self.mode=='command-without-action':
    raw='foreign.exe'.encode('utf-16le')+b'\0\0';ctypes.memmove(ctypes.addressof(buffer)+512,raw,len(raw));record.command=ctypes.addressof(buffer)+512
   if self.mode=='bad-failure-pointer':record.command=1
   if self.mode=='huge-failure-count':record.count=0xffffffff
   if self.mode=='empty-bounded-arrays':record.actions=ctypes.addressof(buffer)+512
  elif kind==8:
   record=actuator.TRIGGER_INFO.from_buffer(buffer)
   if self.mode=='trigger':record.count=1;record.triggers=ctypes.addressof(buffer)+512
   if self.mode=='bad-trigger-pointer':record.triggers=1
   if self.mode=='huge-trigger-count':record.count=0xffffffff
   if self.mode=='empty-bounded-arrays':record.triggers=ctypes.addressof(buffer)+512
  else:ctypes.cast(buffer,ctypes.POINTER(ctypes.c_uint32))[0]=int(self.mode==('noncrash' if kind==4 else 'delayed'))
  return 1
 def QueryServiceStatusEx(self,handle,kind,buffer,size,needed):
  import ctypes
  record=ctypes.cast(buffer,ctypes.POINTER(actuator.STATUS)).contents;record.type=16;record.state=1;return 1
 def RegOpenKeyExW(self,parent,path,reserved,access,output):
  import ctypes
  self.calls.append(('registry-open',path,access));ctypes.cast(output,ctypes.POINTER(ctypes.c_void_p))[0]=73;return 0
 def RegQueryValueExW(self,handle,name,reserved,kind,data,size):self.calls.append(('registry-probe',handle,name,data));return 0 if self.mode=='environment' else 5 if self.mode=='environment-unavailable' else 2
 def RegCloseKey(self,handle):self.calls.append(('registry-close',handle));return 0

def native_api(mode=None):
 api=actuator._WinSCM.__new__(actuator._WinSCM);api.dll=NativeDLL(mode);return api

class NativeBufferTests(unittest.TestCase):
 def test_bounded_native_config_and_status_decode_rejects_foreign_type_or_pointer(self):
  api=native_api();proof=api.read(44);self.assertEqual(api.dll.handle,44);self.assertEqual(proof['account'],'NT AUTHORITY\\LocalService');self.assertEqual(proof['binary_path'],'"C:\\owned\\nssm.exe"')
  api.dll.foreign_dependency=True
  with self.assertRaises(actuator.ActuationBlocked):api.read(44)
  api.dll.foreign_dependency=False;api.dll.service_type=256
  with self.assertRaises(actuator.ActuationBlocked):api.read(44)
  api.dll.service_type=16;api.dll.bad_pointer=True
  with self.assertRaises(actuator.ActuationBlocked):api.read(44)

 def test_zero_count_unused_array_pointers_must_stay_in_bounded_buffer(self):
  api=native_api('empty-bounded-arrays');self.assertEqual(api.read(44)['state'],1)

 def test_successful_optional_query_may_clear_insufficient_buffer_size_output(self):
  api=native_api('success-needed-zero');self.assertEqual(api.read(44)['state'],1)

if __name__=='__main__':unittest.main()
