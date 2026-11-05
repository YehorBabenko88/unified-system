"""Owned PostgreSQL boundary tests: inert capsule/native fakes only."""
import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unified_system import service_postgres as pg,lab_release
from tests import test_runtime_profile as fixtures

ROOT=Path(__file__).resolve().parents[1]
class Server:
 def __init__(self):self.closed=False
 def alive(self):return not self.closed
 def close(self):self.closed=True
class Boundary:
 def __init__(self):self.calls=[];self.servers=[];self.fault=None;self.sql_change={}
 def writer_identity(self):return {'computer_name':'LABHOST','user_sid':'S-1-5-21-123-456-789-1001'}
 def admit(self,plan):lab_release.verify_capsule(plan['service_plan']['code'],plan['service_plan']['manifest_sha256']);self.calls.append('admit')
 def retain_failure(self,plan):self.calls.append('failure_sealed')
 def prepare(self,plan):
  self.calls.append('prepare');Path(plan['namespace']).mkdir();Path(plan['data_root']).mkdir()
 def admit_auth(self,plan):self.calls.append('auth_acl')
 def release_id(self,plan):return 'lab-1'
 def grid_commit(self,plan):return 'a'*40
 def initialize(self,plan,password):
  self.calls.append('initialize');Path(plan['cluster']).mkdir();(Path(plan['cluster'])/'PG_VERSION').write_bytes(b'18')
  for name in pg.CONFIG_FILES:
   if name!='PG_VERSION':(Path(plan['cluster'])/name).write_bytes(b'INERT_CONFIG')
  if self.fault=='initialize':raise ValueError('PRIVATE_FAILURE')
 def start(self,plan,provision=False):
  self.calls.append('start');server=Server();self.servers.append(server);return server
 def stop(self,plan,server):server.close()
 def require_running(self,grant,record):return True
 def configure(self,plan,server,password):self.calls.append('configure')
 def ready(self,plan,server,provision=False):
  self.calls.append('ready')
  return {**dict(version_num=180001,database=plan['database'],user=plan['user'],data_directory=plan['cluster'],port=plan['port'],system_identifier='123456789',bootstrap_login=False,superuser=False,createdb=False,createrole=False,replication=False,bypassrls=False),**self.sql_change}
 def seal(self,plan,password):self.calls.append('seal');(Path(plan['namespace'])/'pgpass.conf').write_text('INERT_PRIVATE_FIXTURE')
 def publish(self,plan,raw):self.calls.append('publish');(Path(plan['namespace'])/'receipt.json').write_bytes(raw)
 def admit_runtime(self,grant,record):self.calls.append('runtime_admit')
class Kernel:
 def require_readonly(self,path,sid,anchor):
  if not path.is_file():raise ValueError('missing')
  return True
class Resource:
 def __init__(self,plan):self.plan=plan
 def recorded(self):return {'plan':copy.deepcopy(self.plan),'receipt_sha256':'d'*64}

