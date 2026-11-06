import json,os,pathlib,subprocess,sys,uuid
import yaml
ROOT=pathlib.Path(__file__).resolve().parents[1];original=ROOT/'work/review2-api';source=ROOT/'work'/('review2-ci-negative-'+uuid.uuid4().hex);sha='320b5d0894019d72aa8927dc5c4246d28c6e5f3c';out=ROOT/'outputs/phase8'
subprocess.run(['git','clone','--local','--no-checkout',str(original),str(source)],check=True,capture_output=True)
subprocess.run(['git','-C',str(source),'-c','core.autocrlf=false','checkout','--detach',sha],check=True,capture_output=True)
workflow=yaml.safe_load((source/'.github/workflows/agent2-control-api.yml').read_text());steps=workflow['jobs']['boundary']['steps'];code=next(s['run'] for s in steps if s.get('name','').startswith('Denial and unavailable'))
target=source/'unified_system/control_api_readonly.py';before=target.read_bytes();target.write_bytes(before+b'\n# Auditor-owned uncommitted source tamper negative fixture.\n')
env={k:v for k,v in os.environ.items() if not k.startswith('GITHUB_')};env.update(EXPECTED_HEAD=sha,GITHUB_RUN_ID='LOCAL_AUDITOR_NOT_GITHUB',GITHUB_RUN_ATTEMPT='LOCAL_ONLY',PYTHONDONTWRITEBYTECODE='1')
dirty_before=subprocess.check_output(['git','-C',str(source),'status','--porcelain','--untracked-files=no'],text=True)
try:
    p=subprocess.run([sys.executable,'-I','-B','-c','import sys,os;sys.path.insert(0,os.getcwd());\n'+code],cwd=source,env=env,capture_output=True,timeout=30)
    (out/'ci-tamper.stdout.log').write_bytes(p.stdout);(out/'ci-tamper.stderr.log').write_bytes(p.stderr)
    receipt=json.loads((source/'p0-ci-evidence.json').read_text())
    result={'head':sha,'scope':'LOCAL_AUDITOR_WORKTREE_TAMPER_NEGATIVE_ONLY','tracked_dirty_before':dirty_before,
      'expected_gate':'REJECT_BEFORE_TESTS_OR_NONZERO_EXIT','actual_exit':p.returncode,'actual_receipt':receipt,
      'git_committed_blob_sha256':__import__('hashlib').sha256(before).hexdigest(),
      'executed_dirty_file_sha256':__import__('hashlib').sha256(target.read_bytes()).hexdigest(),
      'finding':'UNCOMMITTED_TRACKED_SOURCE_ACCEPTED_BY_CI_HEAD_ONLY_GUARD' if p.returncode==0 else 'REJECTED'}
    (out/'ci-source-tamper-probe.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
finally:target.write_bytes(before)
