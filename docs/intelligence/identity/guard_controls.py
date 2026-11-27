"""Exercise actual qualification helpers with owned negative source fixtures."""
import ast
import hashlib
import inspect
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import zlib

runner = Path(__file__).with_name('run_qualification.py')
raw = runner.read_bytes()
tree = ast.parse(raw, filename=str(runner))
selected = ast.Module(body=[item for item in tree.body if isinstance(item,
                       (ast.Import, ast.ImportFrom, ast.FunctionDef)) or
                       (isinstance(item,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('EXPECTED_TEST_NAMES','EXPECTED_STRICT_TEST_ID') for t in item.targets))], type_ignores=[])
namespace = {}
exec(compile(selected, str(runner), 'exec'), namespace)

class SourceControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='a2-identity-guard-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.root = self.base/'source'
        self.root.mkdir()
        (self.root/'tracked.txt').write_bytes(b'raw\n')
        for args in (('init','-q'), ('add','tracked.txt'),
                     ('-c','user.name=A2','-c','user.email=a2@example.invalid',
                      '-c','core.hooksPath=NUL' if os.name=='nt' else 'core.hooksPath=/dev/null',
                      'commit','-qm','fixture')):
            subprocess.run(['git','-c','core.autocrlf=false','-C',str(self.root),*args], check=True, capture_output=True)
    def inventory(self, root=None):
        target = root or self.root
        namespace['root'] = target
        helper = namespace['inventory']
        return helper(target) if inspect.signature(helper).parameters else helper()
    def junction(self, path, target):
        if os.name=='nt':
            subprocess.run(['powershell','-NoProfile','-Command',
                "New-Item -ItemType Junction -Path '"+str(path)+"' -Target '"+str(target)+"' | Out-Null"],
                check=True, capture_output=True, timeout=15)
        else:
            path.symlink_to(target, target_is_directory=True)
    def test_clean_positive_and_tracked_mutation_negative(self):
        self.assertEqual(len(self.inventory()),1)
        (self.root/'tracked.txt').write_bytes(b'changed\n')
        with self.assertRaises((AssertionError,ValueError,subprocess.CalledProcessError)): self.inventory()
    def test_unexpected_shadow_rejected(self):
        (self.root/'ssl.py').write_bytes(b'raise RuntimeError("SHADOW_EXECUTED")\n')
        with self.assertRaises((AssertionError,ValueError)): self.inventory()
    def test_cache_rejected_before_any_source_import(self):
        cache = self.root/'__pycache__'
        cache.mkdir()
        (cache/'ssl.cpython-312.pyc').write_bytes(b'cache-control')
        with self.assertRaises((AssertionError,ValueError)): self.inventory()
    def test_directory_reparse_rejected(self):
        target = self.base/'outside'
        target.mkdir()
        self.junction(self.root/'linked',target)
        with self.assertRaises((AssertionError,ValueError)): self.inventory()
    def test_root_ancestor_reparse_rejected(self):
        alias = self.base/'alias'
        self.junction(alias,self.root)
        with self.assertRaises((AssertionError,ValueError)): self.inventory(alias)
    def corrupt_object(self, oid, kind, raw):
        path=self.root/'.git'/'objects'/oid[:2]/oid[2:]
        path.parent.mkdir(exist_ok=True)
        if path.exists(): path.chmod(0o600)
        path.write_bytes(zlib.compress(kind.encode()+b' '+str(len(raw)).encode()+b'\0'+raw))
    def git(self,*args):
        return subprocess.check_output(['git','--no-replace-objects','-C',str(self.root),*args])
    def test_tampered_primary_blob_oid_rejected(self):
        oid=self.git('rev-parse','HEAD:tracked.txt').decode().strip()
        changed=b'changed\n'
        self.corrupt_object(oid,'blob',changed)
        (self.root/'tracked.txt').write_bytes(changed)
        with self.assertRaises((AssertionError,ValueError)): self.inventory()
    def test_tampered_primary_tree_oid_rejected(self):
        oldblob=self.git('rev-parse','HEAD:tracked.txt').decode().strip()
        treeoid=self.git('rev-parse','HEAD^{tree}').decode().strip()
        treeraw=self.git('cat-file','tree',treeoid)
        changed=b'changed\n'
        bloboid=hashlib.sha1(b'blob '+str(len(changed)).encode()+b'\0'+changed).hexdigest()
        self.corrupt_object(bloboid,'blob',changed)
        self.corrupt_object(treeoid,'tree',treeraw.replace(bytes.fromhex(oldblob),bytes.fromhex(bloboid)))
        (self.root/'tracked.txt').write_bytes(changed)
        with self.assertRaises((AssertionError,ValueError,subprocess.CalledProcessError)): self.inventory()
    def test_missing_and_duplicate_test_ids_rejected(self):
        names = tuple('test_gateway_identity.GatewayIdentityTests.'+name for name in namespace['EXPECTED_TEST_NAMES'])+(namespace['EXPECTED_STRICT_TEST_ID'],)
        class Case(unittest.TestCase):
            def runTest(self): pass
        def suite(values):
            tests=[]
            for value in values:
                test=Case()
                test.id=lambda value=value: value
                tests.append(test)
            return unittest.TestSuite(tests)
        namespace['validate_test_ids'](suite(names))
        with self.assertRaises(AssertionError): namespace['validate_test_ids'](suite(names[:-1]))
        with self.assertRaises(AssertionError): namespace['validate_test_ids'](suite(names[:-1]+(names[0],)))
        with self.assertRaises(AssertionError): namespace['validate_test_ids'](suite(names[1:]))
        with self.assertRaises(AssertionError): namespace['validate_test_ids'](suite(names+('UNAPPROVED_EXTRA',)))

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SourceControls))
    if not result.wasSuccessful(): raise SystemExit(1)
    print(json.dumps(dict(result='PASS',positive_controls=1,negative_controls=11,
                         scope='OWNED_SOURCE_GUARDS_NOT_NATIVE_ADMISSION')))
