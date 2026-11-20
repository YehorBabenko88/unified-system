"""Four exact owner sources and raw-built installed SDKs; never full E2E/native.

This orchestrator invokes Git/build/Python/Node ONLY on reviewed hosted runners.
Local acceptance executes the separate strict inert run_installed path directly.
"""
import argparse,hashlib,json,os,pathlib,re,shutil,subprocess,sys,tempfile,tomllib,venv,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]

def call(command,**kwargs):return subprocess.run([str(x) for x in command],check=True,timeout=180,**kwargs)

def require_external_output(output,roots):
 if any(output.resolve().is_relative_to(path.resolve()) for path in roots):raise ValueError('OUTPUT_INSIDE_SOURCE_REJECTED')

def require_source_origin(fence,repository):
 origin=fence.git('remote','get-url','origin').decode().strip()
 if origin not in ('https://github.com/'+repository,'https://github.com/'+repository+'.git','git@github.com:'+repository+'.git'):raise ValueError('SOURCE_REPOSITORY_ORIGIN_REJECTED')
 return origin

def main(argv=None,*,suite='all',cohort_file='integration/four_owner/cohort.json',runner_file='integration/four_owner/run_installed.py'):
 parser=argparse.ArgumentParser(description=__doc__)
 for name in ('root-head','market-data','math','terminan','out'):parser.add_argument('--'+name,required=True)
 parser.add_argument('--mode',choices=('sdk','scientific-runtime'),default='sdk')
 args=parser.parse_args(argv)
 if not (sys.flags.isolated and sys.dont_write_bytecode):raise ValueError('ISOLATED_NO_BYTECODE_REQUIRED')
 if os.environ.get('GITHUB_ACTIONS')!='true' or os.environ.get('RUNNER_ENVIRONMENT')!='github-hosted':raise ValueError('HOSTED_SOURCE_QUALIFICATION_ONLY')
 paths={'unified_system':ROOT,'market_data':pathlib.Path(args.market_data).absolute(),'math':pathlib.Path(args.math).absolute(),'terminan':pathlib.Path(args.terminan).absolute()}
 out=pathlib.Path(args.out).absolute()
 require_external_output(out,paths.values())
 if out.exists() or any(out.resolve().is_relative_to(p.resolve()) for p in paths.values()) or len({p.resolve() for p in paths.values()})!=4:raise ValueError('FRESH_EXTERNAL_COHORT_OUTPUT_REQUIRED')
 out.mkdir();cache=out/'cache';sys.pycache_prefix=str(cache);sys.path.insert(0,str(ROOT))
 from integration.four_owner.contracts import bind_heads
 from integration.source_guard import SourceFence
 cohort_path=ROOT/cohort_file;runner_path=ROOT/runner_file
 if not cohort_path.resolve().is_relative_to(ROOT) or not runner_path.resolve().is_relative_to(ROOT):raise ValueError('QUALIFICATION_INPUT_OUTSIDE_ROOT')
 manifest=json.loads(cohort_path.read_bytes());heads=bind_heads(manifest,args.root_head)
 report=dict(schema='unified.four-owner.source-qualification.v1',qualification='FAIL_INCOMPLETE',release_status='NO_GO',mode=args.mode,suite=suite,sources=heads,scope='SYNTHETIC_SOURCE_CONSISTENCY_ONLY',source_authenticity='NOT_EVALUATED',point_in_time_availability='UNKNOWN',native_installation='NOT_RUN',physical='NOT_RUN',production='NO_GO',execution_authority=False,trading_authorized=False)
 fences={}
 try:
  fences={name:SourceFence(path,heads[name],isolated_cache=cache) for name,path in paths.items()}
  before={name:fence.check() for name,fence in fences.items()};report['source_before']=before
  for module in (sys.modules['integration.source_guard'],sys.modules['integration.four_owner.contracts']):fences['unified_system'].module(module)
  fences['unified_system'].file(__file__,python=True);fences['unified_system'].file(cohort_path);fences['unified_system'].file(runner_path,python=True)
  if manifest.get('enforce_repository_origins') is True:report['source_origins_before']={name:require_source_origin(fence,manifest['sources'][name]['repository']) for name,fence in fences.items()}
  if args.mode=='scientific-runtime':
   config=manifest['scientific_runtime'];test=paths['math']/config['test'];fences['math'].file(test)
   node=shutil.which('node')
   if not node:raise ValueError('PINNED_NODE_RUNTIME_REQUIRED')
   result=subprocess.run([node,'--test','--test-reporter=tap',str(test)],cwd=paths['math'],capture_output=True,text=True,timeout=90)
   (out/'scientific-runtime.log').write_text(result.stdout+result.stderr,encoding='utf8')
   counts={key:int(value) for key,value in re.findall(r'^# (tests|pass|fail|cancelled|skipped|todo) (\d+)$',result.stdout,re.M)}
   names=re.findall(r'^# Subtest: (.+)$',result.stdout,re.M)
   if result.returncode or counts!={'tests':6,'pass':6,'fail':0,'cancelled':0,'skipped':0,'todo':0} or sorted(names)!=sorted(config['case_ids']):raise ValueError('EXACT_SCIENTIFIC_RUNTIME_CASES_FAILED')
   report.update(qualification='PASS_SCOPED',scope=config['scope'],scientific_counts=counts,scientific_case_ids=names)
  else:
   builder=out/'builder';venv.EnvBuilder(with_pip=True).create(builder);rel='Scripts/python.exe' if os.name=='nt' else 'bin/python';build_python=builder/rel
   call([build_python,'-m','pip','install','--no-deps','--only-binary=:all:','setuptools=='+manifest['builders']['setuptools'],'wheel=='+manifest['builders']['wheel']])
   wheels=out/'wheels';wheels.mkdir();bindings={};built={}
   for owner in ('market_data','math','terminan'):
    spec=manifest['sources'][owner];fence=fences[owner];source=out/'build-source'/owner
    selected=[name for name in fence.files if any(name==prefix or prefix.endswith('/') and name.startswith(prefix) for prefix in spec['build_members'])]
    for name in selected:
     target=source/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(fence.blobs[fence.files[name]])
    package=tomllib.loads((source/'pyproject.toml').read_text(encoding='utf8'))
    if package['build-system']['build-backend']!='setuptools.build_meta' or 'backend-path' in package['build-system'] or package['project']['name']!=spec['distribution'] or package['project']['version']!=spec['metadata_version'] or package['project'].get('dynamic'):raise ValueError('STATIC_REVIEWED_SDK_BACKEND_REQUIRED')
    call([build_python,'-m','pip','wheel','--no-index','--no-deps','--no-build-isolation','--wheel-dir',wheels,source],env={**os.environ,'SOURCE_DATE_EPOCH':'315532800'})
    files=list(wheels.glob(spec['distribution'].replace('-','_')+'-*.whl'))
    if len(files)!=1:raise ValueError('ONE_CANONICAL_WHEEL_REQUIRED')
    wheel=files[0];entries=[]
    with zipfile.ZipFile(wheel) as archive:
     for name in archive.namelist():
      if name.endswith('/') or '.dist-info/' in name:continue
      if (owner=='math' and name not in ('market_math.py','market_compute_api.py','history_statistics.py') or owner!='math' and not name.startswith(spec['package']+'/')):raise ValueError('SDK_NAMESPACE_OWNER_MISMATCH')
      source_name='python/'+name if owner=='math' else name
      if source_name not in fence.files or archive.read(name)!=fence.blobs[fence.files[source_name]]:raise ValueError('WHEEL_NOT_EXACT_COMMITTED_SOURCE')
      if name in bindings:raise ValueError('DUPLICATE_SDK_MODULE_OWNER')
      if name.split('/')[0] in ('grid','strattester','meta_analyse') or name=='market_profile_math.py':raise ValueError('RETIRED_MODULE_IN_WHEEL')
      bindings[name]=dict(owner=owner,commit=heads[owner],source_path=source_name,sha256=hashlib.sha256(archive.read(name)).hexdigest());entries.append(name)
    built[owner]=dict(file=str(wheel),sha256=hashlib.sha256(wheel.read_bytes()).hexdigest(),raw_members=entries)
   root_bindings={name:record['raw_sha256'] for name,record in before['unified_system']['runtime_files'].items()}
   (out/'root-bindings.json').write_text(json.dumps(root_bindings,sort_keys=True),encoding='utf8')
   (out/'sdk-bindings.json').write_text(json.dumps(bindings,sort_keys=True,indent=2),encoding='utf8')
   installed=out/'installed';venv.EnvBuilder(with_pip=True).create(installed);python=installed/rel
   call([python,'-m','pip','install','--no-index','--no-deps',*[built[name]['file'] for name in ('market_data','math','terminan')]])
   site=subprocess.check_output([python,'-I','-B','-c','import sysconfig;print(sysconfig.get_paths()["purelib"])'],text=True).strip()
   child_cache=out/('causal-import-cache' if suite=='causal' else 'sdk-import-cache')
   command=[python,'-I','-S','-B','-X','pycache_prefix='+str(child_cache),runner_path,'--root',ROOT,'--site',site,'--bindings',out/'sdk-bindings.json','--root-bindings',out/'root-bindings.json','--out',out,'--suite',suite,'--cache',child_cache]
   with (out/'installed-tests.log').open('wb') as log:call(command,cwd=out,stdout=log,stderr=subprocess.STDOUT)
   proof=json.loads((out/'installed-tests.json').read_bytes())
   if proof['status']!='PASS_SCOPED':raise ValueError('INSTALLED_SDK_SCOPE_FAILED')
   report.update(qualification='PASS_SCOPED',sdk_wheels=built,installed_test_report=proof)
 except BaseException as exc:
  report['qualification']='FAIL';report['error_type']=type(exc).__name__
  raise
 finally:
  post={};post_errors=[]
  for name,fence in fences.items():
   if fence.before is not None:
    try:post[name]=fence.finish()
    except BaseException as exc:post_errors.append(dict(owner=name,error_type=type(exc).__name__))
  if manifest.get('enforce_repository_origins') is True and not post_errors:
   try:
    report['source_origins_after']={name:require_source_origin(fence,manifest['sources'][name]['repository']) for name,fence in fences.items()}
    if report['source_origins_after']!=report.get('source_origins_before'):post_errors.append(dict(owner='all',error_type='SOURCE_ORIGIN_CHANGED'))
   except BaseException as exc:post_errors.append(dict(owner='all',error_type=type(exc).__name__))
  report['source_after']=post
  if post_errors:report['qualification']='FAIL';report['source_post_errors']=post_errors
  (out/'evidence.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n',encoding='utf8')
  if post_errors:raise ValueError('SOURCE_POSTCHECK_FAILED')
 print(json.dumps(dict(qualification=report['qualification'],release_status='NO_GO',sources=heads,scope=report['scope'])))
 return 0
if __name__=='__main__':raise SystemExit(main())
