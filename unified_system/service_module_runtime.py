"""Closed Python application routes, supplied only after full raw admission."""
import copy,importlib,os,sys
from pathlib import Path
from .service_bootstrap import need,local
from .service_source_admission import StartupSourceAdmission

ENTRIES={'meta_analyse':'meta_analyse.headless_service','strattester':'strattester.owned_results_service','terminan':'terminan.unified_runner'}

def protected_programs(config,grant,manifest):
 result=copy.deepcopy(config)
 entry=grant.code_root/manifest['sources']['unified-system']['root']/'unified_system/service_entry.py'
 relative=entry.relative_to(grant.code_root).as_posix();need(relative in manifest['files'])
 for module_id in ENTRIES:
  program=result['programs'][module_id]
  program['argv']=[program['argv'][0],'-I','-S','-B',str(entry),'--module-source',module_id]
  program.setdefault('external_file_pins',{})[str(entry)]=manifest['files'][relative]['sha256']
 return result

def serve_module(grant,config,manifest,module_id,*,verify_only=False):
 need(module_id in ENTRIES and (not verify_only or module_id=='strattester'))
 from unified_system import owned_python
 source=StartupSourceAdmission(grant,config,manifest)
 state=local(config['state_root']);cache=local(os.environ.get('UNIFIED_PRIVATE_CACHE_ROOT',''))
 need(state in cache.parents and cache.is_dir())
 need(os.environ.get('UNIFIED_MODULE_ID')==module_id and os.environ.get('UNIFIED_MODULE_VERSION')==manifest['sources'][module_id]['version'] and os.environ.get('UNIFIED_RELEASE_ID')==config['release_id'])
 original=config['programs'][module_id]['argv'];index=original.index('--module')
 need(original[index+1:index+3]==[ENTRIES[module_id],'--'])
 arguments=copy.deepcopy(original[index+3:])
 def run():
  need(source.require_current() is True)
  module=importlib.import_module(ENTRIES[module_id])
  if verify_only:
   module.check_source(startup_admission=source);return 0
  return module.main(arguments,startup_admission=source)
 previous=sys.argv
 try:
  # Preserve the original closed source/dependency/module discovery and cache
  # isolation; only the in-process constructor callback carries scoped state.
  sys.argv=copy.deepcopy(original[4:])
  return owned_python.main(admitted_run=run)
 finally:sys.argv=previous
