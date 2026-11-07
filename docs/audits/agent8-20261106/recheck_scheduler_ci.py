"""Run the exact scheduler CI Python block locally and challenge its count/skip guards."""
import hashlib,json,os,pathlib,subprocess,sys
import yaml
ROOT=pathlib.Path(__file__).resolve().parents[1];source=ROOT/'work/review5-scheduler';out=ROOT/'outputs/phase5';sha='942e5f1d1efb28f97fb5eaae7a216424938dd738'
def git(*args):return subprocess.check_output(['git','-C',str(source),*args])
assert git('rev-parse','HEAD').decode().strip()==sha
changed=git('diff','--name-only','787c862568eb47177c21393338e743ec01b5f45f',sha).decode().splitlines();assert set(changed)=={'.github/workflows/agent5-components.yml','docs/scheduler/components.md'}
workflow=yaml.safe_load((source/'.github/workflows/agent5-components.yml').read_text());steps=workflow['jobs']['components-windows']['steps']
checkout=next(s for s in steps if s.get('uses','').startswith('actions/checkout'))
assert checkout['with']['ref']=='${{ github.event.pull_request.head.sha || github.sha }}' and checkout['with']['persist-credentials'] is False
run=next(s['run'] for s in steps if s.get('name')=='Run exact-source component acceptance')
lines=run.splitlines();assert lines[0]=="python - <<'PY'" and lines[-1]=='PY';code='\n'.join(lines[1:-1])
cases={
 'actual15':('',sha,0),
 'zero_tests':("import unittest\nunittest.defaultTestLoader.discover=lambda *a,**k:unittest.TestSuite()\n",sha,1),
 'fourteen_tests':("import unittest\nunittest.defaultTestLoader.discover=lambda *a,**k:unittest.TestSuite(unittest.FunctionTestCase(lambda:None) for _ in range(14))\n",sha,1),
 'fifteen_with_skip':("import unittest\ndef skip():raise unittest.SkipTest('AUDITOR_SYNTHETIC_SKIP')\nunittest.defaultTestLoader.discover=lambda *a,**k:unittest.TestSuite([unittest.FunctionTestCase(skip),*[unittest.FunctionTestCase(lambda:None) for _ in range(14)]])\n",sha,1),
 'wrong_expected_source':('', '0'*40,1)}
results={}
for name,(prelude,expected,exit_code) in cases.items():
    folder=out/('scheduler-ci-'+name);env={k:v for k,v in os.environ.items() if not k.startswith('GITHUB_')}
    env.update(EXPECTED_SOURCE_SHA=expected,EVIDENCE_DIR=str(folder),PYTHONDONTWRITEBYTECODE='1')
    wrapper="import sys,os;sys.path.insert(0,os.getcwd());\n"+prelude+code
    p=subprocess.run([sys.executable,'-I','-B','-c',wrapper],cwd=source,env=env,capture_output=True,timeout=30)
    folder.mkdir(parents=True,exist_ok=True);(folder/'runner.stdout.log').write_bytes(p.stdout);(folder/'runner.stderr.log').write_bytes(p.stderr)
    receipt=json.loads((folder/'receipt.json').read_text());assert receipt['execution']=='LOCAL'
    assert p.returncode==exit_code and receipt['passed']==(exit_code==0),(name,p.returncode,receipt)
    assert hashlib.sha256((folder/'component-tests.log').read_bytes()).hexdigest()==receipt['test_log_sha256']
    results[name]={'exit_code':p.returncode,'passed':receipt['passed'],'tests_run':receipt['tests_run'],'skips':receipt['skips']}
summary={'head':sha,'tree':git('rev-parse','HEAD^{tree}').decode().strip(),'delta_only_workflow_and_docs':changed,'exact_pr_head_checkout':'VERIFIED','local_real_suite_and_negative_guards':results,'source_guard_scope':'HEAD_TREE_TRACKED_STATUS_ONLY_NOT_RAW_BYTE_ATTESTATION','workflow_code_sha256':hashlib.sha256(code.encode()).hexdigest(),'Windows_CI':'QUEUED_NOT_QUALIFIED','global_acceptance':'NO-GO'}
(out/'scheduler-ci-fix-review.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
