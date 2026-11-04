# Separate APP_ONLY backend. No stop/start/ACL/adoption operation.
# https://learn.microsoft.com/windows/win32/api/winsvc/nf-winsvc-deleteservice
# DeleteService marks only; actual absence is checked after closing our handle.
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$script:Native=@'
using System;
using System.Runtime.InteropServices;
public static class UnifiedOwnedRemovalNative {
 public sealed class Snapshot {public string Binary,Account;public uint Type,Start,Error,Sid,State;}
 public interface Kernel {IntPtr Open(string name);Snapshot Read(IntPtr handle);void Delete(IntPtr handle);void Close(IntPtr handle);string Observe(string name);}
 static void Need(bool ok){if(!ok)throw new InvalidOperationException("OWNED_REMOVAL_REJECTED");}
 public static void Validate(Snapshot s,string binary){Need(s!=null&&s.Type==16&&s.Start==3&&s.Error==1&&s.Sid==1&&s.State==1&&s.Binary=="\""+binary+"\""&&String.Equals(s.Account,"NT AUTHORITY\\LocalService",StringComparison.OrdinalIgnoreCase));}
 public static string RemoveUsing(Kernel kernel,string name,string binary,Action extra){
  IntPtr handle=kernel.Open(name);Need(handle!=IntPtr.Zero);
  try{Validate(kernel.Read(handle),binary);extra();Validate(kernel.Read(handle),binary);kernel.Delete(handle);}finally{kernel.Close(handle);}
  var clock=System.Diagnostics.Stopwatch.StartNew();string value;
  do{value=kernel.Observe(name);Need(value=="ABSENT"||value=="MARKED_PENDING"||value=="PRESENT_REVIEW_REQUIRED");if(value!="MARKED_PENDING")return value;System.Threading.Thread.Sleep(50);}while(clock.ElapsedMilliseconds<5000);
  return "MARKED_PENDING";
 }
 public static string Remove(string name,string binary,Action extra){return RemoveUsing(new NativeKernel(),name,binary,extra);}
 public static string Observe(string name){return new NativeKernel().Observe(name);}
 [StructLayout(LayoutKind.Sequential)] struct CONFIG {public uint type,start,error;public IntPtr binary,group;public uint tag;public IntPtr dependencies,account,display;}
 [StructLayout(LayoutKind.Sequential)] struct STATUS {public uint type,state,controls,winerror,specific,checkpoint,hint;}
 [DllImport("advapi32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern IntPtr OpenSCManagerW(string machine,string database,uint access);
 [DllImport("advapi32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern IntPtr OpenServiceW(IntPtr manager,string name,uint access);
 [DllImport("advapi32.dll",SetLastError=true)] static extern bool CloseServiceHandle(IntPtr handle);
 [DllImport("advapi32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern bool QueryServiceConfigW(IntPtr handle,IntPtr buffer,uint size,out uint needed);
 [DllImport("advapi32.dll",SetLastError=true)] static extern bool QueryServiceConfig2W(IntPtr handle,uint kind,IntPtr buffer,uint size,out uint needed);
 [DllImport("advapi32.dll",SetLastError=true)] static extern bool QueryServiceStatus(IntPtr handle,out STATUS status);
 [DllImport("advapi32.dll",SetLastError=true)] static extern bool DeleteService(IntPtr handle);
 static string Text(IntPtr pointer,IntPtr buffer,uint length){long offset=pointer.ToInt64()-buffer.ToInt64();Need(pointer!=IntPtr.Zero&&offset>=0&&offset+2<=length&&(offset&1)==0);int count=0;while(offset+2*count+2<=length){if(Marshal.ReadInt16(pointer,2*count)==0)return Marshal.PtrToStringUni(pointer,count);count++;}throw new InvalidOperationException("SCM_TEXT_BOUNDS");}
 sealed class NativeKernel:Kernel {
  public IntPtr Open(string name){IntPtr manager=OpenSCManagerW(null,null,1);Need(manager!=IntPtr.Zero);try{IntPtr h=OpenServiceW(manager,name,0x10005);Need(h!=IntPtr.Zero);return h;}finally{Need(CloseServiceHandle(manager));}}
  public Snapshot Read(IntPtr handle){IntPtr buffer=IntPtr.Zero,sid=IntPtr.Zero;try{uint size;bool first=QueryServiceConfigW(handle,IntPtr.Zero,0,out size);Need(!first&&Marshal.GetLastWin32Error()==122&&size>=Marshal.SizeOf(typeof(CONFIG))&&size<=8192);buffer=Marshal.AllocHGlobal((int)size);uint actual;Need(QueryServiceConfigW(handle,buffer,size,out actual)&&actual<=size);CONFIG c=(CONFIG)Marshal.PtrToStructure(buffer,typeof(CONFIG));sid=Marshal.AllocHGlobal(4);uint needed;Need(QueryServiceConfig2W(handle,5,sid,4,out needed)&&needed==4);STATUS status;Need(QueryServiceStatus(handle,out status));return new Snapshot {Binary=Text(c.binary,buffer,size),Account=Text(c.account,buffer,size),Type=c.type,Start=c.start,Error=c.error,Sid=(uint)Marshal.ReadInt32(sid),State=status.state};}finally{if(buffer!=IntPtr.Zero)Marshal.FreeHGlobal(buffer);if(sid!=IntPtr.Zero)Marshal.FreeHGlobal(sid);}}
  public void Delete(IntPtr handle){if(!DeleteService(handle))Need(Marshal.GetLastWin32Error()==1072);}
  public void Close(IntPtr handle){Need(CloseServiceHandle(handle));}
  public string Observe(string name){IntPtr manager=OpenSCManagerW(null,null,1);Need(manager!=IntPtr.Zero);try{IntPtr h=OpenServiceW(manager,name,4);if(h!=IntPtr.Zero){Need(CloseServiceHandle(h));return "PRESENT_REVIEW_REQUIRED";}int error=Marshal.GetLastWin32Error();Need(error==1060||error==1072);return error==1060?"ABSENT":"MARKED_PENDING";}finally{Need(CloseServiceHandle(manager));}}
 }
}
'@
function Invoke-UnifiedOwnedServiceRemoval($Request){
 if(-not [String]::Equals([Environment]::MachineName,[string]$Request.plan.computer_name,[StringComparison]::OrdinalIgnoreCase)){throw 'COMPUTER_BINDING_MISMATCH'}
 $id=[Security.Principal.WindowsIdentity]::GetCurrent()
 if(-not ([Security.Principal.WindowsPrincipal]::new($id)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){throw 'ELEVATED_OWNER_SESSION_REQUIRED'}
 if(-not ('UnifiedOwnedRemovalNative' -as [type])){Add-Type -TypeDefinition $script:Native}
 $p=$Request.plan;$expected=$Request.proof
 if($Request.action -cnotin @('REMOVE_SERVICE','OBSERVE_SERVICE') -or $p.schema -cne 'unified.owned-stopped-service.v1' -or $p.activation -cne 'BLOCKED' -or $p.service_name -cnotmatch '^UnifiedLab_[a-f0-9]{24}$' -or $p.plan_sha256 -cnotmatch '^[a-f0-9]{64}$'){throw 'CLOSED_REMOVAL_REQUEST_REQUIRED'}
 if($Request.action -ceq 'OBSERVE_SERVICE'){return @{service=[UnifiedOwnedRemovalNative]::Observe($p.service_name)}}
 # The original service module is hash-pinned by the Python adapter. INSPECT is
 # read-only, and our already-open removal handle pins the service object.
 Import-Module -Name ([WildcardPattern]::Escape($env:UNIFIED_SERVICE_MODULE)) -Force
 $verify=[Action]{
  $live=Invoke-UnifiedOwnedService @{action='INSPECT';plan=$p}
  $fields=@($expected.PSObject.Properties.Name)
  if($live.Count -ne $fields.Count){throw 'RECORDED_PROOF_FIELDS_MISMATCH'}
  foreach($field in $fields){if(-not $live.ContainsKey($field) -or $live[$field] -cne $expected.$field){throw 'RECORDED_LIVE_PROOF_MISMATCH'}}
 }
 $result=[UnifiedOwnedRemovalNative]::Remove($p.service_name,$p.nssm,$verify)
 return @{service=$result}
}
Export-ModuleMember -Function Invoke-UnifiedOwnedServiceRemoval
