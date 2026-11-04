"""Pure role-aware runtime profile derivation, never activation authority.

Inputs are externally pinned metadata, not authenticated runtime observations.
No files, secrets, databases, network clients or processes are opened/created.
The existing validators may inspect local path metadata. Source/ACL/DB/capacity
qualification and the protected startup gate remain separate mandatory work.
"""
import copy,hashlib,re,os
from pathlib import Path
from . import lab_release
from .owned_python import reject_external_namespace
from .lab_capsule_acl import _safe as safe_path
from .runtime_process import _safe_path as legacy_base_path

MODULES=frozenset(lab_release.MODULE_IDS)
PATH_ENV=frozenset(('UNIFIED_GIT_EXECUTABLE','UNIFIED_SOURCE_ROOT','PROGRAMDATA','PROGRAMFILES',
 'ML_ARTIFACT_ROOT','ARCHIVE_ROOT','STRATEGY_CACHE_DIR','TEMP','TMP','USERPROFILE','HOME',
 'APPDATA','LOCALAPPDATA','TERMINAN_RUNTIME_V2_SNAPSHOT','TERMINAN_LAB_SNAPSHOT',
 'GRID_INSTALL_ROOT','GRID_RELEASE_MANIFEST','GRID_CONTROL_JOURNAL','GRID_CONTROL_SNAPSHOTS','GRID_LAB_AUTH_PATH'))
TARGET_KEYS={'installation_id','node_id','computer_name','role','code_root','state_root','credential_root','ports','coordinator_port','auth_binding','postgres_binding'}


def need(ok):
 if not ok:raise ValueError('RUNTIME_PROFILE_REJECTED')


def _path(value,*,legacy_base=False):
 need(isinstance(value,(str,Path)))
 value=Path(value);need(value.is_absolute() and '..' not in value.parts and not str(value).startswith(('//',chr(92))))
 reject_external_namespace(str(value))
 if legacy_base:
  # Already admitted BASE namespaces may use a real Windows 8.3 spelling. Keep
  # that lexical prefix for compatibility; inspect ancestors before resolution
  # so a junction/symlink is never treated as an equivalent base alias. Fresh
  # targets still use the stricter canonical-only path below.
  parts=str(value).replace(chr(92),'/').split('/')[1:]
  need(not any(part in ('.','..') or part.endswith((' ','.')) or ':' in part for part in parts))
  return legacy_base_path(value)
 return safe_path(value)


