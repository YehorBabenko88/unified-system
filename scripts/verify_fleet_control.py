"""Exact checkout identity and disposable-only test receipt for hosted CI."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import unittest

def main():
    suite=unittest.defaultTestLoader.discover('tests',pattern='test_fleet_control.py')
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    git=lambda *args: subprocess.check_output(['git',*args],text=True).strip()
    evidence={'head':git('rev-parse','HEAD'),'tree':git('rev-parse','HEAD^{tree}'),
              'run_id':os.getenv('GITHUB_RUN_ID'),'run_attempt':os.getenv('GITHUB_RUN_ATTEMPT'),
              'job':os.getenv('GITHUB_JOB'),'runner_os':os.getenv('RUNNER_OS'),
              'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
              'software':'PASS' if result.wasSuccessful() else 'FAIL','source_provenance':'NOT_EVALUATED',
              'physical':'NOT_RUN','production':'NO_GO','execution_authorized':False}
    out=Path('fleet-evidence');out.mkdir(exist_ok=True)
    data=(json.dumps(evidence,indent=2,sort_keys=True)+'\n').encode()
    (out/'receipt.json').write_bytes(data)
    (out/'receipt.sha256').write_text(hashlib.sha256(data).hexdigest()+'  receipt.json\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
if __name__=='__main__':main()