class PostgresBoundaryTests(unittest.TestCase):
 def setUp(self):
  self.fixture=fixtures.RuntimeProfileTests('test_all_roles_are_pure_derived_data_never_execution_admission');self.fixture.setUp();self.addCleanup(self.fixture.doCleanups);base=self.fixture.base
  files={name:b'INERT_'+name.encode() for name in ('bin/initdb.exe','bin/postgres.exe','bin/psql.exe','bin/libpq.dll','lib/dummy.dll','share/postgres.bki')}
  for name,raw in files.items():
   path=base/'runtime/postgresql'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
  from tests.test_lab_capsule_builder import builder
  vendor={'postgresql':{'version':'postgres (PostgreSQL) 18.1','files':builder.inventory(base/'runtime/postgresql')[0]}}
  (base/'locks').mkdir();(base/'locks/vendor.json').write_bytes(lab_release.canonical(vendor))
  job=base/'sources/grid/grid/ml_windows_job.py';job.parent.mkdir(parents=True);job.write_bytes(b'INERT_JOB_NOT_EXECUTED')
  (base/'lab-release.json').unlink();self.fixture.manifest['files'],self.fixture.manifest['directories']=builder.inventory(base)
  raw=lab_release.canonical(self.fixture.manifest);(base/'lab-release.json').write_bytes(raw);self.fixture.pin=hashlib.sha256(raw).hexdigest()
  self.root=self.fixture.root/'service';self.root.mkdir();(self.root/'state').mkdir();lab_release.stage_capsule(base,self.root/'code',self.fixture.pin)
  self.auth=self.fixture.root/'protected-auth.json';self.auth.write_bytes(lab_release.canonical(dict(schema='unified.lab.grid-auth.v3',node_id='NODE1',role='CONTROL',release_id='lab-1',source_commit='a'*40,grid_shared_token='d'*64,node_credential=None,postgres_password='c'*64)))
  target=self.fixture.target('CONTROL');target['auth_binding']['sha256']=hashlib.sha256(self.auth.read_bytes()).hexdigest();self.profile=self.fixture.derive(target)
  self.resource=Resource(dict(root=str(self.root),code=str(self.root/'code'),state=str(self.root/'state'),manifest_sha256=self.fixture.pin,role='CONTROL',computer_name='LABHOST',node_id='NODE1',installation_id='install-1',service_sid='S-1-5-80-1-2-3-4-5',plan_sha256='b'*64))
  self.boundary=Boundary();self.plan=pg.postgres_plan(self.resource,self.profile,self.auth,boundary=self.boundary);self.calls=[]
 def owner(self,action,pin):self.calls.append((action,pin));return True
 def provision(self,**changes):return pg.provision_postgres(self.plan,owner_phase=changes.get('owner_phase',self.owner),boundary=self.boundary)
 def grant(self,receipt):
  return SimpleNamespace(descriptor={'service_plan':copy.deepcopy(self.resource.plan),'auth_sha256':self.plan['auth_sha256'],'qualification_refs':{'database_evidence_sha256':receipt['receipt_sha256']}},_kernel=Kernel(),service_sid=self.resource.plan['service_sid'],profile=copy.deepcopy(self.profile),require_current=lambda:True)
 def test_missing_owner_phase_precedes_native_effects(self):
  with self.assertRaises(pg.PostgresBlocked):self.provision(owner_phase=None)
  self.assertEqual(self.boundary.calls,[]);self.assertFalse(Path(self.plan['namespace']).exists())
 def test_foreign_receipt_never_becomes_database_authority(self):
  with self.assertRaises(pg.PostgresBlocked):pg.read_postgres_ownership(None)
 def test_consumed_provision_receipt_runtime_start_and_owned_close(self):
  receipt=self.provision();self.assertEqual(receipt['runtime_readiness'],'NOT_PROVEN');self.assertTrue(self.boundary.servers[0].closed)
  self.assertTrue(all(pin==self.plan['plan_sha256'] for _,pin in self.calls))
  owned=pg.read_postgres_ownership(self.grant(receipt),boundary=self.boundary);owned.start();self.assertIs(owned.require_current(),True);owned.close();self.assertTrue(all(s.closed for s in self.boundary.servers))
  self.assertNotIn('c'*64,(Path(self.plan['namespace'])/'receipt.json').read_text())
 def test_exposed_record_copy_cannot_redirect_runtime_data_or_ownership(self):
  receipt=self.provision();owned=pg.read_postgres_ownership(self.grant(receipt),boundary=self.boundary)
  exposed=owned.record;exposed['plan']['cluster']=str(self.fixture.root/'foreign');exposed['system_identifier']='999'
  self.assertEqual(owned.record['plan']['cluster'],self.plan['cluster']);self.assertEqual(owned.record['system_identifier'],'123456789')
  owned.start();owned.close();self.assertFalse((self.fixture.root/'foreign').exists())

 def test_delayed_runtime_readiness_waits_same_owned_process_without_respawn(self):
  from unittest.mock import patch
  receipt=self.provision();owned=pg.read_postgres_ownership(self.grant(receipt),boundary=self.boundary)
  original=self.boundary.ready;calls=[]
  def delayed(*args,**kwargs):
   calls.append(True)
   if len(calls)==1:raise pg.PostgresBlocked('POSTGRES_NOT_READY')
   return original(*args,**kwargs)
  before=len(self.boundary.servers)
  with patch.object(self.boundary,'ready',side_effect=delayed),patch('time.sleep'):
   owned.start()
  self.assertEqual(len(calls),2);self.assertEqual(len(self.boundary.servers),before+1);owned.close()
 def test_wrong_runtime_identity_is_not_retried_as_startup_delay(self):
  from unittest.mock import patch
  receipt=self.provision();owned=pg.read_postgres_ownership(self.grant(receipt),boundary=self.boundary)
  with patch.object(self.boundary,'ready',side_effect=pg.PostgresBlocked('POSTGRES_IDENTITY_REJECTED')) as ready,patch('time.sleep') as sleep:
   with self.assertRaises(pg.PostgresBlocked):owned.start()
  ready.assert_called_once();sleep.assert_not_called();self.assertTrue(self.boundary.servers[-1].closed)

 def test_existing_data_never_adopted_or_deleted(self):
  data=Path(self.plan['data_root']);data.mkdir();(data/'foreign').write_text('keep')
  with self.assertRaises(pg.PostgresBlocked):self.provision()
  self.assertEqual((data/'foreign').read_text(),'keep');self.assertNotIn('prepare',self.boundary.calls)
 def test_partial_init_retains_data_and_no_ownership_receipt(self):
  self.boundary.fault='initialize'
  with self.assertRaises(pg.PostgresBlocked):self.provision()
  self.assertTrue((Path(self.plan['cluster'])/'PG_VERSION').exists());self.assertFalse((Path(self.plan['namespace'])/'receipt.json').exists())
 def test_wrong_sql_cluster_or_role_never_publishes_and_stops_only_own_job(self):
  self.boundary.sql_change={'system_identifier':'0'}
  with self.assertRaises(pg.PostgresBlocked):self.provision()
  self.assertTrue(self.boundary.servers[0].closed);self.assertFalse((Path(self.plan['namespace'])/'receipt.json').exists())
 def test_runtime_replaced_data_root_is_not_attached(self):
  receipt=self.provision();data=Path(self.plan['data_root']);data.rename(data.with_name('retained'));data.mkdir()
  with self.assertRaises(pg.PostgresBlocked):pg.read_postgres_ownership(self.grant(receipt),boundary=self.boundary)
 def test_receipt_hash_is_not_optional_and_no_public_pass_boolean(self):
  receipt=self.provision();grant=self.grant(receipt);grant.descriptor['qualification_refs']['database_evidence_sha256']='0'*64
  with self.assertRaises(pg.PostgresBlocked):pg.read_postgres_ownership(grant,boundary=self.boundary)

class NativePolicyTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve();self.data=self.root/'postgres';self.data.mkdir();(self.data/'cluster').mkdir();(self.data/'cluster/file').write_bytes(b'18')
  self.sid='S-1-5-80-1-2-3-4-5';self.plan={'data_root':str(self.data),'service_plan':{'service_sid':self.sid}}
 def test_owner_rights_policy_is_required_for_future_localservice_owned_files(self):
  from unittest.mock import patch
  kernel=object.__new__(pg.PostgresDataKernel)
  def security(path):
   flags=(3 if path.is_dir() else 0)|(0 if path==self.data else 16)
   return ('S-1-5-32-544' if path==self.data else 'S-1-5-19'),path==self.data,[('S-1-5-18',0x1f01ff,flags),('S-1-5-32-544',0x1f01ff,flags),(self.sid,0x1301bf,flags),('S-1-3-4',0x20000,flags)]
  with patch.object(kernel,'_data_security',side_effect=security):self.assertTrue(kernel.require_data(self.plan))
  for change in ('missing_owner_rights','owner_write_dac','generic_localservice','wrong_inheritance','foreign_owner'):
   def bad(path):
    owner,protected,rows=security(path)
    if change=='missing_owner_rights':rows.pop()
    elif change=='owner_write_dac':rows[-1]=('S-1-3-4',0x60000,rows[-1][2])
    elif change=='generic_localservice':rows[2]=('S-1-5-19',0x1301bf,rows[2][2])
    elif change=='wrong_inheritance':rows[-1]=('S-1-3-4',0x20000,0)
    else:owner='S-1-5-21-999'
    return owner,protected,rows
   with self.subTest(change=change),patch.object(kernel,'_data_security',side_effect=bad),self.assertRaises(pg.PostgresBlocked):kernel.require_data(self.plan)
 def test_toolhelp_resumes_only_exact_owned_process_sole_thread(self):
  from unittest.mock import patch
  import ctypes
  class Function:
   def __init__(self,call):self.call=call
   def __call__(self,*args):return self.call(*args)
  closed=[];resumed=[]
  def first(snapshot,pointer):pointer._obj.process_id=123;pointer._obj.thread_id=321;return 1
  kernel=SimpleNamespace(CreateToolhelp32Snapshot=Function(lambda *a:55),Thread32First=Function(first),Thread32Next=Function(lambda *a:0),OpenThread=Function(lambda *a:66),GetProcessIdOfThread=Function(lambda *a:123),ResumeThread=Function(lambda handle:resumed.append(handle) or 1),CloseHandle=Function(lambda h:closed.append(h) or 1))
  identity=['created','owned.exe']
  with patch('unified_system.runtime_process._identity',return_value=identity):pg._resume_owned_primary(123,identity,kernel=kernel)
  self.assertEqual(resumed,[66]);self.assertEqual(closed,[66,55])
  resumed.clear();kernel.GetProcessIdOfThread.call=lambda *a:999
  with patch('unified_system.runtime_process._identity',return_value=identity),self.assertRaises(pg.PostgresBlocked):pg._resume_owned_primary(123,identity,kernel=kernel)
  self.assertEqual(resumed,[])
 def test_copy_replacement_or_redirection_is_not_launched_or_cleaned(self):
  from unittest.mock import patch
  source=self.root/'code/runtime/postgresql/bin';source.mkdir(parents=True);(source/'postgres.exe').write_bytes(b'INERT')
  boundary=pg.WindowsPostgresBoundary();plan={'data_root':str(self.data),'service_plan':{'code':str(self.root/'code')},'postgresql_files':{'bin/postgres.exe':{'bytes':5,'sha256':hashlib.sha256(b'INERT').hexdigest()}}}
  with patch.object(boundary,'_permit'):boundary._copy_bootstrap(plan)
  path=self.data/'bootstrap-runtime/bin/postgres.exe';path.rename(path.with_name('retained.exe'));path.write_bytes(b'FOREIGN')
  with self.assertRaises(Exception):boundary._verify_bootstrap(plan)
  with self.assertRaises(Exception):boundary._cleanup_bootstrap(plan)
  self.assertEqual(path.read_bytes(),b'FOREIGN');self.assertTrue(path.with_name('retained.exe').exists())

class NativeSqlFencingTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve();(self.root/'cluster').mkdir();(self.root/'bootstrap').mkdir()
  self.plan={'data_root':str(self.root),'cluster':str(self.root/'cluster'),'port':55479,'database':'unified_lab_fixture','user':'unified_lab_fixture','bootstrap_user':'unified_bootstrap_fixture','service_plan':{'code':str(self.root/'code')}}
  self.passfile=self.root/'bootstrap/pgpass.conf';self.passfile.write_text('127.0.0.1:55479:*:unified_bootstrap_fixture:'+('c'*64)+'\n')
  self.boundary=pg.WindowsPostgresBoundary();self.boundary.secret_files[self.passfile]=pg.stamp(self.passfile)
  self.server=SimpleNamespace(alive=lambda:True)
 def test_nologin_occurs_only_after_successful_application_identity_probe(self):
  from unittest.mock import patch
  events=[]
  proof=dict(version_num=180001,database=self.plan['database'],user=self.plan['user'],data_directory=self.plan['cluster'],port=55479,system_identifier='123456789',bootstrap_login=True,superuser=False,createdb=False,createrole=False,replication=False,bypassrls=False)
  def sql(plan,server,command,**kwargs):events.append(command);return b'1'
  def ready(*a,**k):events.append('APP_IDENTITY');return proof
  with patch.object(self.boundary,'_permit'),patch.object(self.boundary,'_sql',side_effect=sql),patch.object(self.boundary,'ready',side_effect=ready):self.boundary.configure(self.plan,self.server,'c'*64)
  self.assertLess(events.index('APP_IDENTITY'),next(i for i,event in enumerate(events) if ' NOLOGIN' in event))
 def test_failed_application_identity_does_not_disable_bootstrap_role(self):
  from unittest.mock import patch
  commands=[]
  with patch.object(self.boundary,'_permit'),patch.object(self.boundary,'_sql',side_effect=lambda p,s,sql,**k:commands.append(sql) or b'1'),patch.object(self.boundary,'ready',side_effect=pg.PostgresBlocked('POSTGRES_NOT_READY')):
   with self.assertRaises(pg.PostgresBlocked):self.boundary.configure(self.plan,self.server,'c'*64)
  self.assertFalse(any(' NOLOGIN' in sql for sql in commands))
 def test_foreign_listener_is_rejected_before_credentials_or_client_creation(self):
  from unittest.mock import patch
  with patch.object(self.boundary,'_permit'),patch.object(pg,'_prove_listener',side_effect=pg.PostgresBlocked('POSTGRES_PROCESS_REJECTED')),patch.object(pg,'regular',side_effect=AssertionError('NO SECRET READ')),patch.object(pg,'_LibpqConnection') as connect,patch.dict(pg.os.environ,{},clear=True):
   with self.assertRaises(pg.PostgresBlocked):self.boundary._sql(self.plan,self.server,'CREATE DATABASE should_never_run;',provision=True)
   connect.assert_not_called()
 def test_foreign_backend_on_same_connection_precedes_mutating_sql(self):
  from unittest.mock import patch
  from contextlib import nullcontext
  binary=self.root/'code/runtime/postgresql/bin';binary.mkdir(parents=True);dll=binary/'libpq.dll';dll.write_bytes(b'INERT_DLL');self.plan['postgresql_files']={'bin/libpq.dll':{'bytes':9,'sha256':hashlib.sha256(b'INERT_DLL').hexdigest()}}
  queries=[];closed=[]
  identity=dict(backend_pid=999,database=self.plan['database'],user=self.plan['bootstrap_user'],data_directory=self.plan['cluster'],port=55479,system_identifier='123456789',version_num=180001)
  connection=SimpleNamespace(query=lambda query:queries.append(query) or json.dumps(identity).encode(),close=lambda:closed.append(True))
  with patch.object(self.boundary,'_permit'),patch.object(pg,'_prove_listener',return_value=True),patch.object(pg,'_job_process_identity',side_effect=pg.PostgresBlocked('POSTGRES_PROCESS_REJECTED')),patch.object(pg,'_LibpqConnection',return_value=connection),patch.object(pg.os,'add_dll_directory',return_value=nullcontext(),create=True),patch.object(pg,'_load_libpq',return_value=object()),patch.dict(pg.os.environ,{},clear=True):
   with self.assertRaises(pg.PostgresBlocked):self.boundary._sql(self.plan,self.server,'CREATE DATABASE should_never_run;',database=self.plan['database'],user=self.plan['bootstrap_user'],provision=True)
  self.assertEqual(len(queries),1);self.assertIn('pg_backend_pid()',queries[0]);self.assertEqual(closed,[True])
 def test_typed_tcp_table_requires_exact_loopback_unique_listener(self):
  import ctypes,struct,socket
  class Function:
   def __init__(self,rows):self.rows=rows
   def __call__(self,buffer,size,*args):
    raw=struct.pack('<I',len(self.rows))+b''.join(struct.pack('<6I',*row) for row in self.rows);size._obj.value=len(raw)
    if buffer is None:return 122
    ctypes.memmove(buffer,raw,len(raw));return 0
  row=(2,int.from_bytes(socket.inet_aton('127.0.0.1'),'little'),socket.htons(55479),0,0,123)
  self.assertEqual(pg._listener_pid(55479,api=Function([row])),123)
  for rows in ([],[row,row],[(2,0,row[2],0,0,123)]):
   with self.subTest(rows=rows),self.assertRaises(pg.PostgresBlocked):pg._listener_pid(55479,api=Function(rows))