def rebase_config(config,*,node_id,role,old_root,new_root,new_state,ports,coordinator_port,auth_path,auth_sha256,postgres_dsn=None):
 """Shared pure transform; worker facade retains its existing caller guards.

 Only reviewed path slots are rebased. High-level derivation validates both the
 original and derived launch profiles; this helper alone grants no admission.
 """
 config=copy.deepcopy(config);ports=copy.deepcopy(ports)
 need(role in ('CONTROL','WORKER','SINGLE_PC') and type(node_id) is str and re.fullmatch('[A-Za-z0-9_-]{1,64}',node_id))
 need(type(ports) is dict and set(ports)==MODULES and all(type(p) is int and 1024<=p<=65535 for p in ports.values()) and len(set(ports.values()))==6)
 if role=='WORKER':need(type(coordinator_port) is int and 1024<=coordinator_port<=65535 and coordinator_port not in ports.values() and postgres_dsn is None)
 else:need(coordinator_port is None)
 old_root=_path(old_root,legacy_base=True);new_root=_path(new_root);old_state=_path(config['state_root'],legacy_base=True);new_state=_path(new_state);auth_path=_path(auth_path)
 need(new_root!=new_state and new_root not in new_state.parents and new_state not in new_root.parents)
 need(type(auth_sha256) is str and re.fullmatch('[a-f0-9]{64}',auth_sha256))
 def text(value):
  if type(value) is not str:return value
  for old,new in ((old_root,new_root),(old_state,new_state)):
   if value==str(old):return str(new)
   if value.startswith(str(old)+'\\') or value.startswith(str(old)+'/'):return str(new)+value[len(str(old)):]
  return value
 config['state_root']=str(new_state);config['snapshot_path']=text(config['snapshot_path']);config['node_id']=node_id;config['http_port']=ports['unified-system']
 for name,program in config['programs'].items():
  program['cwd']=text(program['cwd']);program['argv']=[text(value) for value in program['argv']]
  if 'ca_file' in program:program['ca_file']=text(program['ca_file'])
  if 'external_file_pins' in program:program['external_file_pins']={text(key):value for key,value in program['external_file_pins'].items()}
  env=program.get('env',{})
  for key,value in list(env.items()):
   if key.upper() in PATH_ENV:env[key]=text(value)
   elif key.upper()=='PATH':env[key]=os.pathsep.join(text(item) for item in value.split(os.pathsep))
  previous=program['health_url'].rsplit(':',1)[1].split('/',1)[0]
  program['health_url']=f'http://127.0.0.1:{ports[name]}/internal/v2/module/health'
  if name!='math':
   args=program['argv'];port_index=args.index('--port');need(args[port_index+1]==previous);args[port_index+1]=str(ports[name])
  else:program['env']['MATH_ENGINE_PORT']=str(ports[name])
 for name,program in config['programs'].items():
  need(not any(key.upper() in ('PGPASSWORD','NODE_CREDENTIAL','GRID_SHARED_TOKEN') for key in program['env']))
  if name!='grid':need(not any(key.upper()=='POSTGRES_DSN' for key in program['env']))
 grid=config['programs']['grid'];env=grid['env']
 for key in list(env):
  if key.upper() in ('POSTGRES_DSN','COORDINATOR_URL'):del env[key]
 env.update(ROLE='worker' if role=='WORKER' else 'coordinator',NODE_ID=node_id,NODE_ROLE='WORKER' if role=='WORKER' else 'CONTROL',GRID_LAB_AUTH_PATH=str(auth_path),GRID_LAB_AUTH_SHA256=auth_sha256)
 if role=='WORKER':env['COORDINATOR_URL']=f'http://127.0.0.1:{coordinator_port}'
 else:need(type(postgres_dsn) is str);env['POSTGRES_DSN']=postgres_dsn
 args=grid['argv'];source=str(new_root/'sources/grid');deps=str(new_root/'dependencies/site-packages')
 args[args.index('--source-root')+1]=source if role=='WORKER' else deps
 dependency_indices=[i+1 for i,a in enumerate(args) if a=='--dependency-root'];need(len(dependency_indices)==1)
 args[dependency_indices[0]]=deps if role=='WORKER' else source
 index=args.index('--module')
 tail=['grid.owned_worker_service','--','--execute','--port',str(ports['grid'])] if role=='WORKER' else ['uvicorn','--','grid.coordinator:app','--host','127.0.0.1','--port',str(ports['grid']),'--no-access-log']
 grid['argv']=args[:index]+['--module',*tail]
 return config


