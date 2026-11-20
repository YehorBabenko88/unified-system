"""Private driver capability tests: inert subprocess/health substitutes only."""
import hashlib,io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from unified_system.runtime_process import ProcessDriver,PRIVATE_DATA_CAPABILITY_ENV as KEY
from unified_system.runtime import ModuleSpec,RuntimeSupervisor

class PrivateDataCapabilityTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve()
  executable=self.root/'inert.exe';executable.write_bytes(b'never executed');pin=hashlib.sha256(executable.read_bytes()).hexdigest()
  self.program=dict(argv=[str(executable)],cwd=str(self.root),executable_sha256=pin,file_pins={'inert.exe':pin},health_url='http://127.0.0.1:29001/health',env={'UNIFIED_SOURCE_COMMIT':'a'*40})
  self.programs={name:{**self.program,'env':dict(self.program['env'])} for name in ('market_data','terminan','math')}
  self.driver=ProcessDriver(self.root/'private',self.programs,authorize=lambda *_:True,child_environment=lambda _: {KEY:'ambient-must-not-leak','PGPASSWORD':'SYNTHETIC_ONLY_PASSWORD'})
  self.epoch='a'*32;self.token='b'*64;self.add_source(self.epoch,self.token)
  self.alive=patch.object(self.driver,'alive',return_value=True);self.alive.start();self.addCleanup(self.alive.stop)
  self.health=patch.object(self.driver,'ready',return_value=dict(module_id='market_data',version='1.0.0',release_id='r',ready=True));self.health.start();self.addCleanup(self.health.stop)
 def add_source(self,epoch,token):
  self.driver.children[epoch]=SimpleNamespace()
  self.driver._save(epoch,dict(module_id='market_data',version='1.0.0',release_id='r',token=token,state='RUNNING',pid=10,created=['owned','exe'],source_commit='a'*40),new=True)
 def test_only_private_terminan_environment_receives_current_ready_source(self):
  child=SimpleNamespace(pid=22,stdin=io.BytesIO());op='c'*32
  with patch('unified_system.runtime_process.subprocess.Popen',return_value=child) as spawn,patch('unified_system.runtime_process._identity',return_value=['owned','exe']):
   self.driver.start(ModuleSpec('terminan','1.0.0'),'r',op)
  cap=json.loads(spawn.call_args.kwargs['env'][KEY]);self.assertEqual(cap['token'],self.token);self.assertEqual(cap['epoch'],self.epoch)
  self.assertEqual(cap['source_commit'],'a'*40);self.assertEqual(cap['port'],29001)
  self.assertNotIn('PGPASSWORD',spawn.call_args.kwargs['env'])
  record=self.driver._load(op);self.assertEqual(record['market_data_epoch'],self.epoch);self.assertNotIn(self.token,self.driver._file(op).read_text())
  with patch('unified_system.runtime_process.subprocess.Popen',return_value=child) as spawn,patch('unified_system.runtime_process._identity',return_value=['owned','exe']):
   self.driver.start(ModuleSpec('math','1.0.0'),'r','d'*32)
  self.assertNotIn(KEY,spawn.call_args.kwargs['env']);self.assertNotIn('PGPASSWORD',spawn.call_args.kwargs['env'])
  with patch('unified_system.runtime_process.subprocess.Popen',return_value=child) as spawn,patch('unified_system.runtime_process._identity',return_value=['owned','exe']):
   self.driver.start(ModuleSpec('market_data','1.0.0'),'r','e'*32)
  self.assertEqual(spawn.call_args.kwargs['env']['PGPASSWORD'],'SYNTHETIC_ONLY_PASSWORD');self.assertNotIn(KEY,spawn.call_args.kwargs['env'])
 def test_public_configuration_override_is_rejected_even_after_construction(self):
  for key in (KEY,KEY.lower(),'PGPASSWORD','pgpassfile'):
   self.programs['terminan']['env'][key]='injected'
   with self.assertRaises(ValueError):ProcessDriver(self.root/'other',self.programs)
   with patch('unified_system.runtime_process.subprocess.Popen') as spawn,self.assertRaises(ValueError):self.driver.start(ModuleSpec('terminan','1.0.0'),'r','c'*32)
   spawn.assert_not_called();self.programs['terminan']['env'].pop(key)
 def test_missing_ambiguous_unready_or_cross_release_source_never_starts_child(self):
  for problem in ('missing','ambiguous','not-ready','wrong-release','wrong-source','nonliteral-ready'):
   with self.subTest(problem=problem):
    sources=dict(self.driver.children);record=self.driver._load(self.epoch)
    if problem=='missing':self.driver.children.clear()
    elif problem=='ambiguous':self.add_source('e'*32,'f'*64)
    elif problem=='wrong-release':self.driver._save(self.epoch,{**record,'release_id':'other'})
    elif problem=='wrong-source':self.driver._save(self.epoch,{**record,'source_commit':'0'*40})
    result=dict(module_id='market_data',version='1.0.0',release_id='r',ready=True)
    if problem=='not-ready':result['ready']=False
    elif problem=='nonliteral-ready':result['ready']=1
    self.health.stop();self.health=patch.object(self.driver,'ready',return_value=result);self.health.start()
    with patch('unified_system.runtime_process.subprocess.Popen') as spawn,self.assertRaises(ValueError):self.driver.start(ModuleSpec('terminan','1.0.0'),'r','c'*32)
    spawn.assert_not_called();self.assertFalse(self.driver._file('c'*32).exists())
    self.driver.children=sources;self.driver._save(self.epoch,record)
 def test_new_data_epoch_refuses_idempotent_old_terminal_operation(self):
  op='c'*32;self.driver._save(op,dict(module_id='terminan',version='1.0.0',release_id='r',token='d'*64,state='RUNNING',pid=22,created=['owned','exe'],market_data_epoch='old'),new=True)
  with patch('unified_system.runtime_process.subprocess.Popen') as spawn,self.assertRaises(ValueError):self.driver.start(ModuleSpec('terminan','1.0.0'),'r',op)
  spawn.assert_not_called()

