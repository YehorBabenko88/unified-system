import hashlib,json,subprocess,time
from pathlib import Path
base=Path('C:/Users/LS-5/.codex/native-e2e-evidence-20261109');activation=base/'ls5-package453-c.activation-plan.json';raw=activation.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='5cef428e7284d66ee3fc94b95dde31f91f8eb7533bb666d0f33666b937701369'
record=json.loads(raw);assert record['manifest_sha256']=='2ffadb31cc16dd4044d6fb1455c976f0988e4e0c565a1d0d5c6201cf28355ed7'
assert not Path(record['state_path']).exists()
started=time.monotonic();status='UNKNOWN';code=None
try:
 with (base/'ls5-smoke453-c-controller.stdout.log').open('xb') as stdout,(base/'ls5-smoke453-c-controller.stderr.log').open('xb') as stderr:
  result=subprocess.run(record['argv'],cwd=base/'ls5-source-qualified-453cb6d',stdout=stdout,stderr=stderr,shell=False,timeout=300)
 code=result.returncode;status='CONTROLLER_EXIT_ZERO' if code==0 else 'CONTROLLER_EXIT_NONZERO'
finally:
 receipt=dict(status=status,returncode=code,elapsed_seconds=time.monotonic()-started,activation_sha256=hashlib.sha256(raw).hexdigest(),source_head=record['source_head'],manifest_sha256=record['manifest_sha256'],scope='ROOT_OWNER_AUTHORIZED_LS5_DISPOSABLE_ONLY_NOT_FULL_ACCEPTANCE')
 (base/'ls5-smoke453-c-driver-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(receipt))
raise SystemExit(0 if code==0 else 1)
