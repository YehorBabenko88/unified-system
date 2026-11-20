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
 'MARKET_DATA_PINNED_HISTORY_CATALOG'))
TARGET_KEYS={'installation_id','node_id','computer_name','role','code_root','state_root','credential_root','ports','database_credential_binding','postgres_binding'}


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


def rebase_config(config,*,node_id,role,old_root,new_root,new_state,ports,database_credential_path=None,database_credential_sha256=None,postgres_dsn=None):
 """Shared pure transform; worker facade retains its existing caller guards.

 Only reviewed path slots are rebased. High-level derivation validates both the
 original and derived launch profiles; this helper alone grants no admission.
 """
 config=copy.deepcopy(config);ports=copy.deepcopy(ports)
 need(role in ('CONTROL','WORKER','SINGLE_PC') and type(node_id) is str and re.fullmatch('[A-Za-z0-9_-]{1,64}',node_id))
 need(type(ports) is dict and set(ports)==MODULES and all(type(p) is int and 1024<=p<=65535 for p in ports.values()) and len(set(ports.values()))==len(MODULES))
 if role=='WORKER':need(postgres_dsn is None and database_credential_path is None and database_credential_sha256 is None)
 else:
  credential=_path(database_credential_path);lab_release.digest(database_credential_sha256)
 old_root=_path(old_root,legacy_base=True);new_root=_path(new_root);old_state=_path(config['state_root'],legacy_base=True);new_state=_path(new_state)
 need(new_root!=new_state and new_root not in new_state.parents and new_state not in new_root.parents)
 def text(value):
  if type(value) is not str:return value
  for old,new in ((old_root,new_root),(old_state,new_state)):
   if value==str(old):return str(new)
   if value.startswith(str(old)+'\\') or value.startswith(str(old)+'/'):return str(new)+value[len(str(old)):]
  return value
 config['state_root']=str(new_state);config['snapshot_path']=text(config['snapshot_path']);config['node_id']=node_id;config['http_port']=ports['unified_system']
 for name,program in config['programs'].items():
  program['cwd']=text(program['cwd']);program['argv']=[text(value) for value in program['argv']]
  if 'ca_file' in program:program['ca_file']=text(program['ca_file'])
  if 'external_file_pins' in program:program['external_file_pins']={text(key):value for key,value in program['external_file_pins'].items()}
  env=program.get('env',{})
  for key,value in list(env.items()):
   if key.upper() in PATH_ENV:env[key]=text(value)
   elif key.upper()=='PATH':env[key]=os.pathsep.join(text(item) for item in value.split(os.pathsep))
  previous=program['health_url'].rsplit(':',1)[1].split('/',1)[0]
  route='/internal/v2/module/health' if name=='math' else '/health'
  program['health_url']=f'http://127.0.0.1:{ports[name]}{route}'
  if name=='terminan':
   args=program['argv'];port_index=args.index('--port');need(args[port_index+1]==previous);args[port_index+1]=str(ports[name])
  elif name=='market_data':program.setdefault('env',{})['MARKET_DATA_PORT']=str(ports[name])
  elif name=='math':program.setdefault('env',{})['MATH_ENGINE_PORT']=str(ports[name])
  else:need(False)
 for name,program in config['programs'].items():
  need(not any(key.upper() in ('PGPASSWORD','NODE_CREDENTIAL','GRID_SHARED_TOKEN','POSTGRES_DSN','COORDINATOR_URL','GRID_LAB_AUTH_PATH','GRID_LAB_AUTH_SHA256') for key in program['env']))
  if name!='market_data':need(not any(key.upper()=='MARKET_DATA_DSN' for key in program['env']))
 data=config['programs']['market_data'];env=data['env']
 for key in list(env):
  if key.upper()=='MARKET_DATA_DSN':del env[key]
 if role!='WORKER':
  need(type(postgres_dsn) is str);env['MARKET_DATA_DSN']=postgres_dsn

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
 old_root=_path(config['programs']['market_data']['env']['UNIFIED_SOURCE_ROOT'],legacy_base=True).parents[1]
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
 binding=target['database_credential_binding'];path=None;credential_pin=None
 if role=='WORKER':need(binding is None)
 else:
  need(type(binding) is dict and set(binding)=={'path','sha256'})
  path=_path(binding['path']);need(credential in path.parents);lab_release.digest(binding['sha256']);credential_pin=binding['sha256']
 pg=target['postgres_binding'];dsn=None
 if role=='WORKER':need(pg is None)
 else:
  need(type(pg) is dict and set(pg)=={'database','user','port'})
  for field in ('database','user'):need(type(pg[field]) is str and re.fullmatch('unified_lab_[a-z0-9_]{1,48}',pg[field]))
  need(type(pg['port']) is int and 1024<=pg['port']<=65535 and pg['port'] not in target['ports'].values())
  dsn=f"postgresql://{pg['user']}@127.0.0.1:{pg['port']}/{pg['database']}"
 derived=rebase_config(config,node_id=target['node_id'],role=role,old_root=old_root,new_root=code,new_state=state,ports=target['ports'],database_credential_path=path,database_credential_sha256=credential_pin,postgres_dsn=dsn)
 derived['release_sha256']=base_manifest_sha256
 context=dict(scope='OFFLINE_VALIDATION_ONLY',role=role,node_id=target['node_id'],computer_name=target['computer_name'],credential_root=str(credential))
 derived=lab_runtime.validate_config(derived,manifest,code,hostname=target['computer_name'],offline_context=context)
 receipt=dict(schema='unified.runtime-profile-derivation.v2',base_manifest_sha256=base_manifest_sha256,base_config_sha256=hashlib.sha256(raw).hexdigest(),profile_sha256=hashlib.sha256(lab_release.canonical(derived)).hexdigest(),installation_id=target['installation_id'],node_id=target['node_id'],computer_name=target['computer_name'],role=role,sources=copy.deepcopy(manifest['sources']))
 return dict(schema='unified.runtime-profile.v2',status='DERIVED_PROFILE_ONLY',database_credential_binding=copy.deepcopy(binding),runtime_config=derived,offline_context=context,derivation_receipt=receipt,
  activation='BLOCKED',execution_authority=False,source_proof='NOT_EVALUATED',acl_qualification='NOT_EVALUATED',credential_qualification='NOT_EVALUATED',database_ownership='NOT_EVALUATED',capacity='NOT_EVALUATED',physical_acceptance='NOT_RUN')


def derive_runtime_profile(base_config,base_manifest,*,base_manifest_sha256,target,data_first=None):
 try:
  result=_derive_runtime_profile(base_config,base_manifest,base_manifest_sha256=base_manifest_sha256,target=target)
  if data_first is not None:
   from .data_first_policy import validate_data_first_grant
   result['data_first']=validate_data_first_grant(data_first,base_manifest)
  return result
 except (TypeError,KeyError,IndexError,AttributeError,OverflowError) as exc:raise ValueError('RUNTIME_PROFILE_REJECTED') from exc
