# Fixed reviewed backend. Import defines functions; native operations require
# explicit invocation from the externally admitted phase-plan Python boundary.
# https://learn.microsoft.com/windows/win32/api/winsvc/nf-winsvc-createservicew
# https://learn.microsoft.com/windows/win32/api/winsvc/ns-winsvc-service_sid_info
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$script:NativeStage='UNAVAILABLE'
function Get-UnifiedOwnedServiceStage {return $script:NativeStage}
function Get-UnifiedOwnedNativeExitCode {
 if($script:NativeStage -cmatch '^NSSM_(SET|GET)_' -and ('UnifiedStoppedServiceNative' -as [type])){
  $code=[UnifiedStoppedServiceNative]::LastExitCode
  if($code -ge 0 -and $code -le 4294967295){return $code}
 }
 return $null
}
$script:Native=@'
using System;
using System.Runtime.InteropServices;
public static class UnifiedStoppedServiceNative {
 public static long LastExitCode=-1;
 static string Drain(System.IO.StreamReader reader,System.Diagnostics.Process process){
  var result=new System.Text.StringBuilder();var buffer=new char[4096];int count;
  while((count=reader.Read(buffer,0,buffer.Length))>0){
   if(result.Length+count>65536){try{process.Kill();}catch(InvalidOperationException){}throw new InvalidOperationException("CHILD_OUTPUT_LIMIT");}
   result.Append(buffer,0,count);
  }
  return result.ToString();
 }
 public static string Run(string executable,string arguments){
  LastExitCode=-1;
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
    LastExitCode=unchecked((uint)p.ExitCode);
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
 $script:NativeStage='SID_LOOKUP'
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
 $script:NativeStage='ACL_PROOF'
 Assert-OwnedMarker $Plan
 $null=Get-OwnedAclProof $Plan.root $Plan.service_sid 'ReadAndExecute' $false
 $null=Get-OwnedAclProof (Join-Path $Plan.root 'ownership') '' '' $true
 $code=Get-OwnedAclProof $Plan.code $Plan.service_sid 'ReadAndExecute' $true
 $state=Get-OwnedAclProof $Plan.state $Plan.service_sid 'Modify' $false
 return @{code_acl_sha256=$code;state_acl_sha256=$state;acl_policy='EXACT_SERVICE_SID_V1'}
}
function Get-OwnedService($Plan){
 $script:NativeStage='MEMBER_PINS'
 Assert-OwnedFile $Plan.nssm $Plan.nssm_sha256;Assert-OwnedFile $Plan.python $Plan.python_sha256;Assert-OwnedFile $Plan.bootstrap $Plan.bootstrap_sha256;Assert-OwnedFile $Plan.entry $Plan.entry_sha256
 $script:NativeStage='SCM_READ';$native=[UnifiedStoppedServiceNative]::Read($Plan.service_name)
 $script:NativeStage='SCM_PROOF'
 $sid=([Security.Principal.NTAccount]::new('NT SERVICE\'+$Plan.service_name)).Translate([Security.Principal.SecurityIdentifier]).Value
 if($sid -cne $Plan.service_sid -or $native.Sid -ne 1 -or $native.State -ne 1 -or $native.Start -ne 3 -or $native.Account -ine 'NT AUTHORITY\LocalService' -or $native.Binary -cne ('"'+$Plan.nssm+'"')){throw 'LIVE_SCM_MISMATCH'}
 $proof=Get-OwnedProof $Plan
 $script:NativeStage='NSSM_GET_APPLICATION';$application=Invoke-OwnedNative $Plan.nssm @('get',$Plan.service_name,'Application')
 $script:NativeStage='NSSM_GET_PARAMETERS';$parameters=Invoke-OwnedNative $Plan.nssm @('get',$Plan.service_name,'AppParameters')
 $script:NativeStage='NSSM_GET_DIRECTORY';$directory=Invoke-OwnedNative $Plan.nssm @('get',$Plan.service_name,'AppDirectory')
 $script:NativeStage='NSSM_GET_APP_EXIT';$appExit=Invoke-OwnedNative $Plan.nssm @('get',$Plan.service_name,'AppExit','Default')
 return @{service_name=$Plan.service_name;service_sid=$sid;account='NT AUTHORITY\LocalService';start_type=[int]$native.Start;sid_type=[int]$native.Sid;state=[int]$native.State;binary_path=$native.Binary;
 application=$application;parameters=$parameters;directory=$directory;app_exit=$appExit;
 marker=$Plan.plan_sha256;code_acl_sha256=$proof.code_acl_sha256;state_acl_sha256=$proof.state_acl_sha256;acl_policy=$proof.acl_policy}
}
function Write-NewOwnedNssmApplication($ServiceKey,[string]$Application){
 # NSSM treats a service without Parameters/Application as a native service and
 # refuses App* edits. Seed only the exact freshly created service namespace.
 # https://git.nssm.cc/nssm/nssm/src/a2f02c89bef2c4aae9fbebc1191291e5be41380a/service.cpp
 $existing=$ServiceKey.OpenSubKey('Parameters',$false)
 if($null -ne $existing){$existing.Dispose();throw 'EXISTING_NSSM_PARAMETERS_REJECTED'}
 $parameters=$ServiceKey.CreateSubKey('Parameters',[Microsoft.Win32.RegistryKeyPermissionCheck]::ReadWriteSubTree,[Microsoft.Win32.RegistryOptions]::None)
 if($null -eq $parameters){throw 'NSSM_PARAMETERS_UNAVAILABLE'}
 try{
  if($parameters.ValueCount -ne 0 -or $parameters.SubKeyCount -ne 0){throw 'EXISTING_NSSM_PARAMETERS_REJECTED'}
  $parameters.SetValue('Application',$Application,[Microsoft.Win32.RegistryValueKind]::ExpandString)
  $parameters.Flush()
  if($parameters.GetValue('Application',$null,[Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames) -cne $Application -or $parameters.GetValueKind('Application') -ne [Microsoft.Win32.RegistryValueKind]::ExpandString){throw 'NSSM_APPLICATION_SEED_REJECTED'}
 }finally{$parameters.Dispose()}
}
function Get-OwnedCollectorExecutorPin {
 # Integrity of the imported executor file, not operational approval. The future
 # Python boundary must independently pin exact primary bytes before invocation.
 $module=$MyInvocation.MyCommand.Module
 if($null -eq $module -or [string]::IsNullOrEmpty($module.Path)){throw 'COLLECTOR_EXECUTOR_UNAVAILABLE'}
 $stream=$null;$hash=$null;$primary=$null;$result=$null
 $cleanup=[Collections.Generic.List[Exception]]::new()
 try{
  $stream=[IO.File]::OpenRead($module.Path)
  $hash=[Security.Cryptography.SHA256]::Create()
  if($stream.Length -le 0 -or $stream.Length -gt 1048576){throw 'COLLECTOR_EXECUTOR_SIZE_REJECTED'}
  $result=([BitConverter]::ToString($hash.ComputeHash($stream))).Replace('-','').ToLowerInvariant()
 }catch{$primary=$_}
 finally{
  if($null -ne $hash){try{$hash.Dispose()}catch{$cleanup.Add($_.Exception)}}
  if($null -ne $stream){try{$stream.Dispose()}catch{$cleanup.Add($_.Exception)}}
 }
 if($cleanup.Count -gt 0){
  $failures=[Collections.Generic.List[Exception]]::new()
  if($null -ne $primary){$failures.Add($primary.Exception)}
  foreach($failure in $cleanup){$failures.Add($failure)}
  throw [AggregateException]::new('COLLECTOR_EXECUTOR_CUSTODY_UNCERTAIN',$failures.ToArray())
 }
 if($null -ne $primary){throw $primary}
 return $result
}
function ConvertTo-OwnedCollectorString([string]$Value){
 $text=[Text.StringBuilder]::new();$null=$text.Append('"')
 foreach($char in $Value.ToCharArray()){
  $n=[int]$char
  switch($n){
   8 {$null=$text.Append('\b');continue}
   9 {$null=$text.Append('\t');continue}
   10 {$null=$text.Append('\n');continue}
   12 {$null=$text.Append('\f');continue}
   13 {$null=$text.Append('\r');continue}
   34 {$null=$text.Append('\"');continue}
   92 {$null=$text.Append('\\');continue}
   default {if($n -lt 32 -or $n -gt 126){$null=$text.Append(('\u{0:x4}' -f $n))}else{$null=$text.Append($char)}}
  }
 }
 $null=$text.Append('"');return $text.ToString()
}
function ConvertTo-OwnedCollectorCanonical($Value,[string]$Omit=''){
 if($Value -is [string]){return ConvertTo-OwnedCollectorString $Value}
 if($null -eq $Value -or $Value.GetType() -ne [Management.Automation.PSCustomObject]){throw 'COLLECTOR_CANONICAL_TYPE_REJECTED'}
 [string[]]$keys=@($Value.PSObject.Properties.Name);[Array]::Sort($keys,[StringComparer]::Ordinal)
 $parts=@();foreach($key in $keys){if($key -cne $Omit){$parts+=((ConvertTo-OwnedCollectorString $key)+':'+(ConvertTo-OwnedCollectorCanonical $Value.$key))}}
 return '{'+($parts -join ',')+'}'
}
function Assert-OwnedCollectorKeys($Value,[string[]]$Fields){
 if($null -eq $Value -or $Value.GetType() -ne [Management.Automation.PSCustomObject]){throw 'COLLECTOR_CLOSED_KEYS_REQUIRED'}
 $properties=@($Value.PSObject.Properties)
 if($properties.Count -ne $Fields.Count){throw 'COLLECTOR_CLOSED_KEYS_REQUIRED'}
 foreach($property in $properties){if($property.MemberType -ne [Management.Automation.PSMemberTypes]::NoteProperty -or $property.Name -cnotin $Fields){throw 'COLLECTOR_CLOSED_KEYS_REQUIRED'}}
}
function Assert-OwnedCollectorPlan($p){
 $fields=@('schema','installation_id','node_id','computer_name','role','root','code','state','capsule_root','manifest_sha256','service_name','service_sid','nssm','nssm_sha256','python','python_sha256','bootstrap','bootstrap_sha256','entry','entry_sha256','parameters','executor_sha256','native_tools','activation','plan_sha256','collector_profile_sha256','source_manifest_sha256','collector_bootstrap_sha256','security_helper_sha256','job_helper_sha256')
 Assert-OwnedCollectorKeys $p $fields
 foreach($field in $fields){if($field -cne 'native_tools' -and ($p.$field -isnot [string] -or $p.$field.Length -gt 8192)){throw 'COLLECTOR_EXACT_STRING_REQUIRED'}}
 Assert-OwnedCollectorKeys $p.native_tools @('sc','powershell')
 foreach($tool in @($p.native_tools.sc,$p.native_tools.powershell)){
  Assert-OwnedCollectorKeys $tool @('path','sha256')
  if($tool.path -isnot [string] -or $tool.sha256 -isnot [string]){throw 'COLLECTOR_EXACT_STRING_REQUIRED'}
 }
 if($p.schema -cne 'unified.owned-collector-stopped-service.v1' -or $p.role -cne 'COLLECTOR' -or $p.activation -cne 'BLOCKED'){throw 'COLLECTOR_KIND_REJECTED'}
 foreach($field in $fields){if($field.EndsWith('_sha256',[StringComparison]::Ordinal) -and $p.$field -cnotmatch '^[a-f0-9]{64}\z'){throw 'COLLECTOR_DIGEST_REJECTED'}}
 foreach($field in @('installation_id','node_id','computer_name')){if($p.$field -cnotmatch '^[A-Za-z0-9][A-Za-z0-9_-]{0,63}\z'){throw 'COLLECTOR_LABEL_REJECTED'}}
 # Match Python _path inputs; derived code/member paths are root-bound below.
 foreach($path in @($p.root,$p.capsule_root,$p.native_tools.sc.path,$p.native_tools.powershell.path)){if($path.Length -gt 4096){throw 'COLLECTOR_PATH_REJECTED'}}
 foreach($path in @($p.root,$p.code,$p.state,$p.capsule_root,$p.nssm,$p.python,$p.bootstrap,$p.entry,$p.native_tools.sc.path,$p.native_tools.powershell.path)){
  if($path.Length -gt 8192 -or $path -cnotmatch '^[A-Za-z]:\\' -or $path -match '["\x00-\x1f]' -or [IO.Path]::GetFullPath($path) -cne $path){throw 'COLLECTOR_PATH_REJECTED'}
 }
 $code=[IO.Path]::Combine($p.root,'code')
 if($p.code -cne $code -or $p.state -cne [IO.Path]::Combine($p.root,'state') -or $p.nssm -cne [IO.Path]::Combine($code,'runtime\nssm\nssm.exe') -or $p.python -cne [IO.Path]::Combine($code,'runtime\python\python.exe') -or $p.bootstrap -cne [IO.Path]::Combine($code,'sources\unified-system\unified_system\collector_service_bootstrap.py') -or $p.entry -cne [IO.Path]::Combine($code,'sources\unified-system\unified_system\collector_service_entry.py') -or $p.parameters -cne ('-I -S -B "'+$p.entry+'"')){throw 'COLLECTOR_ROOT_BINDING_MISMATCH'}
 $comparison=[StringComparison]::OrdinalIgnoreCase
 if([string]::Equals($p.root,$p.capsule_root,$comparison) -or $p.root.StartsWith($p.capsule_root.TrimEnd('\')+'\',$comparison) -or $p.capsule_root.StartsWith($p.root.TrimEnd('\')+'\',$comparison)){throw 'COLLECTOR_ROOT_OVERLAP'}
 $pins=@{entry_sha256='3645dddef0ac6479edcc22ac61203db14fe802aa37641fa50ef2c1535f46f3cb';bootstrap_sha256='6d3be096e0df7d7633b14b55ec9d049e25b537bb530ba17f995c10a357b85005';collector_bootstrap_sha256='6d3be096e0df7d7633b14b55ec9d049e25b537bb530ba17f995c10a357b85005';security_helper_sha256='a8012a04c4a0507a72bd6ba38c63ad0af855d5f25efea7669ea11db1386d8d45';nssm_sha256='eee9c44c29c2be011f1f1e43bb8c3fca888cb81053022ec5a0060035de16d848'}
 foreach($field in $pins.Keys){if($p.$field -cne $pins[$field]){throw 'COLLECTOR_REVIEWED_PIN_MISMATCH'}}
 if($p.executor_sha256 -cne (Get-OwnedCollectorExecutorPin)){throw 'COLLECTOR_EXECUTOR_PIN_MISMATCH'}
 foreach($tool in @($p.native_tools.sc,$p.native_tools.powershell)){if($tool.sha256 -cnotmatch '^[a-f0-9]{64}\z'){throw 'COLLECTOR_DIGEST_REJECTED'}}
 $identity=[pscustomobject]@{domain=$p.schema;installation_id=$p.installation_id;node_id=$p.node_id}
 $name='UnifiedCollector_'+(Hash-OwnedText ((ConvertTo-OwnedCollectorCanonical $identity)+"`n")).Substring(0,24)
 if($p.service_name -cne $name -or $p.service_sid -cnotmatch '^S-1-5-80-(?:[0-9]+-){4}[0-9]+\z'){throw 'COLLECTOR_SERVICE_BINDING_MISMATCH'}
 if((Hash-OwnedText ((ConvertTo-OwnedCollectorCanonical $p 'plan_sha256')+"`n")) -cne $p.plan_sha256){throw 'COLLECTOR_PLAN_SEAL_MISMATCH'}
}
function Get-OwnedCollectorExpected($Plan){
 Assert-OwnedCollectorPlan $Plan
 return @{service_name=$Plan.service_name;service_sid=$Plan.service_sid;account='NT AUTHORITY\LocalService';start_type=3;sid_type=1;state=1;binary_path='"'+$Plan.nssm+'"';application=$Plan.python;parameters=$Plan.parameters;directory=$Plan.code;app_exit='Exit';marker=$Plan.plan_sha256;acl_policy='EXACT_SERVICE_SID_V1';execution_authority=$false}
}
function Invoke-OwnedCollectorService($Request){
 Assert-OwnedCollectorKeys $Request @('action','plan')
 if($Request.action -isnot [string] -or $Request.action -cnotin @('BEGIN','SEAL','REGISTER','INSPECT')){throw 'COLLECTOR_ACTION_REJECTED'}
 Assert-OwnedCollectorPlan $Request.plan
 # No real independent operational provider or new-kind phase-bound Python
 # boundary exists yet. No admin/SID/member/native/ACL command precedes this.
 # Hashes and syntactically valid plans are data, never permission to mutate.
 throw 'COLLECTOR_OPERATIONAL_ADAPTER_NOT_AVAILABLE'
}
function Invoke-UnifiedOwnedService($Request){
 $p=$Request.plan
 if($p.schema -is [string] -and $p.schema -ceq 'unified.owned-collector-stopped-service.v1'){return Invoke-OwnedCollectorService $Request}
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
   $script:NativeStage='MEMBER_PINS'
   Assert-OwnedFile $p.nssm $p.nssm_sha256;Assert-OwnedFile $p.python $p.python_sha256;Assert-OwnedFile $p.bootstrap $p.bootstrap_sha256;Assert-OwnedFile $p.entry $p.entry_sha256
   if([UnifiedStoppedServiceNative]::Exists($p.service_name)){throw 'EXISTING_RESOURCE_REJECTED'}
   $script:NativeStage='SCM_CREATE';[UnifiedStoppedServiceNative]::Create($p.service_name,$p.nssm)
   $script:NativeStage='NSSM_INITIAL_APPLICATION'
   $serviceKey=[Microsoft.Win32.Registry]::LocalMachine.OpenSubKey(('SYSTEM\CurrentControlSet\Services\'+$p.service_name),$true)
   if($null -eq $serviceKey){throw 'NEW_SERVICE_REGISTRY_UNAVAILABLE'}
   try{Write-NewOwnedNssmApplication $serviceKey $p.python}finally{$serviceKey.Dispose()}
   foreach($setting in @(@('Application',$p.python),@('AppParameters',$p.parameters),@('AppDirectory',$p.code),@('AppExit','Default','Exit'))){
    $script:NativeStage=@{Application='NSSM_SET_APPLICATION';AppParameters='NSSM_SET_PARAMETERS';AppDirectory='NSSM_SET_DIRECTORY';AppExit='NSSM_SET_APP_EXIT'}[$setting[0]]
    $null=Invoke-OwnedNative $p.nssm (@('set',$p.service_name)+$setting)
   }
   return Get-OwnedService $p
  }
  'INSPECT'{return Get-OwnedService $p}
 }
}
Export-ModuleMember -Function Invoke-UnifiedOwnedService,Get-UnifiedOwnedServiceStage,Get-UnifiedOwnedNativeExitCode
