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
        '-NoProfile','-NonInteractive','-EncodedCommand',encoded],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=90,env={k:v for k,v in os.environ.items() if k.upper()!='PSMODULEPATH'})


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
    def pip_file(self,path):
        literal="'"+str(path).replace("'","''")+"'"
        result=ps("$ErrorActionPreference='Stop';$p="+literal+";$a=Get-Acl -LiteralPath $p;$a.SetAccessRuleProtection($true,$false);foreach($r in @($a.Access)){$a.RemoveAccessRuleSpecific($r)};foreach($id in @('S-1-3-4','S-1-5-18','S-1-5-32-544')){$s=[Security.Principal.SecurityIdentifier]::new($id);$a.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($s,'FullControl','Allow'))};(Get-Item -LiteralPath $p -Force).SetAccessControl($a)")
        self.assertEqual(result.returncode,0,result.stderr)

    def test_pip_protected_file_is_normalized_then_sealed_without_byte_changes(self):
        from unified_system.lab_capsule_acl import FreshCodeRoot
        with tempfile.TemporaryDirectory(prefix='lab-acl-') as directory:
            parent=Path(directory).resolve();root=parent/'code';owned=FreshCodeRoot.create(root)
            try:
                payload=root/'py.py';payload.write_bytes(b'value=73\n');self.pip_file(payload)
                before=hashlib.sha256(payload.read_bytes()).hexdigest()
                owned.normalize_installer_acls()
                manifest=root/'lab-release.json';manifest.write_bytes(b'owned')
                pin=hashlib.sha256(manifest.read_bytes()).hexdigest();owned.seal(pin)
                self.assertTrue(owned.verify_sealed(pin))
                self.assertEqual(hashlib.sha256(payload.read_bytes()).hexdigest(),before)
                with self.assertRaises(PermissionError):payload.write_bytes(b'changed')
            finally:restore_test_root(root,parent)

    def test_protected_file_extra_ace_refuses_before_any_normalization(self):
        from unified_system.lab_capsule_acl import FreshCodeRoot
        with tempfile.TemporaryDirectory(prefix='lab-acl-') as directory:
            parent=Path(directory).resolve();root=parent/'code';owned=FreshCodeRoot.create(root)
            try:
                valid=root/'a-valid.py';valid.write_bytes(b'valid');self.pip_file(valid)
                bad=root/'z-extra.py';bad.write_bytes(b'invalid');self.pip_file(bad)
                literal="'"+str(bad).replace("'","''")+"'"
                result=ps("$p="+literal+";$a=Get-Acl -LiteralPath $p;$a.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new('S-1-1-0'),'Write','Allow'));(Get-Item -LiteralPath $p -Force).SetAccessControl($a)")
                self.assertEqual(result.returncode,0,result.stderr)
                def descriptor(path):
                    result=ps("(Get-Acl -LiteralPath '"+str(path).replace("'","''")+"').Sddl")
                    self.assertEqual(result.returncode,0,result.stderr);return result.stdout
                before={path:descriptor(path) for path in (root,valid,bad)}
                with self.assertRaisesRegex(ValueError,'ACL_'):owned.normalize_installer_acls()
                self.assertEqual(before,{path:descriptor(path) for path in before})
            finally:restore_test_root(root,parent)

    def test_protected_file_foreign_owner_is_rejected(self):
        from unified_system.lab_capsule_acl import FreshCodeRoot
        with tempfile.TemporaryDirectory(prefix='lab-acl-') as directory:
            parent=Path(directory).resolve();root=parent/'code';owned=FreshCodeRoot.create(root)
            try:
                bad=root/'foreign.py';bad.write_bytes(b'owned');self.pip_file(bad)
                literal="'"+str(bad).replace("'","''")+"'"
                result=ps("$ErrorActionPreference='Stop';$p="+literal+";$a=Get-Acl -LiteralPath $p;$a.SetOwner([Security.Principal.SecurityIdentifier]::new('S-1-5-18'));(Get-Item -LiteralPath $p -Force).SetAccessControl($a)")
                if result.returncode:self.skipTest('Current token cannot assign SYSTEM as foreign file owner')
                with self.assertRaisesRegex(ValueError,'ACL_OWNER_REJECTED'):owned.normalize_installer_acls()
            finally:restore_test_root(root,parent)

    def pip_directory(self,path):
        literal="'"+str(path).replace("'","''")+"'"
        result=ps("$ErrorActionPreference='Stop';$p="+literal+";$a=Get-Acl -LiteralPath $p;$a.SetAccessRuleProtection($true,$false);foreach($r in @($a.Access)){$a.RemoveAccessRuleSpecific($r)};foreach($id in @('S-1-3-4','S-1-5-18','S-1-5-32-544')){$s=[Security.Principal.SecurityIdentifier]::new($id);$a.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($s,'FullControl','ContainerInherit,ObjectInherit','None','Allow'))};(Get-Item -LiteralPath $p -Force).SetAccessControl($a)")
        self.assertEqual(result.returncode,0,result.stderr)

    def test_pip_protected_directory_is_normalized_then_sealed(self):
        from unified_system.lab_capsule_acl import FreshCodeRoot
        with tempfile.TemporaryDirectory(prefix='lab-acl-') as directory:
            parent=Path(directory).resolve();root=parent/'code';owned=FreshCodeRoot.create(root)
            try:
                package=root/'package';package.mkdir();self.pip_directory(package)
                (package/'nested').mkdir();(package/'nested/file.py').write_bytes(b'value=1\n')
                manifest=root/'lab-release.json';manifest.write_bytes(b'owned')
                owned.normalize_installer_acls()
                owned.seal(hashlib.sha256(manifest.read_bytes()).hexdigest())
                self.assertTrue(owned.verify_sealed(hashlib.sha256(manifest.read_bytes()).hexdigest()))
                with self.assertRaises(PermissionError):(package/'nested/file.py').write_bytes(b'changed')
            finally:restore_test_root(root,parent)

    def test_unknown_ace_refuses_normalization_before_any_acl_write(self):
        from unified_system.lab_capsule_acl import FreshCodeRoot
        with tempfile.TemporaryDirectory(prefix='lab-acl-') as directory:
            parent=Path(directory).resolve();root=parent/'code';owned=FreshCodeRoot.create(root)
            try:
                package=root/'a-package';package.mkdir();self.pip_directory(package)
                bad=root/'z-foreign';bad.mkdir()
                literal="'"+str(bad).replace("'","''")+"'"
                result=ps("$p="+literal+";$a=Get-Acl -LiteralPath $p;$a.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new('S-1-1-0'),'Write','Allow'));(Get-Item -LiteralPath $p -Force).SetAccessControl($a)")
                self.assertEqual(result.returncode,0,result.stderr)
                def acl(path):
                    result=ps("(Get-Acl -LiteralPath '"+str(path).replace("'","''")+"').Sddl")
                    self.assertEqual(result.returncode,0,result.stderr);return result.stdout
                before={path:acl(path) for path in (root,package,bad)}
                with self.assertRaisesRegex(ValueError,'ACL_'):owned.normalize_installer_acls()
                self.assertEqual(before,{path:acl(path) for path in before})
            finally:restore_test_root(root,parent)

    def test_hardlink_refuses_normalization_before_acl_changes(self):
        from unified_system.lab_capsule_acl import FreshCodeRoot
        with tempfile.TemporaryDirectory(prefix='lab-acl-') as directory:
            parent=Path(directory).resolve();root=parent/'code';owned=FreshCodeRoot.create(root)
            try:
                package=root/'package';package.mkdir();self.pip_directory(package)
                (package/'file').write_bytes(b'owned');os.link(package/'file',root/'alias')
                with self.assertRaisesRegex(ValueError,'ACL_HARDLINK'):owned.normalize_installer_acls()
            finally:restore_test_root(root,parent)

    def test_foreign_owner_refuses_normalization_before_acl_changes(self):
        from unified_system.lab_capsule_acl import FreshCodeRoot
        with tempfile.TemporaryDirectory(prefix='lab-acl-') as directory:
            parent=Path(directory).resolve();root=parent/'code';owned=FreshCodeRoot.create(root)
            try:
                package=root/'a-package';package.mkdir();self.pip_directory(package)
                bad=root/'z-owner';bad.mkdir()
                literal="'"+str(bad).replace("'","''")+"'"
                result=ps("$ErrorActionPreference='Stop';$p="+literal+";$a=Get-Acl -LiteralPath $p;$a.SetOwner([Security.Principal.SecurityIdentifier]::new('S-1-5-18'));(Get-Item -LiteralPath $p -Force).SetAccessControl($a)")
                if result.returncode:self.skipTest('Current token cannot assign SYSTEM as foreign test owner')
                with self.assertRaisesRegex(ValueError,'ACL_OWNER_REJECTED'):owned.normalize_installer_acls()
                result=ps("(Get-Acl -LiteralPath '"+str(package).replace("'","''")+"').AreAccessRulesProtected")
                self.assertEqual(result.stdout.strip(),'True')
            finally:restore_test_root(root,parent)

    def test_token_default_admin_owner_descendants_are_supported_conditionally(self):
        from unified_system.lab_capsule_acl import FreshCodeRoot
        result=ps("$i=[Security.Principal.WindowsIdentity]::GetCurrent();if($i.Owner.Value -eq 'S-1-5-32-544' -and ([Security.Principal.WindowsPrincipal]::new($i)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){'SUPPORTED'}else{'UNAVAILABLE'}")
        self.assertEqual(result.returncode,0,result.stderr)
        if result.stdout.strip()!='SUPPORTED':self.skipTest('Current token is not an unfiltered administrator with Administrators default owner')
        with tempfile.TemporaryDirectory(prefix='lab-acl-') as directory:
            parent=Path(directory).resolve();root=parent/'code';owned=FreshCodeRoot.create(root)
            try:
                package=root/'package';package.mkdir();self.pip_directory(package)
                child=package/'file.py';child.write_bytes(b'value=1\n')
                for path in (package,child):
                    # Exercise the real token default. Even redundant SetOwner
                    # can remove OWNER_RIGHTS ACEs on Windows, altering the
                    # installer shape that this fixture is meant to validate.
                    result=ps("$ErrorActionPreference='Stop';$p='"+str(path).replace("'","''")+"';(Get-Acl -LiteralPath $p).GetOwner([Security.Principal.SecurityIdentifier]).Value")
                    self.assertEqual(result.returncode,0,result.stderr)
                    self.assertEqual(result.stdout.strip(),'S-1-5-32-544')
                owned.normalize_installer_acls()
                manifest=root/'lab-release.json';manifest.write_bytes(b'owned')
                pin=hashlib.sha256(manifest.read_bytes()).hexdigest();owned.seal(pin)
                self.assertTrue(owned.verify_sealed(pin))
            finally:restore_test_root(root,parent)

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
                result=subprocess.run([sys.executable,'-I','-S','-c',child,str(root),str(state)],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=30)
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
