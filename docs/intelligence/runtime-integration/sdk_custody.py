"""Hosted READ source/installed SDK custody; no identity or disclosure grant.

Reuses SourceFence and import_custody. Raw wheel bytes originate solely in the
existing four-owner qualifier, not RECORD claims or ambient SDK installations.
"""
import hashlib,importlib.machinery,importlib.metadata,importlib.util,json,os,pathlib,sys,sysconfig,zipfile
SDK_TOP={'market_data','terminan','market_math','market_compute_api','history_statistics'}
DEPENDENCIES={'cryptography':'46.0.3','cffi':'2.0.0','pycparser':'2.23'}

def ordinary(path):
 for item in (path,*path.parents):
  info=item.lstat()
  if item.is_symlink() or getattr(info,'st_file_attributes',0)&1024:raise ValueError('READ_CUSTODY_PATH_ALIAS')

def installed_site(qualification):
 return qualification/'installed'/('Lib/site-packages' if os.name=='nt' else 'lib/python3.12/site-packages')

def check_result(result,expected):
 actual=getattr(result,'started',[])
 if (result.testsRun!=len(expected) or len(actual)!=len(set(actual)) or set(actual)!=set(expected) or not result.wasSuccessful() or result.skipped or result.expectedFailures or result.unexpectedSuccesses):raise ValueError('EXACT_READ_RESULTS_REQUIRED')

def dependency_snapshot(site):
 records={}
 for name,version in DEPENDENCIES.items():
  dist=importlib.metadata.distribution(name)
  if dist.metadata.get('Name','').lower()!=name or dist.version!=version or pathlib.Path(dist.locate_file('')).resolve()!=site:raise ValueError('PINNED_READ_DEPENDENCY_ORIGIN_REQUIRED')
  if not dist.files:raise ValueError('DEPENDENCY_FILE_ROSTER_REQUIRED')
  for member in dist.files:
   relative=pathlib.Path(str(member))
   # Installed command wrappers are not imported; bind all files under purelib.
   if relative.is_absolute() or '..' in relative.parts:continue
   path=site/relative;ordinary(path)
   if not path.is_file():raise ValueError('DEPENDENCY_ORDINARY_FILE_REQUIRED')
   records[str(path.resolve())]=hashlib.sha256(path.read_bytes()).hexdigest()
 return records



def verify_source_bindings(bindings,fences,heads,sources):
 """One exact owner/relative/source-path bijection for raw qualifier members."""
 if type(bindings) is not dict:raise ValueError('SDK_SOURCE_BINDINGS_REQUIRED')
 expected={}
 math_files={'python/market_math.py','python/market_compute_api.py','python/history_statistics.py'}
 for owner in ('market_data','math','terminan'):
  fence=fences[owner];spec=sources[owner]
  selected={name for name in fence.files if any(name==prefix or prefix.endswith('/') and name.startswith(prefix) for prefix in spec['build_members'])}-{ 'README.md','pyproject.toml'}
  if owner=='math':
   if selected!=math_files:raise ValueError('EXACT_MATH_BUILD_MEMBERS_REQUIRED')
  elif any(not name.startswith(owner+'/') for name in selected):raise ValueError('EXACT_PACKAGE_BUILD_MEMBERS_REQUIRED')
  for source in selected:
   relative=source[7:] if owner=='math' else source
   if relative in expected:raise ValueError('SDK_SOURCE_MEMBER_COLLISION')
   expected[relative]=(owner,source)
 if set(bindings)!=set(expected):raise ValueError('COMPLETE_SDK_SOURCE_ROSTER_REQUIRED')
 for relative,(owner,source) in expected.items():
  record=bindings[relative];fence=fences[owner]
  if record['owner']!=owner or record['commit']!=heads[owner] or record['source_path']!=source:raise ValueError('SDK_CANONICAL_SOURCE_PATH_REQUIRED')
  if hashlib.sha256(fence.blobs[fence.files[source]]).hexdigest()!=record['sha256']:raise ValueError('SDK_BINDING_NOT_EXACT_GIT_SOURCE')
 return {'runtime_files':len(expected),'owners':['market_data','math','terminan']}

