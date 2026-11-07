"""Explicit Windows-only disposable native primitive qualification, not a login service."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def run(output):
    root=Path(__file__).resolve().parents[2]
    script=root/'scripts/Test-LocalPipeIdentity.ps1'
    if not script.is_file():raise RuntimeError('NATIVE_PIPE_FIXTURE_MISSING')
    if sys.platform!='win32':raise RuntimeError('WINDOWS_NATIVE_REQUIRED_NO_PASS')
    powershell=Path('C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe')
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    before=hashlib.sha256(script.read_bytes()).hexdigest();cases=[]
    for name,options,expected in [('identification',[],0),('wrong-pid',['-WrongPid'],2),
                                  ('anonymous',['-ClientLevel','Anonymous'],2),
                                  ('impersonation',['-ClientLevel','Impersonation'],2)]:
        result=subprocess.run([str(powershell),'-NoLogo','-NoProfile','-NonInteractive',
            '-File',str(script),*options],stdin=subprocess.DEVNULL,capture_output=True,timeout=30)
        (output/(name+'.stdout.log')).write_bytes(result.stdout)
        (output/(name+'.stderr.log')).write_bytes(result.stderr)
        if result.returncode!=expected:raise RuntimeError(f'NATIVE_CASE_REJECTED:{name}:{result.returncode}')
        value=json.loads(result.stdout.decode('utf-8-sig'))
        assert value['restored_server_identity'], 'server identity must be checked after every outcome'
        if expected==0:
            assert value['status']=='OBSERVED_NATIVE_IDENTIFICATION_ONLY'
            assert value['impersonation_level']==1 and value['restored_server_identity']
            assert value['client_pid_matches_owned_child'] and not value['runtime_admission']
            assert not value['observer_is_administrator']
        else:
            assert value['status']=='REJECTED' and value['owned_child_stopped']
            assert value['reason'] in ('CLIENT_PID_MISMATCH','IDENTIFICATION_LEVEL_REQUIRED')
            if name=='wrong-pid':
                assert value['kernel_client_pid']!=value['expected_client_pid']
        if name!='wrong-pid':
            assert value['kernel_client_pid']==value['expected_client_pid']
        cases.append({'case':name,'exit':result.returncode,'result':value,
            'stdout_sha256':hashlib.sha256(result.stdout).hexdigest(),
            'stderr_sha256':hashlib.sha256(result.stderr).hexdigest()})
    assert before==hashlib.sha256(script.read_bytes()).hexdigest()
    receipt={'schema':'unified.windows-pipe-identification.qualification.v1',
        'scope':'LOCAL_OWNED_SAME_ACCOUNT_PRIMITIVE_NOT_CROSS_ACCOUNT_OR_RUNTIME',
        'script_raw_sha256':before,'cases':cases,'tests':4,'skipped':0,
        'native_operator_bridge':'NOT_IMPLEMENTED','runtime_admission':False,
        'physical_installation':False}
    (output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'tests':4,'skipped':0,'runtime_admission':False}))


if __name__=='__main__':run(sys.argv[1])
