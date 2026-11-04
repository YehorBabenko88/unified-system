"""Offline profile derivation; synthetic metadata, no activation/credentials/DB."""
import ast,copy,hashlib,importlib.util,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from unified_system import lab_release,lab_runtime
from unified_system.runtime_profile import derive_runtime_profile
from tests.test_lab_release import fixture
from tests.test_lab_capsule_builder import builder as control
from tests.test_prepare_worker_capsule import builder as worker_builder

ROOT=Path(__file__).resolve().parents[1]
LEGACY_WORKER_SOURCE = "def worker_config(config,*,node_id,old_root,new_root,new_state,ports,coordinator_port,auth_path,auth_sha256):\n    if node_id not in WORKERS or set(ports)!=MODULES:raise ValueError('WORKER_TARGET_REQUIRED')\n    if any(type(p) is not int or not 1024<=p<=65535 for p in [*ports.values(),coordinator_port]) or len(set(ports.values()))!=6 or coordinator_port in ports.values():\n        raise ValueError('BOUND_LOOPBACK_PORTS_REQUIRED')\n    old_root=Path(old_root);new_root=Path(new_root);old_state=Path(config['state_root']);new_state=Path(new_state)\n    if not all(p.is_absolute() for p in (old_root,new_root,old_state,new_state,Path(auth_path))):raise ValueError('ABSOLUTE_PATH_REQUIRED')\n    if new_root==new_state or new_root in new_state.parents or new_state in new_root.parents:raise ValueError('DISJOINT_STATE_REQUIRED')\n    if new_state not in Path(auth_path).parents or not isinstance(auth_sha256,str) or not re.fullmatch('[a-f0-9]{64}',auth_sha256):raise ValueError('PRIVATE_AUTH_BINDING_REQUIRED')\n    def text(value):\n        if type(value) is not str:return value\n        for old,new in ((old_root,new_root),(old_state,new_state)):\n            if value==str(old):return str(new)\n            if value.startswith(str(old)+'\\\\') or value.startswith(str(old)+'/'):return str(new)+value[len(str(old)):]\n        return value\n    def rebase(value):\n        if isinstance(value,dict):return {text(k):rebase(v) for k,v in value.items()}\n        if isinstance(value,list):return [rebase(v) for v in value]\n        return text(value)\n    c=rebase(copy.deepcopy(config));c['node_id']=node_id;c['http_port']=ports['unified-system']\n    for name,program in c['programs'].items():\n        previous=program['health_url'].rsplit(':',1)[1].split('/',1)[0]\n        program['health_url']=f'http://127.0.0.1:{ports[name]}/internal/v2/module/health'\n        if name!='math':\n            args=program['argv'];port_index=args.index('--port')\n            if args[port_index+1]!=previous:raise ValueError('SOURCE_PORT_BINDING')\n            args[port_index+1]=str(ports[name])\n        else:program['env']['MATH_ENGINE_PORT']=str(ports[name])\n    for name,program in c['programs'].items():\n        need(not any(k.upper() in ('PGPASSWORD','NODE_CREDENTIAL','GRID_SHARED_TOKEN') for k in program['env']))\n        if name!='grid':need(not any(k.upper()=='POSTGRES_DSN' for k in program['env']))\n    grid=c['programs']['grid'];env=grid['env']\n    for key in list(env):\n        if key.upper()=='POSTGRES_DSN':del env[key]\n    for key in ('PGPASSWORD','NODE_CREDENTIAL','GRID_SHARED_TOKEN'):\n        if key in env:raise ValueError('PRIVATE_ENV_NOT_IN_PUBLIC_CONFIG')\n    env.update(ROLE='worker',NODE_ID=node_id,NODE_ROLE='WORKER',COORDINATOR_URL=f'http://127.0.0.1:{coordinator_port}',\n               GRID_LAB_AUTH_PATH=str(auth_path),GRID_LAB_AUTH_SHA256=auth_sha256)\n    args=grid['argv'];source=str(new_root/'sources/grid');deps=str(new_root/'dependencies/site-packages')\n    args[args.index('--source-root')+1]=source\n    dependency_indices=[i+1 for i,a in enumerate(args) if a=='--dependency-root']\n    if len(dependency_indices)!=1:raise ValueError('REVIEWED_GRID_DEPENDENCIES_REQUIRED')\n    args[dependency_indices[0]]=deps\n    index=args.index('--module')\n    grid['argv']=args[:index]+['--module','grid.owned_worker_service','--','--execute','--port',str(ports['grid'])]\n    return c"

