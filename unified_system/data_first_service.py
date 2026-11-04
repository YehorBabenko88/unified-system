"""Fixed research child constructor after central protected full admission."""
import os,sys
from pathlib import Path
from .service_bootstrap import need,local,_repeat_admission
from .data_first_workspace import admit_data_first_workspace

def serve_research(grant,config,manifest,cap):
 from unified_system import lab_release,owned_python
 workspace=admit_data_first_workspace(grant,manifest)
 # A child may use only its existing Grid-owned immediate temporary namespace.
 cwd=local(Path.cwd());need(cwd.parent==workspace.root and cwd.name.startswith('data-first-'))
 cache=local(os.environ.get('UNIFIED_PRIVATE_CACHE_ROOT',''));need(cache==cwd/'cache' and cache.is_dir())
 need(os.environ.get('UNIFIED_MODULE_ID')=='strattester')
 need(os.environ.get('UNIFIED_MODULE_VERSION')==manifest['sources']['strattester']['version'])
 need(os.environ.get('UNIFIED_RELEASE_ID')==config['release_id'])
 source=grant.code_root/manifest['sources']['strattester']['root']
 deps=grant.code_root/'dependencies/site-packages'
 def readmission(current):
  need(current is grant and workspace.require_current() is True)
  repeated,_auth=_repeat_admission(grant,lab_release)
  need(repeated==config,'ACTIVATION_REVISION_CHANGED')
  return repeated,manifest
 def run():
  need(workspace.require_current() is True)
  from strattester.engine.grid_data_first_factory import build_scheduler
  from strattester.engine.grid_data_first_worker import serve
  scheduler=build_scheduler(grant,readmission)
  try:return serve(scheduler,cap['source_commit'])
  finally:
   # Scheduler construction owns only its existing domain handles; no adoption
   # or recursive deletion is performed by this entry.
   close=getattr(scheduler,'close',None)
   if callable(close):close()
 previous=sys.argv
 try:
  sys.argv=['owned-python','--source-root',str(source),'--dependency-root',str(deps),'--module','strattester.engine.grid_data_first_worker']
  return owned_python.main(admitted_run=run)
 finally:sys.argv=previous


def worker_program(config,grant,manifest):
 """Closed internal child-route rewrite, never a serialized launch permission."""
 import copy
 from .data_first_policy import validate_data_first_grant
 validate_data_first_grant(grant.profile.get('data_first'),manifest)
 need(grant.descriptor['service_plan']['role']=='WORKER')
 result=copy.deepcopy(config)
 entry=grant.code_root/manifest['sources']['unified-system']['root']/'unified_system/service_entry.py'
 relative=entry.relative_to(grant.code_root).as_posix();need(relative in manifest['files'])
 program=result['programs']['grid']
 program['argv']=[program['argv'][0],'-I','-S','-B',str(entry),'--data-first-worker']
 program.setdefault('external_file_pins',{})[str(entry)]=manifest['files'][relative]['sha256']
 return result

def serve_worker(grant,config,manifest,cap):
 from unified_system import lab_release,owned_python
 from urllib.parse import urlsplit
 need(grant.descriptor['service_plan']['role']=='WORKER')
 state=local(config['state_root']);cache=local(os.environ.get('UNIFIED_PRIVATE_CACHE_ROOT',''))
 need(state in cache.parents and cache.is_dir())
 need(os.environ.get('UNIFIED_MODULE_ID')=='grid')
 need(os.environ.get('UNIFIED_MODULE_VERSION')==manifest['sources']['grid']['version'])
 need(os.environ.get('UNIFIED_RELEASE_ID')==config['release_id'])
 def readmission(current):
  need(current is grant)
  repeated,_auth=_repeat_admission(grant,lab_release)
  need(repeated==config,'ACTIVATION_REVISION_CHANGED');return repeated,manifest
 def run():
  import asyncio
  from grid.data_first_runtime import ProtectedDataFirstAdmission
  from grid.owned_worker_service import serve
  admission=ProtectedDataFirstAdmission(grant,readmission)
  admission.admitted(full=True)
  asyncio.run(serve(urlsplit(config['programs']['grid']['health_url']).port,data_first_admission=admission))
  return 0
 previous=sys.argv
 try:
  sys.argv=['owned-python','--source-root',str(grant.code_root/manifest['sources']['grid']['root']),'--dependency-root',str(grant.code_root/'dependencies/site-packages'),'--module','grid.owned_worker_service']
  return owned_python.main(admitted_run=run)
 finally:sys.argv=previous
