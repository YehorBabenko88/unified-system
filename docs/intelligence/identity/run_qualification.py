"""Exact raw tracked source pre/post and mandatory isolated identity tests."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

parser = argparse.ArgumentParser()
parser.add_argument('--expected-head', required=True)
args = parser.parse_args()
assert sys.flags.isolated and sys.dont_write_bytecode
root = Path(__file__).resolve().parents[3]
def git(*arguments):
    return subprocess.check_output(['git','--no-replace-objects','-C',str(root),*arguments])
assert git('rev-parse','HEAD').decode().strip() == args.expected_head
def inventory():
    result = {}
    process = subprocess.Popen(['git','--no-replace-objects','-C',str(root),'cat-file','--batch'],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    try:
        for row in git('ls-tree','-rz','--full-tree','HEAD').split(b'\0'):
            if not row: continue
            meta, name = row.split(b'\t',1)
            mode, kind, oid = meta.split()
            assert kind == b'blob' and mode in (b'100644',b'100755')
            path = root / name.decode('utf-8')
            assert not path.is_symlink() and path.resolve().is_relative_to(root)
            process.stdin.write(oid+b'\n'); process.stdin.flush()
            header = process.stdout.readline().split()
            assert header[0] == oid and header[1] == b'blob'
            raw = process.stdout.read(int(header[2])); assert process.stdout.read(1)==b'\n'
            assert path.read_bytes() == raw, name
            result[name.decode()] = hashlib.sha256(raw).hexdigest()
    finally:
        process.stdin.close(); process.wait(timeout=15); process.stdout.close()
    assert process.returncode == 0
    return result
before = inventory()
sys.path.insert(0,str(root))
suite = unittest.defaultTestLoader.discover(str(root/'tests'),pattern='test_gateway_identity.py')
assert suite.countTestCases()==22
result = unittest.TextTestRunner(verbosity=2).run(suite)
after = inventory()
assert before==after and result.testsRun==22 and not result.skipped
assert result.wasSuccessful()
print(json.dumps(dict(result='PASS',head=args.expected_head,tests=22,skips=0,
                      raw_files_before_after=len(before),scope='DISPOSABLE_MTLS_AND_LOCAL_READ_CAPABILITY_ONLY',
                      cross_owner_read='NOT_RUN',nativeauthentication=False)))