class RuntimeProfileTests(unittest.TestCase):
 def test_optional_research_permissions_are_detached_metadata_only(self):
  from tests.test_data_first_policy import PolicyTests
  case=PolicyTests();case.setUp();policy=case.value
  policy['source_commit']=self.manifest['sources']['strattester']['commit']
  target=self.target();legacy=self.derive(target)
  result=derive_runtime_profile(self.config,self.manifest,base_manifest_sha256=self.pin,target=target,data_first=policy)
  self.assertEqual({k:v for k,v in result.items() if k!='data_first'},legacy)
  self.assertEqual(derive_runtime_profile(self.config,self.manifest,base_manifest_sha256=self.pin,target=target,data_first=None),legacy)
  self.assertFalse(result['execution_authority']);self.assertEqual(result['activation'],'BLOCKED')
  policy['categories'].append('spot');self.assertEqual(result['data_first']['categories'],['linear'])
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve();self.base=self.root/'base';self.base.mkdir()
  self.manifest=fixture(self.base)
  bootstrap=self.base/'sources/unified-system/unified_system/owned_python.py';bootstrap.parent.mkdir(parents=True);bootstrap.write_bytes(b'# INERT FIXTURE\n')
  for name in self.manifest['sources']:self.manifest['sources'][name]['dependencies']={dep:'1.0.0' for dep in control.GRAPH[name]}
  snapshots={name:{'runtime_files':{'inert.txt':{'raw_sha256':self.manifest['files']['sources/'+name+'/inert.txt']['sha256']}}} for name in self.manifest['sources']}
  tool=self.base/'tools/git.exe'
  self.config=control.runtime_config(self.base,self.root/'old-state',self.manifest['sources'],snapshots,tool,tool,tool,'lab-1',(self.root/'old-state/private/grid-auth.json','a'*64),55459)
  raw=lab_release.canonical(self.config);(self.base/'runtime.json').write_bytes(raw)
  self.manifest['files'],self.manifest['directories']=control.inventory(self.base)
  raw=lab_release.canonical(self.manifest);(self.base/'lab-release.json').write_bytes(raw);self.pin=hashlib.sha256(raw).hexdigest()
 def target(self,role='WORKER'):
  return dict(installation_id='install-1',node_id='NODE1',computer_name='LABHOST',role=role,code_root=str(self.root/'service/code'),state_root=str(self.root/'service/state'),credential_root=str(self.root/'service/activation/credentials'),ports=dict(zip(sorted(control.NAMES),range(26000,26006))),coordinator_port=29000 if role=='WORKER' else None,auth_binding={'path':str(self.root/'service/activation/credentials/grid-auth.json'),'sha256':'c'*64},postgres_binding=None if role=='WORKER' else {'database':'unified_lab_install1','user':'unified_lab_install1','port':55479})
 def derive(self,target=None):return derive_runtime_profile(self.config,self.manifest,base_manifest_sha256=self.pin,target=self.target() if target is None else target)
 def test_all_roles_are_pure_derived_data_never_execution_admission(self):
  before=copy.deepcopy((self.config,self.manifest));files=sorted(str(p) for p in self.root.rglob('*'))
  for role in ('CONTROL','WORKER','SINGLE_PC','SINGLE-PC'):
   with self.subTest(role=role),patch('subprocess.Popen',side_effect=AssertionError('NO PROCESS')),patch('socket.socket',side_effect=AssertionError('NO NETWORK')),patch.object(lab_runtime,'read_grid_auth',side_effect=AssertionError('NO SECRET READ')):
    result=self.derive(self.target(role));c=result['runtime_config'];context=result['offline_context']
    self.assertEqual(result['status'],'DERIVED_PROFILE_ONLY');self.assertFalse(result['execution_authority']);self.assertEqual(result['activation'],'BLOCKED')
    self.assertEqual(lab_runtime.validate_config(c,self.manifest,Path(c['programs']['grid']['cwd']).parents[1],hostname='LABHOST',offline_context=context),c)
    self.assertEqual(c['release_sha256'],self.pin);self.assertEqual(c['node_id'],'NODE1')
    for name,program in c['programs'].items():
     self.assertEqual(program['file_pins'],self.config['programs'][name]['file_pins']);self.assertEqual(program['executable_sha256'],self.config['programs'][name]['executable_sha256'])
     self.assertTrue(program['cwd'].startswith(self.target(role)['code_root']))
    self.assertEqual('POSTGRES_DSN' in c['programs']['grid']['env'],role!='WORKER')
    self.assertEqual(result['derivation_receipt']['profile_sha256'],hashlib.sha256(lab_release.canonical(c)).hexdigest())
  self.assertEqual((self.config,self.manifest),before);self.assertEqual(sorted(str(p) for p in self.root.rglob('*')),files)
 def test_worker_facade_matches_frozen_previous_output_bytes(self):
  b=worker_builder();namespace={'Path':Path,'copy':copy,'re':__import__('re'),'WORKERS':b.WORKERS,'MODULES':b.MODULES,'need':b.need};exec(LEGACY_WORKER_SOURCE,namespace)
  kwargs=dict(node_id='PC1',old_root=self.base,new_root=self.root/'worker',new_state=self.root/'worker-state',ports=self.target()['ports'],coordinator_port=29000,auth_path=self.root/'worker-state/private/auth.json',auth_sha256='d'*64)
  for with_ca in (False,True):
   config=copy.deepcopy(self.config)
   if with_ca:config['programs']['math']['ca_file']=str(self.base/'tools/ca.pem')
   expected=namespace['worker_config'](config,**kwargs);actual=b.worker_config(config,**kwargs)
   self.assertEqual(lab_release.canonical(actual),lab_release.canonical(expected))
 @unittest.skipUnless(os.name=='nt','actual Windows 8.3 base alias compatibility')
 def test_existing_short_base_alias_matches_frozen_worker_without_relaxing_targets(self):
  import ctypes
  kernel=ctypes.WinDLL('kernel32',use_last_error=True);function=kernel.GetShortPathNameW;function.argtypes=[ctypes.c_wchar_p,ctypes.c_wchar_p,ctypes.c_uint];function.restype=ctypes.c_uint
  output=ctypes.create_unicode_buffer(32768);count=function(str(self.base),output,len(output));self.assertGreater(count,0)
  alias=Path(output.value)
  if str(alias).casefold()==str(self.base).casefold():self.skipTest('volume did not provide an 8.3 alias')
  self.assertTrue(alias.samefile(self.base))
  def replace(value):
   if isinstance(value,dict):return {replace(key):replace(item) for key,item in value.items()}
   if isinstance(value,list):return [replace(item) for item in value]
   if type(value) is str and value.startswith(str(self.base)):return str(alias)+value[len(str(self.base)):]
   return value
  config=replace(self.config);lab_runtime.validate_config(config,self.manifest,alias,hostname='LS5')
  b=worker_builder();namespace={'Path':Path,'copy':copy,'re':__import__('re'),'WORKERS':b.WORKERS,'MODULES':b.MODULES,'need':b.need};exec(LEGACY_WORKER_SOURCE,namespace)
  kwargs=dict(node_id='PC1',old_root=alias,new_root=self.root/'worker',new_state=self.root/'worker-state',ports=self.target()['ports'],coordinator_port=29000,auth_path=self.root/'worker-state/private/auth.json',auth_sha256='d'*64)
  expected=namespace['worker_config'](config,**kwargs);actual=b.worker_config(config,**kwargs)
  self.assertEqual(lab_release.canonical(actual),lab_release.canonical(expected))
  with self.assertRaises(ValueError):b.worker_config(config,**{**kwargs,'new_root':alias/'noncanonical-target'})
 def test_base_link_is_not_admitted_as_a_legacy_alias(self):
  alias=self.root/'linked-base'
  if os.name=='nt':
   result=subprocess.run([str(Path(os.environ['SYSTEMROOT'])/'System32/cmd.exe'),'/d','/c','mklink','/J',str(alias),str(self.base)],capture_output=True,timeout=10,creationflags=subprocess.CREATE_NO_WINDOW)
   self.assertEqual(result.returncode,0,result.stderr)
   self.addCleanup(lambda:os.rmdir(alias) if alias.exists() else None)
  else:alias.symlink_to(self.base,target_is_directory=True)
  b=worker_builder();kwargs=dict(node_id='PC1',old_root=alias,new_root=self.root/'worker',new_state=self.root/'worker-state',ports=self.target()['ports'],coordinator_port=29000,auth_path=self.root/'worker-state/private/auth.json',auth_sha256='d'*64)
  with self.assertRaises(ValueError):b.worker_config(self.config,**kwargs)

 def test_closed_target_secret_fields_wrong_roles_ports_and_paths_rejected(self):
  cases=[{'role':'PRODUCTION'},{'password':'SECRET'},{'auth_binding':{'path':self.target()['auth_binding']['path'],'sha256':'c'*64,'token':'SECRET'}},{'postgres_binding':{'database':'unified_lab_x','user':'unified_lab_x','port':55479}},{'code_root':str(self.base)},{'state_root':str(self.base/'state')},{'auth_binding':{'path':str(self.root/'service/state/foreign.json'),'sha256':'c'*64}},{'credential_root':self.target()['state_root']},{'ports':{**self.target()['ports'],'grid':True}},{'coordinator_port':self.target()['ports']['grid']}]
  for changes in cases:
   with self.subTest(changes=changes),self.assertRaises(ValueError):self.derive({**self.target(),**changes})
  for binding in (None,{'database':'postgres','user':'postgres','port':5432},{'database':'unified_lab_x','user':'unified_lab_x','port':55479,'password':'SECRET'}):
   with self.subTest(binding=binding),self.assertRaises(ValueError):self.derive({**self.target('CONTROL'),'postgres_binding':binding})
 def test_unknown_base_launch_or_unbound_manifest_is_not_repaired_into_admission(self):
  with self.assertRaises(ValueError):derive_runtime_profile(self.config,self.manifest,base_manifest_sha256='f'*64,target=self.target())
  changed=copy.deepcopy(self.config);changed['programs']['grid']['argv'][-1]='malicious';manifest=copy.deepcopy(self.manifest);raw=lab_release.canonical(changed);manifest['files']['runtime.json']={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
  pin=hashlib.sha256(lab_release.canonical(manifest)).hexdigest()
  with self.assertRaises(ValueError):derive_runtime_profile(changed,manifest,base_manifest_sha256=pin,target=self.target())
 def test_aliases_are_snapshotted_and_extra_config_context_never_enters_cli(self):
  target=self.target('SINGLE_PC');result=self.derive(target);target['auth_binding']['path']='changed';self.config['programs']['grid']['env']['ROLE']='changed'
  self.assertNotIn('changed',json.dumps(result));self.assertEqual(result['offline_context']['scope'],'OFFLINE_VALIDATION_ONLY')
  raw=copy.deepcopy(result['runtime_config']);raw['offline_context']=result['offline_context']
  with self.assertRaises(ValueError):lab_runtime.validate_config(raw,self.manifest,Path(target['code_root']),hostname='LABHOST')

class ProfileOperatorClosureTests(unittest.TestCase):
 def test_missing_helper_lock_rejects_even_with_ambient_workspace_then_full_lock_accepts(self):
  import shutil
  with tempfile.TemporaryDirectory() as temporary:
   root=Path(temporary).resolve();operator=root/'operator';operator.mkdir();files={}
   for source in [*ROOT.joinpath('unified_system').rglob('*.py'),ROOT/'integration/source_guard.py',ROOT/'scripts/prepare_worker_capsule.py']:
    relative=source.relative_to(ROOT).as_posix();target=operator/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target);files[relative]=hashlib.sha256(target.read_bytes()).hexdigest()
   script="import sys,runpy,pathlib;root=pathlib.Path(sys.argv[1]);sys.path.append(sys.argv[4]);ns=runpy.run_path(str(root/'scripts/prepare_worker_capsule.py'));\ntry:\n ns['admit_operator'](root,pathlib.Path(sys.argv[2]),sys.argv[3]);import unified_system.runtime_profile;assert pathlib.Path(unified_system.runtime_profile.__file__).is_relative_to(root);print('PINNED_HELPER')\nexcept ValueError:\n print('PIN_DENIED');raise SystemExit(7)"
   def run(members):
    lock=root/'lock.json';raw=json.dumps({'schema':'unified.worker-operator.v1','files':members,'source_manifest_sha256s':['a'*64]}).encode();lock.write_bytes(raw)
    return subprocess.run([sys.executable,'-I','-S','-B','-c',script,str(operator),str(lock),hashlib.sha256(raw).hexdigest(),str(ROOT)],capture_output=True,text=True,timeout=30)
   for missing in ('unified_system/runtime_profile.py','unified_system/data_first_policy.py'):
    old={k:v for k,v in files.items() if k!=missing};denied=run(old);self.assertEqual(denied.returncode,7,denied.stderr)
   accepted=run(files);self.assertEqual(accepted.returncode,0,accepted.stderr);self.assertEqual(accepted.stdout.strip(),'PINNED_HELPER')
   (operator/'unified_system/runtime_profile.py').write_text('raise RuntimeError("UNPINNED_HELPER")')
   changed=run(files);self.assertEqual(changed.returncode,7,changed.stderr)

if __name__=='__main__':unittest.main()
