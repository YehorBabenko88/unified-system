"""Collector-only read-only plan validation. No registration or activation API."""
import copy
import hashlib
from pathlib import Path
import re

from . import lab_release
from .runtime_process import _safe_path

SCHEMA='unified.owned-collector-stopped-service.v1'
NSSM_PIN='eee9c44c29c2be011f1f1e43bb8c3fca888cb81053022ec5a0060035de16d848'
SECURITY_PIN='a8012a04c4a0507a72bd6ba38c63ad0af855d5f25efea7669ea11db1386d8d45'
ENTRY_PIN='3645dddef0ac6479edcc22ac61203db14fe802aa37641fa50ef2c1535f46f3cb'
BOOTSTRAP_PIN='6d3be096e0df7d7633b14b55ec9d049e25b537bb530ba17f995c10a357b85005'
EXECUTOR_PIN='ee0ec4d73e92a234396a37622e8080967105c497cf538f66e703021cbc3978bf'
PREFIX='sources/unified-system/unified_system/'
PATHS={'python':'runtime/python/python.exe','nssm':'runtime/nssm/nssm.exe',
       'entry':PREFIX+'collector_service_entry.py','bootstrap':PREFIX+'collector_service_bootstrap.py'}
REVIEWED_FILES={PREFIX+n:Path(__file__).with_name(n) for n in
                ('collector_service_entry.py','collector_service_bootstrap.py','service_bootstrap.py')}
REVIEWED_FILES['sources/unified-system/scripts/UnifiedOwnedService.psm1']=Path(__file__).parents[1]/'scripts/UnifiedOwnedService.psm1'
FIELDS=frozenset(('schema','installation_id','node_id','computer_name','role','root','code','state',
 'capsule_root','manifest_sha256','service_name','service_sid','nssm','nssm_sha256','python','python_sha256',
 'bootstrap','bootstrap_sha256','entry','entry_sha256','parameters','executor_sha256','native_tools',
 'activation','plan_sha256','collector_profile_sha256','source_manifest_sha256',
 'collector_bootstrap_sha256','security_helper_sha256','job_helper_sha256'))

class CollectorServiceBlocked(ValueError):
 def __init__(self):super().__init__('COLLECTOR_SERVICE_PLAN_REJECTED')

def _need(ok):
 if not ok:raise CollectorServiceBlocked()