class LaunchRecoveryTests(unittest.TestCase):
 def setUp(self):
  self.case=PostgresBoundaryTests('test_consumed_provision_receipt_runtime_start_and_owned_close');self.case.setUp();self.addCleanup(self.case.doCleanups);self.case.provision();self.plan=self.case.plan
 def server(self,lease,confirmed=True):
  from unittest.mock import Mock
  server=object.__new__(pg.OwnedJobProcess);server.pid=123;server.identity=['100',str(Path(self.plan['service_plan']['code'])/'runtime/postgresql/bin/postgres.exe')];server.argv=[server.identity[1],'-D',self.plan['cluster']];server.launch=lease;server.confirmed_quiescent=False;server.output=None;server.error=None;server.owned_files={}
  server.job=SimpleNamespace(terminate_and_wait=Mock(return_value=confirmed),close=Mock(side_effect=AssertionError('NO ASYNC CLOSE')))
  server.proc=SimpleNamespace(pid=123,stdin=None,wait=Mock(return_value=0));lease.launched(server)
  return server
 def pid_files(self,server,pid=123):
  import subprocess
  cluster=Path(self.plan['cluster']);(cluster/'postmaster.pid').write_text(str(pid)+'\n'+str(cluster)+'\n123456789\n'+str(self.plan['port'])+'\n')
  (cluster/'postmaster.opts').write_text(subprocess.list2cmdline(server.argv)+'\n')
 def test_failed_before_ready_cleans_only_after_confirmed_job_quiescence_and_allows_retry(self):
  from unittest.mock import patch
  lease=pg._Launch(self.plan);self.addCleanup(lease.release);server=self.server(lease);self.pid_files(server);job=server.job
  with patch.object(pg,'_listener_pid',side_effect=pg.PostgresStartPending()):pg.WindowsPostgresBoundary().stop(self.plan,server)
  job.terminate_and_wait.assert_called_once_with(timeout=5);job.close.assert_not_called()
  self.assertFalse((Path(self.plan['cluster'])/'postmaster.pid').exists());self.assertFalse((Path(self.plan['cluster'])/'postmaster.opts').exists())
  second=pg._Launch(self.plan);second.no_process();second.release()
 def test_unconfirmed_job_retains_owned_files_and_poison_blocks_new_launch(self):
  lease=pg._Launch(self.plan);self.addCleanup(lease.release);server=self.server(lease,False);self.pid_files(server)
  with self.assertRaises(pg.PostgresBlocked) as error:pg.WindowsPostgresBoundary().stop(self.plan,server)
  self.assertEqual(error.exception.code,'POSTGRES_POISONED');self.assertTrue((Path(self.plan['cluster'])/'postmaster.pid').exists())
  lease.release()
  with self.assertRaises(pg.PostgresBlocked):pg._Launch(self.plan)
 def test_competing_launch_cannot_replace_active_lock_or_change_owner_journal(self):
  lease=pg._Launch(self.plan);self.addCleanup(lease.release);before=lease.journal.read()
  with self.assertRaises(pg.PostgresBlocked):pg._Launch(self.plan)
  self.assertEqual(lease.journal.read(),before);lease.no_process()
 def test_old_job_without_synchronous_quiescence_is_rejected_before_any_spawn(self):
  from unittest.mock import patch
  code=Path(self.plan['service_plan']['code']);job=code/'sources/grid/grid/ml_windows_job.py'
  raw=b'class WindowsJob:\n def close(self):pass\n';job.write_bytes(raw);plan=copy.deepcopy(self.plan);plan['job_sha256']=hashlib.sha256(raw).hexdigest()
  with patch('subprocess.Popen') as spawn:
   with self.assertRaises(pg.PostgresBlocked):pg._job_class(plan)
   spawn.assert_not_called()

 def test_foreign_pid_after_start_is_preserved_even_after_own_job_is_quiescent(self):
  from unittest.mock import patch
  lease=pg._Launch(self.plan);self.addCleanup(lease.release);server=self.server(lease);self.pid_files(server,999)
  with patch.object(pg,'_listener_pid',side_effect=pg.PostgresStartPending()),self.assertRaises(pg.PostgresBlocked):pg.WindowsPostgresBoundary().stop(self.plan,server)
  self.assertEqual((Path(self.plan['cluster'])/'postmaster.pid').read_text().splitlines()[0],'999')

if __name__=='__main__':unittest.main()