def _derive_runtime_profile(base_config,base_manifest,*,base_manifest_sha256,target):
 """Closed offline data profile; no CLI, writer or runtime activation path."""
 from . import lab_runtime
 config=copy.deepcopy(base_config);manifest=copy.deepcopy(base_manifest);target=copy.deepcopy(target)
 manifest=lab_release.parse_manifest(lab_release.canonical(manifest),base_manifest_sha256)
 raw=lab_release.canonical(config);need(manifest['files'][manifest['runtime_config']]=={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
 need(type(target) is dict and set(target)==TARGET_KEYS)
 for field in ('installation_id','node_id','computer_name'):need(type(target[field]) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{0,63}',target[field]))
 role=target['role'];role='SINGLE_PC' if role=='SINGLE-PC' else role;need(role in ('CONTROL','WORKER','SINGLE_PC'))
 old_root=_path(config['programs']['grid']['env']['UNIFIED_SOURCE_ROOT'],legacy_base=True).parents[1]
 # Validate declared original paths/entrypoints before rewriting anything. The
 # supplied hostname is offline metadata, never proof of current host identity.
 old_node=config['node_id'];need(old_node.upper() in lab_runtime.LAB_NODES)
 lab_runtime.validate_config(config,manifest,old_root,hostname=lab_runtime.LAB_HOSTNAMES[old_node.upper()])
 for program in config['programs'].values():
  if 'ca_file' in program:
   ca=_path(program['ca_file'],legacy_base=True).resolve(strict=False);resolved_base=old_root.resolve(strict=False);need(resolved_base in ca.parents and ca.relative_to(resolved_base).as_posix() in manifest['files'])
 code=_path(target['code_root']);state=_path(target['state_root']);credential=_path(target['credential_root'])
 for left,right in ((code,state),(code,credential),(state,credential),(code,old_root.resolve(strict=False)),(state,old_root.resolve(strict=False)),(credential,old_root.resolve(strict=False))):
  need(left!=right and left not in right.parents and right not in left.parents)
 auth=target['auth_binding'];need(type(auth) is dict and set(auth)=={'path','sha256'})
 path=_path(auth['path']);need(credential in path.parents);lab_release.digest(auth['sha256'])
 pg=target['postgres_binding'];dsn=None
 if role=='WORKER':need(pg is None)
 else:
  need(type(pg) is dict and set(pg)=={'database','user','port'})
  for field in ('database','user'):need(type(pg[field]) is str and re.fullmatch('unified_lab_[a-z0-9_]{1,48}',pg[field]))
  need(type(pg['port']) is int and 1024<=pg['port']<=65535 and pg['port'] not in target['ports'].values())
  dsn=f"postgresql://{pg['user']}@127.0.0.1:{pg['port']}/{pg['database']}"
 derived=rebase_config(config,node_id=target['node_id'],role=role,old_root=old_root,new_root=code,new_state=state,ports=target['ports'],coordinator_port=target['coordinator_port'],auth_path=path,auth_sha256=auth['sha256'],postgres_dsn=dsn)
 derived['release_sha256']=base_manifest_sha256
 context=dict(scope='OFFLINE_VALIDATION_ONLY',role=role,node_id=target['node_id'],computer_name=target['computer_name'],credential_root=str(credential))
 derived=lab_runtime.validate_config(derived,manifest,code,hostname=target['computer_name'],offline_context=context)
 receipt=dict(schema='unified.runtime-profile-derivation.v1',base_manifest_sha256=base_manifest_sha256,base_config_sha256=hashlib.sha256(raw).hexdigest(),profile_sha256=hashlib.sha256(lab_release.canonical(derived)).hexdigest(),installation_id=target['installation_id'],node_id=target['node_id'],computer_name=target['computer_name'],role=role,sources=copy.deepcopy(manifest['sources']))
 return dict(schema='unified.runtime-profile.v1',status='DERIVED_PROFILE_ONLY',runtime_config=derived,offline_context=context,derivation_receipt=receipt,
  activation='BLOCKED',execution_authority=False,source_proof='NOT_EVALUATED',acl_qualification='NOT_EVALUATED',credential_qualification='NOT_EVALUATED',database_ownership='NOT_EVALUATED',capacity='NOT_EVALUATED',physical_acceptance='NOT_RUN')


def derive_runtime_profile(base_config,base_manifest,*,base_manifest_sha256,target,data_first=None):
 try:
  result=_derive_runtime_profile(base_config,base_manifest,base_manifest_sha256=base_manifest_sha256,target=target)
  if data_first is not None:
   from .data_first_policy import validate_data_first_grant
   result['data_first']=validate_data_first_grant(data_first,base_manifest)
  return result
 except (TypeError,KeyError,IndexError,AttributeError,OverflowError) as exc:raise ValueError('RUNTIME_PROFILE_REJECTED') from exc