def _digest(value):_need(type(value) is str and re.fullmatch('[a-f0-9]{64}',value) is not None)
def _label(value):_need(type(value) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{0,63}',value) is not None)
def _seal(value):return hashlib.sha256(lab_release.canonical(value)).hexdigest()

def _keys(value,fields):
 _need(type(value) is dict and all(type(k) is str for k in value) and set(value)==fields)

def _shape(plan):
 _keys(plan,FIELDS)
 # All scalar fields are wire strings. Reject subclasses before JSON sealing,
 # equality, hashing or filesystem verification can invoke caller behavior.
 _need(all(type(plan[k]) is str for k in FIELDS if k!='native_tools'))
 _keys(plan['native_tools'],{'sc','powershell'})
 for tool in plan['native_tools'].values():
  _keys(tool,{'path','sha256'});_need(all(type(v) is str for v in tool.values()))

def _path(value):
 _need(type(value) is str and 0<len(value)<=4096 and not any(c in value for c in ('"','\0','\r','\n')))
 path=_safe_path(value);_need(path.is_absolute() and str(path)==value);return path

def _members(manifest):
 _need(type(manifest) is dict and manifest.get('schema')==lab_release.COLLECTOR_SCHEMA)
 files=manifest['files']
 for relative,pin in ((PATHS['entry'],ENTRY_PIN),(PATHS['bootstrap'],BOOTSTRAP_PIN),
                      (PREFIX+'service_bootstrap.py',SECURITY_PIN),(PATHS['nssm'],NSSM_PIN),
                      ('sources/unified-system/scripts/UnifiedOwnedService.psm1',EXECUTOR_PIN)):
  _need(files.get(relative,{}).get('sha256')==pin)
 _need('sources/grid/grid/ml_windows_job.py' in files)
 _need(manifest['runtime']['python']['path']==PATHS['python'])
 return files

def _check_manifest(plan,manifest):
 """Validate an already byte-verified manifest; never grants native authority."""
 _shape(plan)
 _need(plan['schema']==SCHEMA and plan['role']=='COLLECTOR' and plan['activation']=='BLOCKED')
 _digest(plan['plan_sha256']);_need(_seal({k:v for k,v in plan.items() if k!='plan_sha256'})==plan['plan_sha256'])
 for key in FIELDS:
  if key.endswith('_sha256'):_digest(plan[key])
 for key in ('installation_id','node_id','computer_name'):_label(plan[key])
 root=_path(plan['root']);source=_path(plan['capsule_root']);code=root/'code'
 _need(source!=root and source not in root.parents and root not in source.parents)
 _need(plan['code']==str(code) and plan['state']==str(root/'state'))
 name='UnifiedCollector_'+_seal(dict(domain=SCHEMA,installation_id=plan['installation_id'],node_id=plan['node_id']))[:24]
 _need(plan['service_name']==name)
 _need(type(plan['service_sid']) is str and re.fullmatch(r'S-1-5-80-(?:[0-9]+-){4}[0-9]+',plan['service_sid']) is not None)
 files=_members(manifest)
 for key,relative in PATHS.items():
  _need(relative in files and plan[key]==str(code/relative) and plan[key+'_sha256']==files[relative]['sha256'])
 _need(plan['collector_bootstrap_sha256']==BOOTSTRAP_PIN and plan['security_helper_sha256']==SECURITY_PIN)
 _need(plan['executor_sha256']==EXECUTOR_PIN)
 _need(plan['job_helper_sha256']==files['sources/grid/grid/ml_windows_job.py']['sha256'])
 for key,member in [('collector_profile_sha256','collector_profile'),('source_manifest_sha256','source_manifest')]:
  _need(plan[key]==files[manifest[member]]['sha256'])
 _need(plan['parameters']=='-I -S -B "'+plan['entry']+'"')
 tools=plan['native_tools']
 for tool in tools.values():
  _path(tool['path']);_digest(tool['sha256'])
 # Existing PSM1 is pinned only as a declared executor; it DOES NOT accept this
 # new kind. Source provenance/operational qualification remain independent.
 return copy.deepcopy(manifest)

def check_collector_service_plan(plan):
 try:
  _shape(plan)
  report=lab_release.verify_capsule(_path(plan['capsule_root']),plan['manifest_sha256'])
  return _check_manifest(plan,report['manifest'])
 except CollectorServiceBlocked:raise
 except Exception:raise CollectorServiceBlocked() from None

def collector_service_plan(capsule_root,manifest_sha256,root,installation_id,node_id,boundary):
 try:
  source=_path(str(capsule_root));target=_path(str(root));_need(target.parent.is_dir())
  _need(source!=target and source not in target.parents and target not in source.parents)
  report=lab_release.verify_capsule(source,manifest_sha256);manifest=report['manifest'];files=_members(manifest)
  for value in (installation_id,node_id):_label(value)
  body=dict(schema=SCHEMA,installation_id=installation_id,node_id=node_id,computer_name=boundary.computer_name(),
   role='COLLECTOR',root=str(target),code=str(target/'code'),state=str(target/'state'),capsule_root=str(source),
   manifest_sha256=manifest_sha256,activation='BLOCKED',collector_bootstrap_sha256=BOOTSTRAP_PIN,
   security_helper_sha256=SECURITY_PIN,job_helper_sha256=files['sources/grid/grid/ml_windows_job.py']['sha256'],
   collector_profile_sha256=files[manifest['collector_profile']]['sha256'],source_manifest_sha256=files[manifest['source_manifest']]['sha256'])
  body['service_name']='UnifiedCollector_'+_seal(dict(domain=SCHEMA,installation_id=installation_id,node_id=node_id))[:24]
  for key,relative in PATHS.items():body.update({key:str(target/'code'/relative),key+'_sha256':files[relative]['sha256']})
  body['parameters']='-I -S -B "'+body['entry']+'"'
  # Read-only injected boundary metadata; no default native boundary is created.
  body['service_sid']=boundary.sid(body['service_name']);body['native_tools']=boundary.native_tools()
  body['executor_sha256']=EXECUTOR_PIN
  plan={**body,'plan_sha256':_seal(body)};_check_manifest(plan,manifest);return plan
 except CollectorServiceBlocked:raise
 except Exception:raise CollectorServiceBlocked() from None

def expected_collector_service(plan):
 check_collector_service_plan(plan)
 return dict(service_name=plan['service_name'],service_sid=plan['service_sid'],account='NT AUTHORITY\\LocalService',
  start_type=3,sid_type=1,state=1,binary_path='"'+plan['nssm']+'"',application=plan['python'],parameters=plan['parameters'],
  directory=plan['code'],app_exit='Exit',marker=plan['plan_sha256'],acl_policy='EXACT_SERVICE_SID_V1',execution_authority=False)