def verify_site_roster(site):
 """Closed installed-domain top level; pip is inert bootstrap, never SDK.

 Python3.12.10 venv.EnvBuilder(with_pip=True) provisions only bundled pip.
 Existing SDK pyc files are inert under the mandatory fresh CLI cache prefix.
 """
 import ensurepip
 sdk={'market_data','terminan','market_math.py','market_compute_api.py','history_statistics.py','market_data-0.1.0.dist-info','unified_math_kernels-0.1.0.dist-info','unified_terminan-0.1.0.dist-info'}
 pip_metadata='pip-'+ensurepip.version()+'.dist-info'
 allowed=sdk|{'pip',pip_metadata,'__pycache__'};seen=set()
 for entry in site.iterdir():
  ordinary(entry)
  if entry.name not in allowed:raise ValueError('UNBOUND_SDK_SITE_TOP_LEVEL')
  seen.add(entry.name)
  if entry.name in ('market_math.py','market_compute_api.py','history_statistics.py'):
   if not entry.is_file():raise ValueError('SDK_TOP_LEVEL_KIND_CHANGED')
  elif not entry.is_dir():raise ValueError('SDK_TOP_LEVEL_KIND_CHANGED')
  if entry.name=='__pycache__':
   for cached in entry.iterdir():
    ordinary(cached)
    if not cached.is_file() or cached.suffix!='.pyc':raise ValueError('NONINERT_SDK_CACHE_ENTRY')
 if not sdk<=seen:raise ValueError('SDK_SITE_TOP_LEVEL_INCOMPLETE')
 if ('pip' in seen)!=(pip_metadata in seen):raise ValueError('BOOTSTRAP_PIP_PAIR_REQUIRED')
 return {'sdk_top_level':sorted(sdk),'inert_bootstrap':sorted(seen-sdk)}

def verify_installed(site,bindings,wheels):
 verify_site_roster(site)
 if type(bindings) is not dict or not bindings:raise ValueError('RAW_SDK_BINDINGS_REQUIRED')
 owners=set();owned={}
 for relative,record in bindings.items():
  owner=('math' if relative in ('market_math.py','market_compute_api.py','history_statistics.py') else 'market_data' if relative.startswith('market_data/') else 'terminan' if relative.startswith('terminan/') else None)
  path=site/relative
  if owner is None or record['owner']!=owner or pathlib.Path(relative).is_absolute() or '..' in pathlib.Path(relative).parts:raise ValueError('SDK_BINDING_OWNER_REJECTED')
  ordinary(path)
  if not path.is_file() or not path.resolve().is_relative_to(site) or hashlib.sha256(path.read_bytes()).hexdigest()!=record['sha256']:raise ValueError('SDK_RAW_BYTES_OR_ORIGIN_CHANGED')
  owned[relative]=owner;owners.add(owner)
 if owners!={'market_data','math','terminan'}:raise ValueError('ALL_THREE_DOMAIN_SDKS_REQUIRED')
 for owner,(distribution,package) in {'market_data':('market-data','market_data'),'math':('unified-math-kernels',None),'terminan':('unified-terminan','terminan')}.items():
  dist=importlib.metadata.distribution(distribution)
  if dist.metadata.get('Name')!=distribution or dist.version!='0.1.0' or pathlib.Path(dist.locate_file('')).resolve()!=site:raise ValueError('SDK_DISTRIBUTION_ORIGIN_CHANGED')
  members={str(member).replace(chr(92),'/') for member in dist.files or ()}
  expected={name for name,value in owned.items() if value==owner}
  if not expected or not expected<=members:raise ValueError('SDK_DISTRIBUTION_OWNERSHIP_REQUIRED')
  for name in expected:
   if pathlib.Path(dist.locate_file(name)).resolve()!=(site/name).resolve():raise ValueError('SDK_DISTRIBUTION_OWNED_LOCATION_CHANGED')
  if package is not None:
   for file in (site/package).rglob('*'):
    ordinary(file)
    if file.is_file() and file.suffix.lower() in ('.py','.pyd','.so','.dll','.sql') and file.relative_to(site).as_posix() not in expected:raise ValueError('UNBOUND_SDK_EXECUTABLE_OR_SQL')
  wheel=wheels[owner];wheel_path=pathlib.Path(wheel['file']);ordinary(wheel_path)
  if hashlib.sha256(wheel_path.read_bytes()).hexdigest()!=wheel['sha256']:raise ValueError('QUALIFIED_SDK_WHEEL_CHANGED')
  with zipfile.ZipFile(wheel_path) as archive:
   names=archive.namelist()
   if len(names)!=len(set(names)):raise ValueError('DUPLICATE_WHEEL_MEMBER')
   runtime=set()
   for name in names:
    if name.endswith('/'):continue
    if pathlib.Path(name).is_absolute() or '..' in pathlib.Path(name).parts:raise ValueError('WHEEL_MEMBER_ESCAPE')
    if '.dist-info/' not in name:runtime.add(name)
    # pip legitimately regenerates RECORD; all original metadata payloads remain exact.
    if name.endswith('.dist-info/RECORD'):continue
    target=site/name;ordinary(target)
    if target.read_bytes()!=archive.read(name):raise ValueError('SDK_WHEEL_PAYLOAD_CHANGED')
   if runtime!=expected:raise ValueError('QUALIFIED_WHEEL_RUNTIME_ROSTER_CHANGED')
 return {'raw_files':len(bindings),'owners':sorted(owners)}

