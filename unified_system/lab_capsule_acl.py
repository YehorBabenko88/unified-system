"""Accidental-write protection for new builder-owned Windows LAB code roots.

This is not hostile-code containment or host attestation. The directory owner
retains WRITE_DAC and can deliberately change its ACL. Mutable state is separate.
There is no CLI or path-only API for sealing an existing directory.
"""
import base64
import hashlib
import os
from pathlib import Path
import re
import stat
import subprocess


# Fixed script; caller paths enter only through a private child environment.
_SCRIPT = r'''
$ErrorActionPreference='Stop'
$p=$env:UNIFIED_ACL_OWNED_ROOT
$sid=[Security.Principal.WindowsIdentity]::GetCurrent().User
$system=[Security.Principal.SecurityIdentifier]::new('S-1-5-18')
$admins=[Security.Principal.SecurityIdentifier]::new('S-1-5-32-544')
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
$adminDefaultOwner=($identity.Owner.Value -ceq $admins.Value -and ([Security.Principal.WindowsPrincipal]::new($identity)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator))
$inherit=[Security.AccessControl.InheritanceFlags]'ContainerInherit,ObjectInherit'
$none=[Security.AccessControl.PropagationFlags]::None
$allow=[Security.AccessControl.AccessControlType]::Allow
$deny=[Security.AccessControl.AccessControlType]::Deny
$full=[Security.AccessControl.FileSystemRights]::FullControl
$rx=[Security.AccessControl.FileSystemRights]::ReadAndExecute
$blocked=[Security.AccessControl.FileSystemRights]([int][Security.AccessControl.FileSystemRights]::Write -bor [int][Security.AccessControl.FileSystemRights]::Delete -bor [int][Security.AccessControl.FileSystemRights]::DeleteSubdirectoriesAndFiles)
function Rule($identity,$rights,$type){return [Security.AccessControl.FileSystemAccessRule]::new($identity,$rights,$inherit,$none,$type)}
function Set-Root($sealed){
 $a=Get-Acl -LiteralPath $p;$a.SetAccessRuleProtection($true,$false)
 if($a.GetOwner([Security.Principal.SecurityIdentifier]).Value -cne $sid.Value){$a.SetOwner($sid)}
 foreach($old in @($a.GetAccessRules($true,$false,[Security.Principal.SecurityIdentifier]))){$a.RemoveAccessRuleSpecific($old)}
 $a.AddAccessRule((Rule $system $full $allow));$a.AddAccessRule((Rule $admins $full $allow))
 if($sealed){$a.AddAccessRule((Rule $sid $blocked $deny));$a.AddAccessRule((Rule $sid $rx $allow))}
 else{$a.AddAccessRule((Rule $sid $full $allow))}
 (Get-Item -LiteralPath $p -Force).SetAccessControl($a)
}
function Verify-Tree($sealed){
 $expected=@{}
 $expected['Allow:S-1-5-18']=[int]$full;$expected['Allow:S-1-5-32-544']=[int]$full
 if($sealed){$expected['Allow:'+$sid.Value]=[int](Rule $sid $rx $allow).FileSystemRights;$expected['Deny:'+$sid.Value]=[int](Rule $sid $blocked $deny).FileSystemRights}
 else{$expected['Allow:'+$sid.Value]=[int]$full}
 $items=@(Get-Item -LiteralPath $p -Force)+@(Get-ChildItem -LiteralPath $p -Force -Recurse)
 if($items.Count -gt 300000){throw 'ACL_TREE_BUDGET'}
 foreach($item in $items){
  if(($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'ACL_LINK_REJECTED'}
  $isRoot=$item.FullName -ceq $p
  $a=Get-Acl -LiteralPath $item.FullName
  if($a.AreAccessRulesProtected -ne $isRoot){throw 'ACL_INHERITANCE_REJECTED'}
  if($isRoot -and $a.GetOwner([Security.Principal.SecurityIdentifier]).Value -cne $sid.Value){throw 'ACL_OWNER_REJECTED'}
  $rules=@($a.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]))
  if($rules.Count -ne $expected.Count){throw 'ACL_RULE_COUNT_REJECTED'}
  $seen=@{}
  foreach($r in $rules){
   $key=$r.AccessControlType.ToString()+':'+$r.IdentityReference.Value
   if(!$expected.ContainsKey($key) -or $seen.ContainsKey($key) -or [int]$r.FileSystemRights -ne $expected[$key]){throw 'ACL_RIGHTS_REJECTED'}
   if($r.IsInherited -eq $isRoot -or $r.PropagationFlags -ne $none){throw 'ACL_EXPLICIT_DESCENDANT_REJECTED'}
   if($item.PSIsContainer -and $r.InheritanceFlags -ne $inherit){throw 'ACL_DIRECTORY_FLAGS_REJECTED'}
   if(!$item.PSIsContainer -and $r.InheritanceFlags -ne [Security.AccessControl.InheritanceFlags]::None){throw 'ACL_FILE_FLAGS_REJECTED'}
   $seen[$key]=$true
  }
 }
}
function Normalize-Installer {
 # Phase one is read-only over the complete tree. Only pip's exact protected
 # OWNER_RIGHTS/System/Admins FullControl shape is eligible for inheritance.
 $items=@(Get-Item -LiteralPath $p -Force)+@(Get-ChildItem -LiteralPath $p -Force -Recurse | Sort-Object { $_.FullName.Length })
 if($items.Count -gt 300000){throw 'ACL_TREE_BUDGET'}
 $shapes=@{};$boundaries=@();$original=@{}
 foreach($item in $items){
  if(($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'ACL_LINK_REJECTED'}
  $a=Get-Acl -LiteralPath $item.FullName
  $isRoot=$item.FullName -ceq $p
  $owner=$a.GetOwner([Security.Principal.SecurityIdentifier]).Value
  # An unfiltered administrator token may default newly created descendants
  # to Builtin Administrators. This exception is derived from this token only;
  # it never applies to the capability root or a foreign/System owner.
  if($owner -cne $sid.Value -and ($isRoot -or !$adminDefaultOwner -or $owner -cne $admins.Value)){throw 'ACL_OWNER_REJECTED'}
  $protected=$a.AreAccessRulesProtected
  if($isRoot){if(!$protected){throw 'ACL_INHERITANCE_REJECTED'};$principal=$sid.Value}
  elseif($protected){
   if(!$item.PSIsContainer){throw 'ACL_INHERITANCE_REJECTED'}
   $principal='S-1-3-4';$boundaries+=,$item.FullName
  }else{
   $parent=[IO.Path]::GetDirectoryName($item.FullName)
   if(!$shapes.ContainsKey($parent)){throw 'ACL_INHERITANCE_REJECTED'}
   $principal=$shapes[$parent]
  }
  $expected=@($principal,'S-1-5-18','S-1-5-32-544');$seen=@{}
  $rules=@($a.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]))
  if($rules.Count -ne 3){throw 'ACL_RULE_COUNT_REJECTED'}
  foreach($r in $rules){
   $id=$r.IdentityReference.Value
   if($id -notin $expected -or $seen.ContainsKey($id) -or $r.AccessControlType -ne $allow -or [int]$r.FileSystemRights -ne [int]$full){throw 'ACL_RIGHTS_REJECTED'}
   if($r.IsInherited -eq $protected -or $r.PropagationFlags -ne $none){throw 'ACL_EXPLICIT_DESCENDANT_REJECTED'}
   if($item.PSIsContainer -and $r.InheritanceFlags -ne $inherit){throw 'ACL_DIRECTORY_FLAGS_REJECTED'}
   if(!$item.PSIsContainer -and $r.InheritanceFlags -ne [Security.AccessControl.InheritanceFlags]::None){throw 'ACL_FILE_FLAGS_REJECTED'}
   $seen[$id]=$true
  }
  $shapes[$item.FullName]=$principal;$original[$item.FullName]=$a.Sddl
 }
 # Recheck all descriptors before the first mutation; unknown ACLs never cause
 # a partial normalization. Each approved boundary then inherits its parent.
 foreach($item in $items){if((Get-Acl -LiteralPath $item.FullName).Sddl -cne $original[$item.FullName]){throw 'ACL_RIGHTS_REJECTED'}}
 foreach($path in $boundaries){
  $a=Get-Acl -LiteralPath $path
  foreach($r in @($a.GetAccessRules($true,$false,[Security.Principal.SecurityIdentifier]))){$a.RemoveAccessRuleSpecific($r)}
  $a.SetAccessRuleProtection($false,$false)
  (Get-Item -LiteralPath $path -Force).SetAccessControl($a)
 }
 Verify-Tree $false
}
switch($env:UNIFIED_ACL_OPERATION){
 'create' {Set-Root $false;Verify-Tree $false}
 'normalize' {Normalize-Installer}
 'seal' {Verify-Tree $false;Set-Root $true;Verify-Tree $true}
 'verify' {Verify-Tree $true}
 default {throw 'ACL_OPERATION_REJECTED'}
}
Write-Output 'OWNED_ACL_VERIFIED'
'''


