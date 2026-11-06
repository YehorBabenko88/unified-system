"""Verify job Git configuration precedes checkout and retains strict raw-byte guards."""
import hashlib,json,os,pathlib,subprocess,sys,uuid
import yaml
ROOT=pathlib.Path(__file__).resolve().parents[1];original=ROOT/'work/review2-api';out=ROOT/'outputs/phase9';sha='0b3af3e872b49ed1848815f7f9ffd42444f89b24'
workflow=yaml.safe_load((original/'.github/workflows/agent2-control-api.yml').read_text());job=workflow['jobs']['boundary'];code=next(s['run'] for s in job['steps'] if s.get('name','').startswith('Denial and unavailable'))
config={k:str(v) for k,v in job['env'].items() if k.startswith('GIT_CONFIG_')};assert config['GIT_CONFIG_COUNT']=='2' and config['GIT_CONFIG_VALUE_0']=='false' and config['GIT_CONFIG_VALUE_1']=='lf'
results={}
for name,configure_before in [('inherited_crlf_then_guard',False),('job_config_before_checkout',True)]:
    source=ROOT/'work'/('f11-checkout-'+uuid.uuid4().hex[:10]);subprocess.run(['git','clone','--local','--no-checkout',str(original),str(source)],check=True,capture_output=True)
    subprocess.run(['git','-C',str(source),'config','core.autocrlf','true'],check=True);subprocess.run(['git','-C',str(source),'config','core.eol','crlf'],check=True)
    env={k:v for k,v in os.environ.items() if not k.startswith(('GITHUB_','GIT_CONFIG_'))}
    checkout_env=dict(env,**config) if configure_before else env
    subprocess.run(['git','-C',str(source),'checkout','--detach',sha],env=checkout_env,check=True,capture_output=True)
    raw=(source/'unified_system/__init__.py').read_bytes();blob=subprocess.check_output(['git','-C',str(source),'show',sha+':unified_system/__init__.py'])
    env.update(config);env.update(EXPECTED_HEAD=sha,GITHUB_RUN_ID='LOCAL_CHECKOUT_NEGATIVE_NOT_GITHUB',GITHUB_RUN_ATTEMPT='LOCAL_ONLY',PYTHONDONTWRITEBYTECODE='1')
    p=subprocess.run([sys.executable,'-I','-B','-c','import sys,os;sys.path.insert(0,os.getcwd());\n'+code],cwd=source,env=env,capture_output=True,timeout=30)
    folder=out/name;folder.mkdir(parents=True,exist_ok=True);(folder/'stdout.log').write_bytes(p.stdout);(folder/'stderr.log').write_bytes(p.stderr)
    if configure_before:assert raw==blob and p.returncode==0
    else:assert raw!=blob and p.returncode!=0
    results[name]={'job_configuration_applied_before_checkout':configure_before,'raw_init_matches_git':raw==blob,'working_init_sha256':hashlib.sha256(raw).hexdigest(),'git_init_sha256':hashlib.sha256(blob).hexdigest(),'runner_exit':p.returncode}
report={'head':sha,'scope':'AUDITOR_OWNED_WINDOWS_CLONES_WITH_LOCAL_AUTOCRLF_TRUE','job_git_env':config,'cases':results,'shared_source_modified':False,'binding_weakened':False,'hosted_CI':'NOT_QUALIFIED','physical':'BLOCKED'}
(out/'checkout-conversion-review.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