class ReadSDKCustody:
 def __init__(self,root,qualification,cache,guard,before):
  if os.environ.get('GITHUB_ACTIONS')!='true' or os.environ.get('RUNNER_ENVIRONMENT')!='github-hosted':raise ValueError('HOSTED_READ_CUSTODY_ONLY')
  self.root=root;ordinary(qualification);self.qualification=qualification.resolve();qualification=self.qualification;self.guard=guard;self.root_before=before
  site_path=installed_site(qualification).absolute();ordinary(site_path);self.site=site_path.resolve()
  dependencies=pathlib.Path(sysconfig.get_paths()['purelib']).absolute();ordinary(dependencies);self.dependencies=dependencies.resolve()
  if self.dependencies==self.site or self.dependencies.is_relative_to(root):raise ValueError('EXPLICIT_HOSTED_DEPENDENCY_SITE_REQUIRED')
  raw=(root/'integration/four_owner/import_custody.py').read_bytes()
  if hashlib.sha256(raw).hexdigest()!=before['integration/four_owner/import_custody.py']:raise ValueError('RAW_IMPORT_CUSTODY_CHANGED')
  namespace={'__name__':'read_raw_import_custody','__file__':str(root/'integration/four_owner/import_custody.py')}
  exec(compile(raw,namespace['__file__'],'exec',dont_inherit=True),namespace)
  self.cache_api=namespace;self.cache_state=namespace['begin'](cache,(root,self.site,self.dependencies))
  sys.path.insert(0,str(root))
  from integration.four_owner.contracts import bind_heads
  from integration.source_guard import SourceFence
  from scripts.qualify_four_owner import require_source_origin
  manifest=json.loads((root/'integration/four_owner/cohort.json').read_bytes());self.heads=bind_heads(manifest,os.environ['EXPECTED_HEAD'])
  proof=json.loads((qualification/'evidence.json').read_bytes())
  if (proof.get('qualification')!='PASS_SCOPED' or proof.get('mode')!='sdk' or proof.get('suite')!='all' or proof.get('sources')!=self.heads or proof.get('release_status')!='NO_GO' or proof.get('execution_authority') is not False or proof.get('source_before')!=proof.get('source_after')):raise ValueError('QUALIFIED_FOUR_OWNER_SDK_PROOF_REQUIRED')
  paths={'unified_system':root,**{name:root.parent/'.source'/name for name in ('market_data','math','terminan')}}
  self.fences={name:SourceFence(path,self.heads[name],isolated_cache=cache) for name,path in paths.items()}
  self.sources_before={name:fence.check() for name,fence in self.fences.items()}
  self.require_source_origin=require_source_origin;self.manifest=manifest
  self.origins={name:require_source_origin(fence,manifest['sources'][name]['repository']) for name,fence in self.fences.items()}
  self.bindings=json.loads((qualification/'sdk-bindings.json').read_bytes());self.wheels=proof['sdk_wheels']
  self.source_bindings_before=verify_source_bindings(self.bindings,self.fences,self.heads,manifest['sources'])
  for owner in ('market_data','math','terminan'):
   if not pathlib.Path(self.wheels[owner]['file']).resolve().is_relative_to(qualification/'wheels'):raise ValueError('QUALIFIED_WHEEL_LOCATION_REQUIRED')
  sys.path[:0]=[str(self.site),str(root/'tests'),str(root/'tests/gateway_runtime'),str(self.dependencies)]
  for old in ('grid','strattester','meta_analyse','market_profile_math'):
   if importlib.util.find_spec(old) is not None:raise ValueError('RETIRED_AMBIENT_MODULE_AVAILABLE')
  self.installed_before=verify_installed(self.site,self.bindings,self.wheels)
  self.dependencies_before=dependency_snapshot(self.dependencies)
  self.probe=namespace['controlled_probe'](qualification/'read-bytecode-control',self.cache_state)
  self.module_check()
 def module_check(self):
  records={}
  for name,module in tuple(sys.modules.items()):
   file=getattr(module,'__file__',None);top=name.split('.')[0]
   if file is None:
    if hasattr(module,'__path__') and any(pathlib.Path(p).resolve().is_relative_to(self.site) or pathlib.Path(p).resolve().is_relative_to(self.dependencies) for p in module.__path__):raise ValueError('UNBOUND_IMPORTED_SITE_NAMESPACE')
    if top in SDK_TOP:raise ValueError('SDK_NAMESPACE_ORIGIN_REJECTED')
    if top in ('unified_system','integration','scripts','storage') and (not hasattr(module,'__path__') or any(not pathlib.Path(p).resolve().is_relative_to(self.root) for p in module.__path__)):raise ValueError('ROOT_NAMESPACE_ORIGIN_REJECTED')
    continue
   path=pathlib.Path(file).resolve()
   if path.is_relative_to(self.site):
    relative=path.relative_to(self.site).as_posix()
    if relative not in self.bindings or top not in SDK_TOP:raise ValueError('UNBOUND_IMPORTED_SDK_SITE_MODULE')
   if path.is_relative_to(self.dependencies) and (str(path) not in self.dependencies_before or hashlib.sha256(path.read_bytes()).hexdigest()!=self.dependencies_before[str(path)]):raise ValueError('UNBOUND_IMPORTED_DEPENDENCY_SITE_MODULE')
   sdk=top in SDK_TOP;owned=path.is_relative_to(self.root)
   if (top in ('unified_system','integration','scripts','storage') or name.startswith('test_')) and not owned:raise ValueError('READ_ROOT_TEST_MODULE_ORIGIN_CHANGED')
   if sdk or owned:
    spec=getattr(module,'__spec__',None)
    # __main__ is the directly executed, prechecked tracked harness.
    if name=='__main__':self.fences['unified_system'].file(path,python=True);continue
    if path.suffix!='.py' or spec is None or type(spec.loader) is not importlib.machinery.SourceFileLoader or getattr(module,'__loader__',None) is not spec.loader or pathlib.Path(spec.origin).resolve()!=path or pathlib.Path(spec.loader.path).resolve()!=path:raise ValueError('READ_APPLICATION_SOURCE_LOADER_REQUIRED')
    cached=getattr(module,'__cached__',None);expected=pathlib.Path(importlib.util.cache_from_source(str(path))).absolute()
    if cached is None or pathlib.Path(cached).absolute()!=expected or pathlib.Path(spec.cached).absolute()!=expected or not expected.is_relative_to(self.cache_state[0]):raise ValueError('READ_APPLICATION_CACHE_ORIGIN_CHANGED')
    if sdk:
     relative=path.relative_to(self.site).as_posix()
     if relative not in self.bindings or hashlib.sha256(path.read_bytes()).hexdigest()!=self.bindings[relative]['sha256']:raise ValueError('READ_SDK_MODULE_ORIGIN_CHANGED')
    else:self.fences['unified_system'].module(module)
    records[name]=str(path)
   if top in ('cryptography','cffi','pycparser','_cffi_backend'):
    if str(path) not in self.dependencies_before or hashlib.sha256(path.read_bytes()).hexdigest()!=self.dependencies_before[str(path)]:raise ValueError('READ_DEPENDENCY_MODULE_ORIGIN_CHANGED')
  self.cache_api['verify_loaded'](self.cache_state,self.root,self.site)
  return records
 def finish(self):
  # Attempt every postcheck even if a module/SDK/dependency check already failed.
  errors=[];modules={};installed=None;after={};origins={}
  def attempt(label,action):
   try:return action()
   except BaseException as exc:errors.append({'check':label,'error_type':type(exc).__name__});return None
  source_bindings=attempt('sdk_source_bindings',lambda:verify_source_bindings(self.bindings,self.fences,self.heads,self.manifest['sources']))
  if source_bindings!=self.source_bindings_before:errors.append({'check':'sdk_source_roster','error_type':'CHANGED'})
  modules=attempt('module_origins',self.module_check)
  installed=attempt('installed_bytes',lambda:verify_installed(self.site,self.bindings,self.wheels))
  if installed!=self.installed_before:errors.append({'check':'installed_snapshot','error_type':'CHANGED'})
  dependencies=attempt('dependency_bytes',lambda:dependency_snapshot(self.dependencies))
  if dependencies!=self.dependencies_before:errors.append({'check':'dependency_snapshot','error_type':'CHANGED'})
  for name,fence in self.fences.items():
   after[name]=attempt('source_'+name,fence.finish)
   origins[name]=attempt('source_origin_'+name,lambda name=name,fence=fence:self.require_source_origin(fence,self.manifest['sources'][name]['repository']))
  root_after=attempt('raw_root_inventory',lambda:self.guard['inventory'](self.root))
  if origins!=self.origins or after!=self.sources_before or root_after!=self.root_before:errors.append({'check':'source_snapshot','error_type':'CHANGED'})
  attempt('empty_fresh_cache',lambda:self.cache_api['empty'](self.cache_state))
  self.post_report={'sources':self.heads,'installed':installed,'module_origins':modules,'dependency_files':len(self.dependencies_before),'bytecode_control':self.probe,'sources_pre_post':'MATCHED' if not errors else 'FAILED','post_errors':errors,'native_admission':False}
  if errors:raise ValueError('READ_SDK_OR_SOURCE_POSTCHECK_FAILED')
  return self.post_report
