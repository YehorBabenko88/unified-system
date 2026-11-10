import pathlib,os,subprocess,time,json,hashlib,tempfile,shutil
root=pathlib.Path(__file__).resolve().parent.parent
packet=root/'outputs/f26-revised-oracle-source-20261110'
assert hashlib.sha256((packet/'f26-revised-oracle.py').read_bytes()).hexdigest()=='587e4625604bd39055485c753e81ab769078f37b16fc062489aa245b13699e5d'
assert hashlib.sha256((packet/'f26-fix-source-guard.py').read_bytes()).hexdigest()=='9d94d44c0d0351443ee234f1263dc715250414bc597041e91120c41c39417fcb'
output=pathlib.Path(tempfile.mkdtemp(prefix='f26-m-revised-once-',dir=root/'outputs'))
assert not list(output.iterdir()) and not (output/'f26-fix-M').exists()
source=root/'work/f26-m-revised-source-once'
assert not source.exists()
start=time.monotonic();deadline=start+90
owned=[]
def command(args,cwd,env=None):
    remaining=deadline-time.monotonic()
    if remaining<=0:raise RuntimeError('OUTER_FAMILY_DEADLINE')
    p=subprocess.Popen(args,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);owned.append(p)
    try:return finish(p,remaining)
    except subprocess.TimeoutExpired:
        subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5)
        p.communicate(timeout=5);raise RuntimeError('OUTER_FAMILY_DEADLINE')
def finish(p,remaining):
    data=p.communicate(timeout=remaining)[0];return p.returncode,data
status='PRECONDITION_FAILED';error=None;receipt=None
try:
    git='C:/Program Files/Git/cmd/git.exe'
    args=[git,'--no-replace-objects']
    rc,data=command(args+['clone','--no-hardlinks','--no-checkout','C:/Users/LS-5/.codex/worktrees/agent1-f26-cadence-source-20261110/gateway-runtime-recovery-20261107',str(source)],root)
    assert rc==0
    rc,data=command(args+['-c','core.autocrlf=false','checkout','--detach','ab9362706cd8cd75b2fc0f5177481a96a5f73ac4'],source);assert rc==0
    rc,data=command(args+['rev-parse','HEAD^{tree}'],source);assert rc==0 and data.strip()==b'cfa80d600603d947e79304e075d48787c116a8a1'
    assert not list(output.iterdir()) and not (output/'f26-fix-M').exists()
    remaining=deadline-time.monotonic();assert remaining>10
    env=dict(os.environ,RUNNER_TEMP=str(output),EXPECTED_HEAD='ab9362706cd8cd75b2fc0f5177481a96a5f73ac4',QUAL_CASE='M',CASE_SAFETY_SECONDS=str(min(84,remaining-3)))
    rc,data=command(['C:/Users/LS-5/AppData/Local/Python/pythoncore-3.12-64/python.exe','-I','-S','-B',str(packet/'f26-revised-oracle.py')],source,env)
    (output/'process.log').write_bytes(data)
    receipt=json.loads((output/'f26-fix-M/receipt.json').read_text(encoding='utf8'))
    phases=json.loads((output/'f26-fix-M/per-call-phases.json').read_text(encoding='utf8'))
    text=(output/'f26-fix-M/M-tests.log').read_text(encoding='utf8');o=receipt['outcomes'][0]
    checks=dict(one_test_one_failure_no_error_skip=o['tests']==1 and o['failures']==1 and o['errors']==0 and o['skips']==0,original_assertion='self.assertIs(renewed.get(timeout=3),True)' in text and 'AssertionError: False is not True' in text,mutation_invoked=receipt['mutant_invocations']>=1 and any(e['phase']=='MUTANT_INNER_FALSE' for e in phases['events']),zero_app_success=not any(e['phase']=='APP_CALL' and e['completed'] for e in phases['events']),no_dropped=phases['dropped']==0,source_unchanged=receipt['source_unchanged'],clean=not receipt['harness_error'] and not receipt['scope_violation'] and receipt['lane']=='RETIRED' and not receipt['retirement']['children_alive'] and not receipt['retirement']['threads_alive'] and rc==0)
    status='ORACLE_CAUSAL_REJECTION' if all(checks.values()) else 'ORACLE_INCONCLUSIVE'
except BaseException as exc:
    error=type(exc).__name__;checks={};status='ORACLE_INCONCLUSIVE' if receipt else 'PRECONDITION_OR_HARNESS_FAILURE'
finally:
    summary=dict(classification=status,checks=checks,error=error,head='ab9362706cd8cd75b2fc0f5177481a96a5f73ac4',tree='cfa80d600603d947e79304e075d48787c116a8a1',family_seconds=round(time.monotonic()-start,3),outer_owned_processes_alive=sum(p.poll() is None for p in owned),lane='RETIRED' if all(p.poll() is not None for p in owned) and (receipt is None or receipt['lane']=='RETIRED') else 'CLEANUP_FAILED',retry=0,push=False,historical_cause='NOT_ESTABLISHED')
    (output/'summary.json').write_bytes(json.dumps(summary,sort_keys=True,indent=2).encode('utf8'))
    for name in ('f26-revised-oracle.py','f26-fix-source-guard.py'):shutil.copyfile(packet/name,output/name)
    shutil.copyfile(pathlib.Path(__file__),output/'f26-revised-m-once.py')
    manifest={p.relative_to(output).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in output.rglob('*') if p.is_file()}
    (output/'SHA256.json').write_bytes(json.dumps(manifest,sort_keys=True,indent=2).encode('utf8'))
    print(json.dumps(dict(output=str(output),summary=summary,seal=hashlib.sha256((output/'SHA256.json').read_bytes()).hexdigest())),flush=True)
