"""Native ACL checks operate only on fresh test-owned directories."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


def ps(script):
    import base64
    encoded=base64.b64encode(script.encode('utf-16le')).decode('ascii')
    return subprocess.run([str(Path(os.environ['SYSTEMROOT'])/'System32/WindowsPowerShell/v1.0/powershell.exe'),
        '-NoProfile','-NonInteractive','-EncodedCommand',encoded],capture_output=True,text=True,timeout=90,env={k:v for k,v in os.environ.items() if k.upper()!='PSMODULEPATH'})


def restore_test_root(root,parent):
    # Cleanup is exclusively for this test's own freshly created absolute root.
    assert root.is_absolute() and root.parent==parent and parent.name.startswith('lab-acl-')
    assert root.resolve()==root and not root.is_symlink()
    literal="'"+str(root).replace("'","''")+"'"
    result=ps("$ErrorActionPreference='Stop';$p="+literal+"; $sid=[Security.Principal.WindowsIdentity]::GetCurrent().User;"
        "$a=Get-Acl -LiteralPath $p;$a.SetAccessRuleProtection($true,$false);foreach($old in @($a.GetAccessRules($true,$false,[Security.Principal.SecurityIdentifier]))){$a.RemoveAccessRuleSpecific($old)};"
        "$r=[Security.AccessControl.FileSystemAccessRule]::new($sid,'FullControl','ContainerInherit,ObjectInherit','None','Allow');$a.AddAccessRule($r);(Get-Item -LiteralPath $p -Force).SetAccessControl($a)")
    assert result.returncode==0,result.stderr


@unittest.skipUnless(os.name=='nt','Native Windows DACL test')
class CapsuleAclTests(unittest.TestCase):
    def test_sealed_fresh_code_reads_but_denies_cache_write_delete_rename_and_state_stays_writable(self):
        from unified_system.lab_capsule_acl import FreshCodeRoot
        with tempfile.TemporaryDirectory(prefix='lab-acl-') as directory:
            parent=Path(directory).resolve();root=parent/'code'
            owned=FreshCodeRoot.create(root)
            try:
                nested=root/'nested';nested.mkdir();code=nested/'fixture.py';code.write_text('value=73\n')
                manifest=root/'lab-release.json';manifest.write_bytes(b'owned test manifest\n')
                state=parent/'state';state.mkdir()
                pin=hashlib.sha256(manifest.read_bytes()).hexdigest()
                owned.seal(pin)
                child='''import importlib.util,pathlib,sys
root=pathlib.Path(sys.argv[1]);state=pathlib.Path(sys.argv[2]);p=root/'nested'/'fixture.py'
spec=importlib.util.spec_from_file_location('owned_acl_fixture',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);assert m.value==73
assert not list(root.rglob('*.pyc')) and not list(root.rglob('__pycache__'))
operations=[lambda:(p.parent/'new.pyc').write_bytes(b'x'),lambda:p.write_text('changed'),lambda:p.unlink(),lambda:p.rename(p.with_name('renamed.py')),lambda:(p.parent/'__pycache__').mkdir()]
for op in operations:
 try:op()
 except PermissionError:pass
 else:raise AssertionError('sealed write permitted')
(state/'own.log').write_text('writable')
'''
                # Deliberately omit -B: real import should attempt and fail cache creation.
                result=subprocess.run([sys.executable,'-I','-S','-c',child,str(root),str(state)],capture_output=True,text=True,timeout=30)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(code.read_text(),'value=73\n');self.assertEqual((state/'own.log').read_text(),'writable')
                self.assertTrue(owned.verify_sealed(pin))
            finally:restore_test_root(root,parent)
    def test_existing_root_and_wrong_manifest_pin_are_rejected(self):
        from unified_system.lab_capsule_acl import FreshCodeRoot
        with tempfile.TemporaryDirectory(prefix='lab-acl-') as directory:
            parent=Path(directory).resolve();root=parent/'code';owned=FreshCodeRoot.create(root)
            try:
                (root/'lab-release.json').write_bytes(b'owned')
                with self.assertRaises(FileExistsError):FreshCodeRoot.create(root)
                with self.assertRaisesRegex(ValueError,'MANIFEST_PIN'):owned.seal('0'*64)
                (root/'still-inactive').write_bytes(b'writable')
            finally:restore_test_root(root,parent)
    def test_descendant_explicit_write_ace_rejected_before_sealing(self):
        from unified_system.lab_capsule_acl import FreshCodeRoot
        with tempfile.TemporaryDirectory(prefix='lab-acl-') as directory:
            parent=Path(directory).resolve();root=parent/'code';owned=FreshCodeRoot.create(root)
            try:
                manifest=root/'lab-release.json';manifest.write_bytes(b'owned');code=root/'fixture.py';code.write_text('value=1')
                literal="'"+str(code).replace("'","''")+"'"
                result=ps("$ErrorActionPreference='Stop';$p="+literal+";$a=Get-Acl -LiteralPath $p;$sid=[Security.Principal.WindowsIdentity]::GetCurrent().User;$a.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($sid,'Write','Allow'));(Get-Item -LiteralPath $p -Force).SetAccessControl($a)")
                self.assertEqual(result.returncode,0,result.stderr)
                with self.assertRaisesRegex(ValueError,'ACL_'):owned.seal(hashlib.sha256(manifest.read_bytes()).hexdigest())
            finally:
                # Test-owned explicit descendant entry is removed before restoring root.
                result=ps("$p="+"'"+str(code).replace("'","''")+"'"+";$a=Get-Acl -LiteralPath $p;foreach($r in @($a.Access)){if(!$r.IsInherited){$a.RemoveAccessRuleSpecific($r)}};(Get-Item -LiteralPath $p -Force).SetAccessControl($a)")
                restore_test_root(root,parent)

    def test_created_root_identity_cannot_be_reused_for_a_replacement(self):
        from unified_system.lab_capsule_acl import FreshCodeRoot
        with tempfile.TemporaryDirectory(prefix='lab-acl-') as directory:
            parent=Path(directory).resolve();root=parent/'code';owned=FreshCodeRoot.create(root)
            root.rename(parent/'old-code');root.mkdir()
            manifest=root/'lab-release.json';manifest.write_bytes(b'replacement')
            with self.assertRaisesRegex(ValueError,'ACL_CREATED_ROOT_IDENTITY_CHANGED'):
                owned.seal(hashlib.sha256(manifest.read_bytes()).hexdigest())
            (root/'untouched').write_bytes(b'writable')
