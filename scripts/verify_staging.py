"""Run only disposable staging checks and serialize exact-checkout receipts."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import unittest
from unified_system.staging import build_staging_plan

ROOT=Path(__file__).resolve().parents[1]
def main():
    git=lambda *args:subprocess.check_output(['git','-C',str(ROOT),*args],text=True).strip()
    head=git('rev-parse','HEAD');tree=git('rev-parse','HEAD^{tree}')
    if git('status','--porcelain'):
        raise SystemExit('clean source required')
    expected=os.getenv('STAGING_EXPECTED_HEAD',head)
    if head!=expected:
        raise SystemExit('source identity mismatch')
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern='test_staging.py'))
    ok=result.wasSuccessful() and result.testsRun==8 and not result.skipped and not result.expectedFailures and not result.unexpectedSuccesses
    source=json.loads((ROOT/'docs/windows-staging-sources.json').read_text())
    plan=build_staging_plan(source,[dict(id='logical-slot-'+str(i+1),modules=['unified','grid','strattester','terminan','math'],intent='PRESENT') for i in range(6)])
    out=ROOT/'staging-evidence';out.mkdir(exist_ok=True)
    specimen=(json.dumps(plan,sort_keys=True,indent=2)+'\n').encode();(out/'six-logical-slots.json').write_bytes(specimen)
    evidence=dict(schema='unified.staging-ci.v1',head=head,tree=tree,run_id=os.getenv('GITHUB_RUN_ID'),attempt=os.getenv('GITHUB_RUN_ATTEMPT'),job=os.getenv('GITHUB_JOB'),runner_os=os.getenv('RUNNER_OS'),python=os.getenv('STAGING_PYTHON'),tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),software='PASS' if ok else 'FAIL',source_provenance='NOT_EVALUATED',physical='NOT_RUN',production='NO_GO',admission='BLOCKED',execution_authorized=False,specimen_sha256=hashlib.sha256(specimen).hexdigest(),source_lock_sha256=plan['source_lock_sha256'])
    raw=(json.dumps(evidence,sort_keys=True,indent=2)+'\n').encode();(out/'receipt.json').write_bytes(raw)
    (out/'receipt.sha256').write_text(hashlib.sha256(raw).hexdigest()+'  receipt.json\n')
    raise SystemExit(0 if ok else 1)
if __name__=='__main__':main()
