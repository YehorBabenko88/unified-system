"""Independently execute exact PR25 CI block with clean and hostile owned fixtures."""
import hashlib,json,os,pathlib,subprocess,sys,uuid
import yaml
ROOT=pathlib.Path(__file__).resolve().parents[1];original=ROOT/'work/review2-api';out=ROOT/'outputs/phase9';sha='0b3af3e872b49ed1848815f7f9ffd42444f89b24';base='320b5d0894019d72aa8927dc5c4246d28c6e5f3c'
def git(*args):return subprocess.check_output(['git','-C',str(original),*args])
assert git('rev-parse','HEAD').decode().strip()==sha
assert git('rev-parse','HEAD^{tree}').decode().strip()=='1769906483356ed41eb8fcd278c5545b1bbafa67'
assert set(git('diff','--name-only',base,sha).decode().splitlines())=={'.github/workflows/agent2-control-api.yml','docs/architecture/control-api-readonly.md'}
for path in ['unified_system/control_api_readonly.py','tests/test_control_api_readonly.py']:
    assert git('rev-parse',base+':'+path)==git('rev-parse',sha+':'+path)
workflow=yaml.safe_load((original/'.github/workflows/agent2-control-api.yml').read_text());steps=workflow['jobs']['boundary']['steps'];code=next(s['run'] for s in steps if s.get('name','').startswith('Denial and unavailable'))
discover_patch='''
import unittest,pathlib,subprocess
_discover=unittest.defaultTestLoader.discover
def _flat(value):
 for item in value:
  if isinstance(item,unittest.TestSuite):yield from _flat(item)
  else:yield item
def _wrapped(*args,**kwargs):
 suite=_discover(*args,**kwargs);items=list(_flat(suite))
 __INJECTION__
 return suite
unittest.defaultTestLoader.discover=_wrapped
'''
cases={
 'clean':{},'tracked_comment':{'comment':True},'hidden_tracked_comment':{'comment':True,'assume':True},
 'wrong_expected_head':{'expected':'0'*40},
 'missing_id':{'inject':'return unittest.TestSuite(items[:-1])'},
 'duplicate_id':{'inject':'return unittest.TestSuite(items[:-1]+[items[0]])'},
 'skip':{'inject':"getattr(items[0],items[0]._testMethodName).__func__.__unittest_skip__=True"},
 'post_test_tamper':{'inject':"items[0].addCleanup(lambda:pathlib.Path('unified_system/control_api_readonly.py').write_bytes(pathlib.Path('unified_system/control_api_readonly.py').read_bytes()+b'\\n# auditor post-test tamper\\n'))"},
 'hidden_post_test_tamper':{'inject':"items[0].addCleanup(lambda:(pathlib.Path('unified_system/control_api_readonly.py').write_bytes(pathlib.Path('unified_system/control_api_readonly.py').read_bytes()+b'\\n# auditor post-test hidden tamper\\n'),subprocess.check_call(['git','update-index','--assume-unchanged','unified_system/control_api_readonly.py'])))"},
}
results={}
for name,options in cases.items():
    source=ROOT/'work'/('f11-guard-'+name+'-'+uuid.uuid4().hex[:10]);subprocess.run(['git','clone','--local','--no-checkout',str(original),str(source)],check=True,capture_output=True);subprocess.run(['git','-C',str(source),'-c','core.autocrlf=false','checkout','--detach',sha],check=True,capture_output=True)
    target=source/'unified_system/control_api_readonly.py'
    if options.get('comment'):target.write_bytes(target.read_bytes()+b'\n# auditor pre-test tracked source tamper\n')
    if options.get('assume'):subprocess.run(['git','-C',str(source),'update-index','--assume-unchanged','unified_system/control_api_readonly.py'],check=True)
    prelude=discover_patch.replace('__INJECTION__',options['inject']) if 'inject' in options else ''
    env={k:v for k,v in os.environ.items() if not k.startswith('GITHUB_')};env.update(EXPECTED_HEAD=options.get('expected',sha),GITHUB_RUN_ID='LOCAL_AUDITOR_NOT_GITHUB',GITHUB_RUN_ATTEMPT='LOCAL_ONLY',PYTHONDONTWRITEBYTECODE='1')
    run=subprocess.run([sys.executable,'-I','-B','-c','import sys,os;sys.path.insert(0,os.getcwd());\n'+prelude+code],cwd=source,env=env,capture_output=True,timeout=30)
    folder=out/name;folder.mkdir(parents=True,exist_ok=True);(folder/'stdout.log').write_bytes(run.stdout);(folder/'stderr.log').write_bytes(run.stderr)
    receipt_path=source/'p0-ci-evidence.json';receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else None
    if name=='clean':
        assert run.returncode==0 and receipt['source_binding_passed'] and receipt['tests']==16 and receipt['skipped']==receipt['errors']==receipt['failures']==0
        assert receipt['source_before']==receipt['source_after'] and len(receipt['source_before']['files'])==5
        assert len(receipt['mandatory_test_ids'])==len(set(receipt['mandatory_test_ids']))==16
        for pin in receipt['source_before']['files'].values():assert pin['raw_sha256']==pin['blob_sha256']
        log=(source/'p0-ci-tests.log').read_bytes();assert hashlib.sha256(log).hexdigest()==receipt['test_log_sha256'];(folder/'tests.log').write_bytes(log);(folder/'receipt.json').write_text(json.dumps(receipt,indent=2))
    else:assert run.returncode!=0,('NEGATIVE_ACCEPTED',name,receipt)
    reasons=[line for line in run.stderr.decode(errors='replace').splitlines() if 'AssertionError' in line]
    results[name]={'expected':'ACCEPT_LOCAL_16' if name=='clean' else 'REJECT','exit_code':run.returncode,'reason':reasons[-1:] or [],'receipt_emitted':receipt is not None}
report={'head':sha,'tree':'1769906483356ed41eb8fcd278c5545b1bbafa67','app_and_16_tests_unchanged':True,'cases':results,
 'scope':'LOCAL_EXECUTION_OF_EXACT_CI_BLOCK_WITH_AUDITOR_OWNED_NEGATIVE_FIXTURES',
 'workflow_code_sha256':hashlib.sha256(code.encode()).hexdigest(),'F11':'FIX_VERIFIED_OFFLINE_EXACT_SOURCE','hosted_CI':'NOT_QUALIFIED','runtime_API':'NOT_QUALIFIED','physical':'BLOCKED'}
(out/'f11-independent-guards.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
