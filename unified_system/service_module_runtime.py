"""Closed Python application routes, supplied only after full raw admission."""
import copy,importlib,os,sys
from pathlib import Path
from urllib.parse import urlsplit
from .service_bootstrap import need,local
from .service_source_admission import StartupSourceAdmission

ENTRIES={'meta_analyse':'meta_analyse.headless_service','strattester':'strattester.owned_results_service','terminan':'terminan.unified_runner'}
GRID_ENTRY='grid.owned_control_service'

def _control_arguments(grant,config,manifest):
 need(grant.descriptor['service_plan']['role'] in ('CONTROL','SINGLE_PC'))
 program=config['programs']['grid'];original=program['argv']
 health=urlsplit(program['health_url']);port=health.port
 need(type(port) is int and 1<=port<=65535)
 need(program['health_url']==f'http://127.0.0.1:{port}/internal/v2/module/health')
 need(type(original) is list and len(original)==18 and all(type(part) is str for part in original))
 root=grant.code_root;python=Path(original[0]);need(python.is_absolute() and root in python.parents)
 need(python.relative_to(root).as_posix() in manifest['files'])
 bootstrap=root/manifest['sources']['unified-system']['root']/'unified_system/owned_python.py'
 need(original==[str(python),'-I','-S','-B',str(bootstrap),'--source-root',str(root/'dependencies/site-packages'),
                 '--dependency-root',str(root/manifest['sources']['grid']['root']),'--module','uvicorn','--',
                 'grid.coordinator:app','--host','127.0.0.1','--port',str(port),'--no-access-log'])
 return ['--execute','--port',str(port)]

def protected_programs(config,grant,manifest):
 result=copy.deepcopy(config)
 entry=grant.code_root/manifest['sources']['unified-system']['root']/'unified_system/service_entry.py'
 relative=entry.relative_to(grant.code_root).as_posix();need(relative in manifest['files'])
 modules=list(ENTRIES)
 if 'grid' in result['programs']:
  role=grant.descriptor['service_plan']['role'];need(role in ('CONTROL','SINGLE_PC','WORKER'))
  if role!='WORKER':_control_arguments(grant,config,manifest);modules.append('grid')
 for module_id in modules:
  program=result['programs'][module_id]
  program['argv']=[program['argv'][0],'-I','-S','-B',str(entry),'--module-source',module_id]
  program.setdefault('external_file_pins',{})[str(entry)]=manifest['files'][relative]['sha256']
 return result

def serve_module(grant,config,manifest,module_id,*,verify_only=False):
 need(module_id in (*ENTRIES,'grid') and (not verify_only or module_id=='strattester'))
 arguments=_control_arguments(grant,config,manifest) if module_id=='grid' else None
 from unified_system import owned_python
 source=StartupSourceAdmission(grant,config,manifest)
 state=local(config['state_root']);cache=local(os.environ.get('UNIFIED_PRIVATE_CACHE_ROOT',''))
 need(state in cache.parents and cache.is_dir())
 need(os.environ.get('UNIFIED_MODULE_ID')==module_id and os.environ.get('UNIFIED_MODULE_VERSION')==manifest['sources'][module_id]['version'] and os.environ.get('UNIFIED_RELEASE_ID')==config['release_id'])
 original=config['programs'][module_id]['argv'];index=original.index('--module')
 if module_id!='grid':
  need(original[index+1:index+3]==[ENTRIES[module_id],'--'])
  arguments=copy.deepcopy(original[index+3:])
 def run():
  need(source.require_current() is True)
  module=importlib.import_module(GRID_ENTRY if module_id=='grid' else ENTRIES[module_id])
  if verify_only:
   module.check_source(startup_admission=source);return 0
  return module.main(arguments,startup_admission=source)
 previous=sys.argv
 try:
  # Preserve the original closed source/dependency/module discovery and cache
  # isolation; only the in-process constructor callback carries scoped state.
  if module_id=='grid':
   # The serialized CONTROL profile retains the original reviewed Uvicorn
   # dependency discovery. The protected callback itself is always Grid-owned.
   sys.argv=['owned-python','--source-root',str(grant.code_root/manifest['sources']['grid']['root']),
             '--dependency-root',str(grant.code_root/'dependencies/site-packages'),'--module',GRID_ENTRY]
  else:sys.argv=copy.deepcopy(original[4:])
  return owned_python.main(admitted_run=run)
 finally:sys.argv=previous