def _safe(path):
    root=Path(path)
    raw=str(path)
    if (not root.is_absolute() or raw.startswith(('\\\\','//'))
            or any(part in ('.','..') or part.endswith((' ','.')) or ':' in part
                   for part in raw.replace('\\','/').split('/')[1:])):
        raise ValueError('ACL_ABSOLUTE_CANONICAL_ROOT_REQUIRED')
    for ancestor in (*reversed(root.parents),root):
        try:info=ancestor.lstat()
        except FileNotFoundError:continue
        if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&1024:
            raise ValueError('ACL_LINK_REJECTED')
    if root.resolve(strict=False)!=root:
        raise ValueError('ACL_CANONICAL_ROOT_REQUIRED')
    return root


class FreshCodeRoot:
    """Capability created only by atomically making a previously absent root."""
    @classmethod
    def create(cls,path):
        if os.name!='nt':raise ValueError('ACL_WINDOWS_REQUIRED')
        root=_safe(path)
        root.mkdir(exist_ok=False)
        instance=object.__new__(cls)
        instance._root=root
        info=root.stat();instance._identity=(info.st_dev,info.st_ino)
        instance._sealed=False
        instance._apply('create')
        return instance

    def __init__(self,*args,**kwargs):
        raise TypeError('Use FreshCodeRoot.create for a new directory')

    def _owned(self):
        root=_safe(self._root);info=root.stat()
        if not root.is_dir() or (info.st_dev,info.st_ino)!=self._identity:
            raise ValueError('ACL_CREATED_ROOT_IDENTITY_CHANGED')
        return root

    def _apply(self,operation):
        root=self._owned()
        env={k:v for k,v in os.environ.items() if k.upper() in
             {'SYSTEMROOT','WINDIR','SYSTEMDRIVE','TEMP','TMP','USERPROFILE','LOCALAPPDATA','APPDATA','OS'}}
        env.update(UNIFIED_ACL_OWNED_ROOT=str(root),UNIFIED_ACL_OPERATION=operation)
        powershell=Path(os.environ['SYSTEMROOT'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
        encoded=base64.b64encode(_SCRIPT.encode('utf-16le')).decode('ascii')
        result=subprocess.run([str(powershell),'-NoProfile','-NonInteractive','-EncodedCommand',encoded],
            env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=600)
        if result.returncode!=0 or result.stdout.decode('utf-8',errors='replace').strip()!='OWNED_ACL_VERIFIED':
            detail=result.stderr.decode('utf-8',errors='replace')
            code=next((c for c in ('ACL_TREE_BUDGET','ACL_LINK_REJECTED','ACL_INHERITANCE_REJECTED','ACL_OWNER_REJECTED','ACL_RULE_COUNT_REJECTED','ACL_RIGHTS_REJECTED','ACL_EXPLICIT_DESCENDANT_REJECTED','ACL_DIRECTORY_FLAGS_REJECTED','ACL_FILE_FLAGS_REJECTED') if c in detail),'ACL_VERIFICATION_FAILED')
            raise ValueError(code)

    def _manifest(self,pin):
        root=self._owned()
        if not isinstance(pin,str) or not re.fullmatch('[a-f0-9]{64}',pin):
            raise ValueError('ACL_MANIFEST_PIN_REQUIRED')
        path=_safe(root/'lab-release.json')
        if not path.is_file() or path.stat().st_size>64*1024*1024:
            raise ValueError('ACL_MANIFEST_PIN_REQUIRED')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=pin:
            raise ValueError('ACL_MANIFEST_PIN_MISMATCH')

    def normalize_installer_acls(self):
        """Normalize exact pip staging ACLs only, before final byte admission."""
        if self._sealed:raise ValueError('ACL_ALREADY_SEALED')
        root=self._owned()
        count=0
        for directory,dirs,files in os.walk(root,followlinks=False):
            for path in (Path(directory),*(Path(directory)/name for name in dirs+files)):
                count+=1
                if count>600000:raise ValueError('ACL_TREE_BUDGET')
                facts=path.lstat()
                if stat.S_ISLNK(facts.st_mode) or getattr(facts,'st_file_attributes',0)&1024:
                    raise ValueError('ACL_LINK_REJECTED')
                if not stat.S_ISDIR(facts.st_mode) and (not stat.S_ISREG(facts.st_mode) or facts.st_nlink!=1):
                    raise ValueError('ACL_HARDLINK_OR_SPECIAL_REJECTED')
        self._apply('normalize')
        return True

    def seal(self,manifest_sha256):
        """Call only after full capsule verification and original-source rechecks."""
        self._manifest(manifest_sha256)
        if self._sealed:raise ValueError('ACL_ALREADY_SEALED')
        self._apply('seal')
        self._sealed=True
        self._manifest(manifest_sha256)
        return True

    def verify_sealed(self,manifest_sha256):
        self._manifest(manifest_sha256)
        if not self._sealed:raise ValueError('ACL_NOT_SEALED')
        self._apply('verify')
        return True
