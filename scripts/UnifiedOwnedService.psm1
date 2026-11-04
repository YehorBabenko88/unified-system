# Fixed reviewed backend. Import defines functions; native operations require
# explicit invocation from the externally admitted phase-plan Python boundary.
# https://learn.microsoft.com/windows/win32/api/winsvc/nf-winsvc-createservicew
# https://learn.microsoft.com/windows/win32/api/winsvc/ns-winsvc-service_sid_info
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$script:Native=@'
using System;
using System.Runtime.InteropServices;
public static class UnifiedStoppedServiceNative {
 static string Drain(System.IO.StreamReader reader,System.Diagnostics.Process process){
  var result=new System.Text.StringBuilder();var buffer=new char[4096];int count;
  while((count=reader.Read(buffer,0,buffer.Length))>0){
   if(result.Length+count>65536){try{process.Kill();}catch(InvalidOperationException){}throw new InvalidOperationException("CHILD_OUTPUT_LIMIT");}
   result.Append(buffer,0,count);
  }
  return result.ToString();
 }
 public static string Run(string executable,string arguments){
  using(var p=new System.Diagnostics.Process()){
   p.StartInfo.FileName=executable;p.StartInfo.Arguments=arguments;p.StartInfo.UseShellExecute=false;p.StartInfo.CreateNoWindow=true;
   p.StartInfo.RedirectStandardOutput=true;p.StartInfo.RedirectStandardError=true;
   var encoding=System.Text.Encoding.GetEncoding(System.Globalization.CultureInfo.CurrentCulture.TextInfo.OEMCodePage,System.Text.EncoderFallback.ExceptionFallback,System.Text.DecoderFallback.ExceptionFallback);
   p.StartInfo.StandardOutputEncoding=encoding;p.StartInfo.StandardErrorEncoding=encoding;
   if(!p.Start())throw new InvalidOperationException("CHILD_REJECTED");
   var output=System.Threading.Tasks.Task.Factory.StartNew(()=>Drain(p.StandardOutput,p));
   var errors=System.Threading.Tasks.Task.Factory.StartNew(()=>Drain(p.StandardError,p));
   try{
    if(!p.WaitForExit(5000))throw new InvalidOperationException("CHILD_DEADLINE");
    if(!System.Threading.Tasks.Task.WaitAll(new System.Threading.Tasks.Task[]{output,errors},1000))throw new InvalidOperationException("CHILD_DRAIN_DEADLINE");
    if(p.ExitCode!=0)throw new InvalidOperationException("CHILD_REJECTED");return output.Result.TrimEnd('\r','\n');
   }finally{
    if(!p.HasExited){p.Kill();p.WaitForExit(1000);}
    try{System.Threading.Tasks.Task.WaitAll(new System.Threading.Tasks.Task[]{output,errors},1000);}catch(AggregateException){}
   }
  }
 }
 [DllImport("advapi32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern IntPtr OpenSCManagerW(string a,string b,uint c);
 [DllImport("advapi32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern IntPtr OpenServiceW(IntPtr a,string b,uint c);
 [DllImport("advapi32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern IntPtr CreateServiceW(IntPtr a,string b,string c,uint d,uint e,uint f,uint g,string h,string i,IntPtr j,string k,string l,string m);
 [DllImport("advapi32.dll",SetLastError=true)] static extern bool CloseServiceHandle(IntPtr a);
 [StructLayout(LayoutKind.Sequential)] struct SID_INFO {public uint type;}
 [DllImport("advapi32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern bool ChangeServiceConfig2W(IntPtr a,uint b,ref SID_INFO c);
 [DllImport("advapi32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern bool QueryServiceConfig2W(IntPtr a,uint b,IntPtr c,uint d,out uint e);
 [DllImport("advapi32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern bool QueryServiceConfigW(IntPtr a,IntPtr b,uint c,out uint d);
 [StructLayout(LayoutKind.Sequential)] struct CONFIG {public uint type,start,error;public IntPtr binary,group;public uint tag;public IntPtr dependencies,account,display;}
 [StructLayout(LayoutKind.Sequential)] struct STATUS {public uint type,state,controls,winerror,specific,checkpoint,hint;}
 [DllImport("advapi32.dll",SetLastError=true)] static extern bool QueryServiceStatus(IntPtr a,out STATUS b);
 public sealed class Snapshot {public string Binary,Account;public uint Start,Sid,State;}
 static void Check(bool ok){if(!ok)throw new InvalidOperationException("SCM_REJECTED");}
 static IntPtr Manager(uint access){IntPtr h=OpenSCManagerW(null,null,access);Check(h!=IntPtr.Zero);return h;}
 public static bool Exists(string name){IntPtr m=Manager(1);try{IntPtr h=OpenServiceW(m,name,4);if(h!=IntPtr.Zero){CloseServiceHandle(h);return true;}Check(Marshal.GetLastWin32Error()==1060);return false;}finally{CloseServiceHandle(m);}}
 public static void Create(string name,string binary){IntPtr m=Manager(2);IntPtr h=IntPtr.Zero;try{
  // Own process=16; demand start=3; normal error=1; LocalService from creation.
  h=CreateServiceW(m,name,name,7,16,3,1,"\""+binary+"\"",null,IntPtr.Zero,null,"NT AUTHORITY\\LocalService",null);Check(h!=IntPtr.Zero);
  SID_INFO sid=new SID_INFO();sid.type=1;Check(ChangeServiceConfig2W(h,5,ref sid));
 }finally{if(h!=IntPtr.Zero)CloseServiceHandle(h);CloseServiceHandle(m);}}
 public static Snapshot Read(string name){IntPtr m=Manager(1);IntPtr h=IntPtr.Zero;IntPtr config=IntPtr.Zero;IntPtr sid=IntPtr.Zero;try{
  h=OpenServiceW(m,name,5);Check(h!=IntPtr.Zero);uint size=0;QueryServiceConfigW(h,IntPtr.Zero,0,out size);Check(size>0 && size<=65536);
  config=Marshal.AllocHGlobal((int)size);Check(QueryServiceConfigW(h,config,size,out size));CONFIG c=(CONFIG)Marshal.PtrToStructure(config,typeof(CONFIG));
  sid=Marshal.AllocHGlobal(4);uint needed;Check(QueryServiceConfig2W(h,5,sid,4,out needed));STATUS state;Check(QueryServiceStatus(h,out state));
  return new Snapshot {Binary=Marshal.PtrToStringUni(c.binary),Account=Marshal.PtrToStringUni(c.account),Start=c.start,Sid=(uint)Marshal.ReadInt32(sid),State=state.state};
 }finally{if(config!=IntPtr.Zero)Marshal.FreeHGlobal(config);if(sid!=IntPtr.Zero)Marshal.FreeHGlobal(sid);if(h!=IntPtr.Zero)CloseServiceHandle(h);CloseServiceHandle(m);}}
}
'@

function Assert-OwnedAdmin {
 $id=[Security.Principal.WindowsIdentity]::GetCurrent()
 if(-not ([Security.Principal.WindowsPrincipal]::new($id)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){throw 'ELEVATED_OWNER_SESSION_REQUIRED'}
 if(-not ('UnifiedStoppedServiceNative' -as [type])){Add-Type -TypeDefinition $script:Native}
}
function Assert-OwnedPath([string]$Path){
 if($Path -cnotmatch '^[A-Za-z]:\\' -or $Path.Substring(2).Contains(':') -or $Path.Contains('/') -or $Path.Contains('..') -or $Path.Contains('"') -or $Path -match '[\x00-\x1f]'){throw 'LOCAL_PATH_REJECTED'}
 $full=[IO.Path]::GetFullPath($Path);if($full -cne $Path){throw 'CANONICAL_PATH_REQUIRED'}
 if([IO.DriveInfo]::new([IO.Path]::GetPathRoot($full)).DriveType -ne [IO.DriveType]::Fixed){throw 'FIXED_DRIVE_REQUIRED'}
 $cursor=$full
 while($cursor){if(Test-Path -LiteralPath $cursor){$item=Get-Item -LiteralPath $cursor -Force;if(($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'LINK_REJECTED'}};$cursor=[IO.Path]::GetDirectoryName($cursor.TrimEnd('\'))}
}
function Hash-OwnedText([string]$Text){$h=[Security.Cryptography.SHA256]::Create();try{return ([BitConverter]::ToString($h.ComputeHash([Text.Encoding]::UTF8.GetBytes($Text)))).Replace('-','').ToLowerInvariant()}finally{$h.Dispose()}}
function Assert-OwnedFile([string]$Path,[string]$Pin){
 Assert-OwnedPath $Path
 if($Pin -cnotmatch '^[a-f0-9]{64}$' -or -not (Test-Path -LiteralPath $Path -PathType Leaf) -or (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() -cne $Pin){throw 'CLOSED_MEMBER_PIN_MISMATCH'}
}
function Quote-OwnedArgument([string]$Value){
 return '"'+[regex]::Replace([regex]::Replace($Value,'(\\*)"','$1$1\"'),'(\\+)$','$1$1')+'"'
}
function Invoke-OwnedNative([string]$Exe,[string[]]$Arguments){
 $argumentsText=(@($Arguments|ForEach-Object {Quote-OwnedArgument $_}) -join ' ')
 return [UnifiedStoppedServiceNative]::Run($Exe,$argumentsText)
}
function Get-OwnedSid($Plan){
 $sc=Join-Path ([Environment]::SystemDirectory) 'sc.exe'
 if($Plan.native_tools.sc.path -cne $sc){throw 'OS_TOOL_PATH_MISMATCH'}
 Assert-OwnedFile $sc $Plan.native_tools.sc.sha256
 $text=Invoke-OwnedNative $sc @('showsid',[string]$Plan.service_name)
 $matches=[regex]::Matches($text,'S-[0-9]+(?:-[0-9]+)+')
 if($matches.Count -ne 1 -or $matches[0].Value -cne $Plan.service_sid){throw 'SERVICE_SID_MISMATCH'}
 return $matches[0].Value
}
function Set-OwnedAcl([string]$Path,[string]$Sid,[string]$Rights){
 $a=Get-Acl -LiteralPath $Path;$a.SetOwner([Security.Principal.SecurityIdentifier]::new('S-1-5-32-544'));$a.SetAccessRuleProtection($true,$false)
 foreach($r in @($a.GetAccessRules($true,$false,[Security.Principal.SecurityIdentifier]))){$a.RemoveAccessRuleSpecific($r)}
 foreach($id in @('S-1-5-18','S-1-5-32-544')){$a.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($id),'FullControl','ContainerInherit,ObjectInherit','None','Allow'))}
 if($Sid){$a.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($Sid),$Rights,'ContainerInherit,ObjectInherit','None','Allow'))}
 (Get-Item -LiteralPath $Path -Force).SetAccessControl($a)
}
function Get-OwnedAclProof([string]$Path,[string]$Sid,[string]$Rights,[bool]$Recurse){
 $items=@(Get-Item -LiteralPath $Path -Force);if($Recurse){$items+=@(Get-ChildItem -LiteralPath $Path -Force -Recurse)}
 if($items.Count -gt 300000){throw 'ACL_TREE_LIMIT'}
 $expected=@{'S-1-5-18'=[int][Security.AccessControl.FileSystemRights]::FullControl;'S-1-5-32-544'=[int][Security.AccessControl.FileSystemRights]::FullControl}
 if($Sid){$rule=[Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($Sid),$Rights,'ContainerInherit,ObjectInherit','None','Allow');$expected[$Sid]=[int]$rule.FileSystemRights}
 $lines=New-Object 'Collections.Generic.List[string]'
 foreach($item in ($items|Sort-Object FullName)){
  Assert-OwnedPath $item.FullName
  $acl=Get-Acl -LiteralPath $item.FullName;$owner=$acl.GetOwner([Security.Principal.SecurityIdentifier]).Value
  if($owner -notin @('S-1-5-18','S-1-5-32-544') -or $acl.AreAccessRulesProtected -ne ($item.FullName -ceq $Path)){throw 'ACL_OWNER_OR_INHERITANCE_MISMATCH'}
  $rules=@($acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]));if($rules.Count -ne $expected.Count){throw 'ACL_RULE_COUNT'}
  $seen=@{}
  foreach($rule in $rules){
   $id=$rule.IdentityReference.Value
   if(-not $expected.ContainsKey($id) -or $seen.ContainsKey($id) -or $rule.AccessControlType -ne 'Allow' -or [int]$rule.FileSystemRights -ne $expected[$id] -or $rule.PropagationFlags -ne 'None' -or $rule.IsInherited -eq ($item.FullName -ceq $Path)){throw 'ACL_RIGHTS_MISMATCH'}
   if($item.PSIsContainer -and $rule.InheritanceFlags -ne 'ContainerInherit,ObjectInherit'){throw 'ACL_FLAGS_MISMATCH'}
   if(-not $item.PSIsContainer -and $rule.InheritanceFlags -ne 'None'){throw 'ACL_FLAGS_MISMATCH'}
   $seen[$id]=$true
  }
  $lines.Add($item.FullName.Substring($Path.Length)+[char]0+$acl.Sddl)
 }
 return Hash-OwnedText ($lines -join [char]10)
}
function Assert-OwnedMarker($Plan){
 $path=Join-Path $Plan.root 'ownership\claim.txt'
 if(-not (Test-Path -LiteralPath $path) -or [IO.File]::ReadAllText($path) -cne $Plan.plan_sha256){throw 'OWNED_ROOT_RECEIPT_REQUIRED'}
}
function Get-OwnedProof($Plan){
 Assert-OwnedMarker $Plan
 $null=Get-OwnedAclProof $Plan.root $Plan.service_sid 'ReadAndExecute' $false
 $null=Get-OwnedAclProof (Join-Path $Plan.root 'ownership') '' '' $true
 $code=Get-OwnedAclProof $Plan.code $Plan.service_sid 'ReadAndExecute' $true
 $state=Get-OwnedAclProof $Plan.state $Plan.service_sid 'Modify' $false
 return @{code_acl_sha256=$code;state_acl_sha256=$state;acl_policy='EXACT_SERVICE_SID_V1'}
}
function Get-OwnedService($Plan){
 Assert-OwnedFile $Plan.nssm $Plan.nssm_sha256;Assert-OwnedFile $Plan.python $Plan.python_sha256;Assert-OwnedFile $Plan.bootstrap $Plan.bootstrap_sha256;Assert-OwnedFile $Plan.entry $Plan.entry_sha256
 $native=[UnifiedStoppedServiceNative]::Read($Plan.service_name)
 $sid=([Security.Principal.NTAccount]::new('NT SERVICE\'+$Plan.service_name)).Translate([Security.Principal.SecurityIdentifier]).Value
 if($sid -cne $Plan.service_sid -or $native.Sid -ne 1 -or $native.State -ne 1 -or $native.Start -ne 3 -or $native.Account -ine 'NT AUTHORITY\LocalService' -or $native.Binary -cne ('"'+$Plan.nssm+'"')){throw 'LIVE_SCM_MISMATCH'}
 $proof=Get-OwnedProof $Plan
 return @{service_name=$Plan.service_name;service_sid=$sid;account='NT AUTHORITY\LocalService';start_type=[int]$native.Start;sid_type=[int]$native.Sid;state=[int]$native.State;binary_path=$native.Binary;
 application=(Invoke-OwnedNative $Plan.nssm @('get',$Plan.service_name,'Application'));parameters=(Invoke-OwnedNative $Plan.nssm @('get',$Plan.service_name,'AppParameters'));directory=(Invoke-OwnedNative $Plan.nssm @('get',$Plan.service_name,'AppDirectory'));app_exit=(Invoke-OwnedNative $Plan.nssm @('get',$Plan.service_name,'AppExit','Default'));
 marker=$Plan.plan_sha256;code_acl_sha256=$proof.code_acl_sha256;state_acl_sha256=$proof.state_acl_sha256;acl_policy=$proof.acl_policy}
}
function Invoke-UnifiedOwnedService($Request){
 $p=$Request.plan
 if(-not [string]::Equals([string]$p.computer_name,[Environment]::MachineName,[StringComparison]::OrdinalIgnoreCase)){throw 'COMPUTER_BINDING_MISMATCH'}
 Assert-OwnedAdmin
 $ps=Join-Path ([Environment]::SystemDirectory) 'WindowsPowerShell\v1.0\powershell.exe'
 if($p.native_tools.powershell.path -cne $ps){throw 'OS_TOOL_PATH_MISMATCH'}
 Assert-OwnedFile $ps $p.native_tools.powershell.sha256
 if($Request.action -cnotin @('BEGIN','SEAL','REGISTER','INSPECT') -or $p.schema -cne 'unified.owned-stopped-service.v1' -or $p.activation -cne 'BLOCKED' -or $p.plan_sha256 -cnotmatch '^[a-f0-9]{64}$' -or $p.service_name -cnotmatch '^UnifiedLab_[a-f0-9]{24}$' -or $p.service_sid -cnotmatch '^S-1-5-80-(?:[0-9]+-){4}[0-9]+$'){throw 'CLOSED_PLAN_REQUIRED'}
 foreach($path in @($p.root,$p.code,$p.state,$p.nssm,$p.python,$p.bootstrap,$p.entry)){Assert-OwnedPath $path}
 if($p.code -cne (Join-Path $p.root 'code') -or $p.state -cne (Join-Path $p.root 'state') -or $p.nssm -cne (Join-Path $p.code 'runtime\nssm\nssm.exe') -or $p.python -cne (Join-Path $p.code 'runtime\python\python.exe') -or $p.bootstrap -cne (Join-Path $p.code 'sources\unified-system\unified_system\owned_python.py') -or $p.entry -cne (Join-Path $p.code 'sources\unified-system\unified_system\service_entry.py') -or $p.parameters -cne ('-I -S -B "'+$p.entry+'"')){throw 'ROOT_BINDING_MISMATCH'}
 $null=Get-OwnedSid $p
 switch -CaseSensitive ($Request.action){
  'BEGIN'{
   if([UnifiedStoppedServiceNative]::Exists($p.service_name) -or (Test-Path -LiteralPath $p.root)){throw 'EXISTING_RESOURCE_REJECTED'}
   $null=New-Item -ItemType Directory -Path $p.root -ErrorAction Stop
   Set-OwnedAcl $p.root $p.service_sid 'ReadAndExecute'
   $control=Join-Path $p.root 'ownership';$null=New-Item -ItemType Directory -Path $control
   Set-OwnedAcl $control '' ''
   $null=New-Item -ItemType Directory -Path $p.state;Set-OwnedAcl $p.state $p.service_sid 'Modify'
   $f=[IO.File]::Open((Join-Path $control 'claim.txt'),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
   try{$bytes=[Text.Encoding]::UTF8.GetBytes($p.plan_sha256);$f.Write($bytes,0,$bytes.Length);$f.Flush($true)}finally{$f.Dispose()}
   return @{root_created=$true}
  }
  'SEAL'{
   Assert-OwnedMarker $p
   foreach($tree in @($p.code,(Join-Path $p.root 'ownership'))){
    $items=@(Get-Item -LiteralPath $tree -Force)+@(Get-ChildItem -LiteralPath $tree -Force -Recurse)
    if($items.Count -gt 300000){throw 'ACL_TREE_LIMIT'}
    foreach($item in $items){Assert-OwnedPath $item.FullName;$a=Get-Acl -LiteralPath $item.FullName;$a.SetOwner([Security.Principal.SecurityIdentifier]::new('S-1-5-32-544'));$item.SetAccessControl($a)}
   }
   Set-OwnedAcl $p.code $p.service_sid 'ReadAndExecute'
   return Get-OwnedProof $p
  }
  'REGISTER'{
   Assert-OwnedMarker $p
   $null=Get-OwnedProof $p
   Assert-OwnedFile $p.nssm $p.nssm_sha256;Assert-OwnedFile $p.python $p.python_sha256;Assert-OwnedFile $p.bootstrap $p.bootstrap_sha256;Assert-OwnedFile $p.entry $p.entry_sha256
   if([UnifiedStoppedServiceNative]::Exists($p.service_name)){throw 'EXISTING_RESOURCE_REJECTED'}
   [UnifiedStoppedServiceNative]::Create($p.service_name,$p.nssm)
   foreach($setting in @(@('Application',$p.python),@('AppParameters',$p.parameters),@('AppDirectory',$p.code),@('AppExit','Default','Exit'))){$null=Invoke-OwnedNative $p.nssm (@('set',$p.service_name)+$setting)}
   return Get-OwnedService $p
  }
  'INSPECT'{return Get-OwnedService $p}
 }
}
Export-ModuleMember -Function Invoke-UnifiedOwnedService
