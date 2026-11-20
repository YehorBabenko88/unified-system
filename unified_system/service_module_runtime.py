"""Canonical application routes after raw source admission; no legacy factories."""
import copy,importlib,os,sys
from pathlib import Path
from urllib.parse import urlsplit
from .module_catalog import MODULE_IDS
from .service_bootstrap import need,local
from .service_source_admission import StartupSourceAdmission

ENTRIES={'market_data':'market_data.cli','terminan':'terminan.server'}

def _module_arguments(grant,config,manifest,module_id):
 need(module_id in ENTRIES and type(config.get('programs')) is dict)
 need(set(config['programs'])<=set(MODULE_IDS))
 program=config['programs'].get(module_id);need(type(program) is dict)
 original=program.get('argv');need(type(original) is list and bool(original) and all(type(x) is str for x in original))
 health=urlsplit(program.get('health_url',''));port=health.port
 need(type(port) is int and 1<=port<=65535)
 need(program['health_url']==f'http://127.0.0.1:{port}/health')
 root=local(grant.code_root);sources=manifest['sources']
 need(set(sources)==set(MODULE_IDS))
 python=local(original[0]);need(root in python.parents and python.relative_to(root).as_posix() in manifest['files'])
 bootstrap=root/sources['unified_system']['root']/'unified_system/owned_python.py'
 source=root/sources[module_id]['root'];dependencies=root/'dependencies/site-packages'
 arguments=['serve'] if module_id=='market_data' else ['--host','127.0.0.1','--port',str(port)]
 if module_id=='market_data':need(program.get('env',{}).get('MARKET_DATA_PORT')==str(port))
 need(original==[str(python),'-I','-S','-B',str(bootstrap),'--source-root',str(source),
                 '--dependency-root',str(dependencies),'--module',ENTRIES[module_id],'--',*arguments])
 return arguments

def protected_programs(config,grant,manifest):
 result=copy.deepcopy(config)
 need(type(result.get('programs')) is dict and set(result['programs'])<=set(MODULE_IDS))
 entry=grant.code_root/manifest['sources']['unified_system']['root']/'unified_system/service_entry.py'
 relative=entry.relative_to(grant.code_root).as_posix();need(relative in manifest['files'])
 for module_id in ENTRIES:
  if module_id not in result['programs']:continue
  _module_arguments(grant,config,manifest,module_id)
  program=result['programs'][module_id]
  program['argv']=[program['argv'][0],'-I','-S','-B',str(entry),'--module-source',module_id]
  program.setdefault('external_file_pins',{})[str(entry)]=manifest['files'][relative]['sha256']
 return result

def serve_module(grant,config,manifest,module_id):
 need(module_id in ENTRIES)
 arguments=_module_arguments(grant,config,manifest,module_id)
 from unified_system import owned_python
 source=StartupSourceAdmission(grant,config,manifest)
 state=local(config['state_root']);cache=local(os.environ.get('UNIFIED_PRIVATE_CACHE_ROOT',''))
 need(state in cache.parents and cache.is_dir())
 need(os.environ.get('UNIFIED_MODULE_ID')==module_id
      and os.environ.get('UNIFIED_MODULE_VERSION')==manifest['sources'][module_id]['version']
      and os.environ.get('UNIFIED_RELEASE_ID')==config['release_id'])
 original=config['programs'][module_id]['argv']
 def run():
  need(source.require_current() is True)
  module=importlib.import_module(ENTRIES[module_id])
  return module.main(arguments,startup_admission=source)
 previous=sys.argv
 try:
  sys.argv=copy.deepcopy(original[4:])
  return owned_python.main(admitted_run=run)
 finally:sys.argv=previous
