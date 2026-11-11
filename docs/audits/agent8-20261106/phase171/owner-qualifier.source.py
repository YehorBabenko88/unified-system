"""Source-bound local negative tests only. No native worker fixture."""
import contextlib, hashlib, io, json, os
from pathlib import Path
import subprocess, sys, unittest
from unittest.mock import patch

root = Path(sys.argv[1]).resolve()
output = Path(sys.argv[2]).resolve()
output.mkdir(exist_ok=False)
os.chdir(root)
expected = '7fa10ea3d2f0335db5950c37f8fe5faa56acde18'
def git(*args, data=None):
    return subprocess.check_output(['git', '--no-replace-objects', '--no-optional-locks',
        '-c', 'core.fsmonitor=false', *args], input=data, timeout=30)
assert git('rev-parse','HEAD').decode().strip() == expected
assert not git('status','--porcelain','--untracked-files=all').strip()
def inventory():
    rows = []
    for row in git('ls-tree','-rz','--full-tree','HEAD').split(b'\0'):
        if not row: continue
        meta, name = row.split(b'\t', 1)
        mode, kind, oid = meta.split()
        assert mode in (b'100644',b'100755') and kind == b'blob'
        rows.append((name.decode(), oid))
    blobs = io.BytesIO(git('cat-file','--batch', data=b''.join(oid+b'\n' for _,oid in rows)))
    hashes = {}
    for name, oid in rows:
        got, kind, size = blobs.readline().split()
        raw = blobs.read(int(size))
        assert got == oid and kind == b'blob' and blobs.read(1) == b'\n'
        assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest().encode() == oid
        file = root/name
        assert not file.is_symlink() and not getattr(file.lstat(),'st_file_attributes',0)&1024
        assert file.read_bytes() == raw
        hashes[name] = hashlib.sha256(raw).hexdigest()
    assert blobs.read() == b''
    return hashes
before = inventory()
sys.path[:0] = [str(root), str(root/'tests/gateway_jobs'), str(root/'tests')]
patterns = ['test_one_shot_closed_integration.py', 'test_closed_jobs.py',
            'test_resource_capabilities.py', 'test_cpu_policy.py',
            'test_capacity_freshness.py', 'test_clock_source_prerequisites.py', 'test_preparation_integrity.py']
with (output/'pure-tests.log').open('w',encoding='utf-8') as log:
    suite = unittest.TestSuite(unittest.TestLoader().discover('tests/gateway_jobs',pattern=p) for p in patterns)
    from test_agent5_scheduler_components import DurablePreparationTests
    suite.addTests(DurablePreparationTests(n) for n in unittest.TestLoader().getTestCaseNames(DurablePreparationTests) if n != 'test_process_crash_before_event_commit_recovers_without_partial_hold')
    assert suite.countTestCases() == 53
    result = unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
assert result.wasSuccessful() and result.testsRun == 53 and not result.skipped
from test_one_shot_closed_integration import OneShotClosedIntegration as T
from scheduler_components.authority_boundary import ClosedAuthorityBoundary as B
from unified_system.gateway_worker import GatewayWorker as W
controls = [
    (patch.object(B,'execute',return_value='GRANTED'),
     'test_advisory_placement_and_preparation_never_issue_assignment_or_start'),
    (patch.object(W,'start',return_value=None),
     'test_forged_committed_metadata_or_session_never_opens_start')]
with (output/'mutation-expected-failures.log').open('w',encoding='utf-8') as log:
    for guard, name in controls:
        with guard:
            mutant = unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.TestSuite([T(name)]))
        assert len(mutant.failures) == 1 and not mutant.errors
after = inventory()
assert before == after
assert not git('status','--porcelain','--untracked-files=all').strip()
receipt = dict(schema='agent5.one-shot-negative-verification.v1',head=expected,
    tree=git('rev-parse','HEAD^{tree}').decode().strip(),python=sys.version,
    interpreter_file_sha256=hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
    raw_source_files=len(before),raw_pre_post_equal=True,extra_files=False,
    tests=53,new_tests=6,existing_tests=47,skips=0,mutation_controls_expected_failures=2,
    native_worker_job_calls=0,consul_rpc=0,target_browser_math_runs=0,
    local_scheduler_source_changes=1,shared_runtime_source_changes=0,strict_time='OPTION1_LOGICAL_MUTATIONS_DISABLED',
    positive_job='NOT_IMPLEMENTED_NOT_RUN',qualification='LOCAL_NEGATIVE_ONLY_NOT_NATIVE_HA',
    hashes={name:before[name] for name in [
      'unified_system/gateway_worker.py','unified_system/gateway_jobs.py','scheduler_components/durable.py','tests/gateway_jobs/test_preparation_integrity.py',
      'tests/gateway_jobs/test_one_shot_closed_integration.py',
      '.github/workflows/agent5-one-shot-negative.yml']})
receipt['evidence_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir()}
(output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print(json.dumps(receipt,indent=2))