class DependencyEpochTests(unittest.TestCase):
 def test_data_fault_stops_consumer_and_new_ready_epoch_restarts_it(self):
  class Driver:
   def __init__(self):self.records={};self.started=[];self.stopped=[];self.epoch=None
   def start(self,spec,release,op):
    self.records[op]=dict(module=spec.module_id,version=spec.version,alive=True)
    if spec.module_id=='market_data':self.epoch=op
    self.started.append((spec.module_id,op,self.epoch));return op
   def alive(self,op):return self.records[op]['alive']
   def ready(self,spec,op,release):return dict(module_id=spec.module_id,version=spec.version,release_id=release,ready=True)
   def stop(self,op):self.records[op]['alive']=False;self.stopped.append(op)
  with tempfile.TemporaryDirectory() as temp:
   driver=Driver();clock=[0.];runtime=RuntimeSupervisor(Path(temp)/'runtime.sqlite',driver,[ModuleSpec('unified_system','1.0.0'),ModuleSpec('math','1.0.0',dependencies=('unified_system',)),ModuleSpec('market_data','1.0.0',dependencies=('unified_system',)),ModuleSpec('terminan','1.0.0',dependencies=('market_data','math'))],release_id='r',release_sha256='a'*64,node_id='N',clock=lambda:clock[0])
   runtime.start();runtime.tick();old=[x for x in driver.started if x[0]=='terminan'][-1];driver.records[old[2]]['alive']=False
   runtime.tick();self.assertIn(old[1],driver.stopped)
   clock[0]=10.;runtime.tick();new=[x for x in driver.started if x[0]=='terminan'][-1]
   self.assertNotEqual(new[1],old[1]);self.assertNotEqual(new[2],old[2]);runtime.stop()
