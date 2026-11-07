param(
    [switch]$Client,
    [ValidatePattern('^UnifiedIdentityLab-[0-9a-f]{32}$')][string]$PipeName,
    [ValidateSet('Identification','Anonymous','Impersonation')][string]$ClientLevel='Identification',
    [switch]$WrongPid
)
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
# Disposable same-account fixture. No service, credentials, privilege adjustment,
# policy change, trust store, network socket or production identity factory.
Add-Type -TypeDefinition @'
using System;
using System.Diagnostics;
using System.IO;
using System.IO.Pipes;
using System.Runtime.InteropServices;
using System.Security.Principal;
using System.Security.Cryptography;
using System.Text;
using Microsoft.Win32.SafeHandles;

public static class UnifiedPipeLab {
    [StructLayout(LayoutKind.Sequential)] struct SA {
        public int length; public IntPtr descriptor; public int inherit;
    }
    [StructLayout(LayoutKind.Sequential)] struct LUID {
        public uint low; public int high;
        public string Hex() { return unchecked((uint)high).ToString("x8")+low.ToString("x8"); }
    }
    [StructLayout(LayoutKind.Sequential)] struct STATS {
        public LUID token, authentication; public long expiration;
        public int type, level; public uint charged, available, groups, privileges; public LUID modified;
    }
    [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)]
    static extern IntPtr CreateNamedPipeW(string name,uint mode,uint pipeMode,uint max,
        uint output,uint input,uint timeout,ref SA security);
    [DllImport("advapi32.dll",CharSet=CharSet.Unicode,SetLastError=true)]
    static extern bool ConvertStringSecurityDescriptorToSecurityDescriptorW(string text,
        uint revision,out IntPtr descriptor,out uint size);
    [DllImport("advapi32.dll",SetLastError=true)] static extern bool ImpersonateNamedPipeClient(IntPtr pipe);
    [DllImport("advapi32.dll",SetLastError=true)] static extern bool RevertToSelf();
    [DllImport("advapi32.dll",SetLastError=true)] static extern bool OpenThreadToken(IntPtr thread,uint access,bool self,out IntPtr token);
    [DllImport("advapi32.dll",SetLastError=true)] static extern bool GetTokenInformation(IntPtr token,int kind,IntPtr data,int size,out int needed);
    [DllImport("kernel32.dll")] static extern IntPtr GetCurrentThread();
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool GetNamedPipeClientProcessId(IntPtr pipe,out uint pid);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool GetNamedPipeClientSessionId(IntPtr pipe,out uint session);
    [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr handle);
    [DllImport("kernel32.dll")] static extern IntPtr LocalFree(IntPtr memory);

    public sealed class Result {
        public string status, reason, sid_sha256, native_logon_id;
        public int impersonation_level;
        public uint kernel_client_pid, expected_client_pid;
        public bool restored_server_identity, client_pid_matches_owned_child,
            observer_is_administrator, owned_child_stopped, runtime_admission=false;
    }
    static Exception Deny(string reason) { return new InvalidOperationException(reason); }
    static void Need(bool condition,string reason) { if(!condition)throw Deny(reason); }
    static string Hash(string value) {
        using(var hash=SHA256.Create())return BitConverter.ToString(hash.ComputeHash(Encoding.ASCII.GetBytes(value))).Replace("-","").ToLowerInvariant();
    }
    static IntPtr TokenData(IntPtr token,int kind) {
        int size;GetTokenInformation(token,kind,IntPtr.Zero,0,out size);
        Need(size>0&&size<=65536,"TOKEN_SIZE_REJECTED");
        IntPtr data=Marshal.AllocHGlobal(size);
        if(!GetTokenInformation(token,kind,data,size,out size)){Marshal.FreeHGlobal(data);throw Deny("TOKEN_READ_REJECTED");}
        return data;
    }
    public static void ClientRun(string name,string level) {
        var mode=(TokenImpersonationLevel)Enum.Parse(typeof(TokenImpersonationLevel),level);
        using(var pipe=new NamedPipeClientStream(".",name,PipeDirection.InOut,PipeOptions.None,mode)) {
            pipe.Connect(8000);byte[] message=Encoding.ASCII.GetBytes("USI1");
            pipe.Write(message,0,message.Length);pipe.Flush();
            Need(pipe.ReadByte()==1,"SERVER_ACK_REJECTED");
        }
    }
    public static Result Run(string script,string powershell,string level,bool wrongPid) {
        var result=new Result();Process child=null;NamedPipeServerStream pipe=null;
        IntPtr descriptor=IntPtr.Zero;
        string ownSid;
        using(var identity=WindowsIdentity.GetCurrent()) {
            ownSid=identity.User.Value;
            result.observer_is_administrator=new WindowsPrincipal(identity).IsInRole(WindowsBuiltInRole.Administrator);
        }
        try {
            Need(!result.observer_is_administrator,"UNPRIVILEGED_OBSERVER_REQUIRED");
            // This test creates ONLY a new private ephemeral pipe DACL.
            // It never changes an existing pipe, OS policy, account or privilege.
            uint descriptorSize;
            Need(ConvertStringSecurityDescriptorToSecurityDescriptorW("D:P(A;;GA;;;"+ownSid+")",1,out descriptor,out descriptorSize),"DACL_REJECTED");
            var sa=new SA {length=Marshal.SizeOf(typeof(SA)),descriptor=descriptor,inherit=0};
            string name="UnifiedIdentityLab-"+Guid.NewGuid().ToString("N");
            // FIRST_PIPE_INSTANCE | OVERLAPPED; message mode | REJECT_REMOTE_CLIENTS.
            IntPtr handle=CreateNamedPipeW(@"\\.\pipe\"+name,3|0x00080000|0x40000000,2|4|8,1,4096,4096,0,ref sa);
            Need(handle!=new IntPtr(-1),"PIPE_CREATE_REJECTED");
            var safe=new SafePipeHandle(handle,true);
            try {pipe=new NamedPipeServerStream(PipeDirection.InOut,true,false,safe);}
            catch {safe.Dispose();throw;}
            var start=new ProcessStartInfo(powershell,
                "-NoLogo -NoProfile -NonInteractive -File \""+script+"\" -Client -PipeName "+name+" -ClientLevel "+level);
            start.UseShellExecute=false;start.CreateNoWindow=true;
            child=Process.Start(start);Need(child!=null,"CHILD_START_REJECTED");
            Need(pipe.WaitForConnectionAsync().Wait(8000),"PIPE_CONNECT_TIMEOUT");
            byte[] bytes=new byte[4];int offset=0;
            while(offset<4) {
                var read=pipe.ReadAsync(bytes,offset,4-offset);Need(read.Wait(8000),"PIPE_READ_TIMEOUT");
                Need(read.Result>0,"PIPE_CLOSED");offset+=read.Result;
            }
            Need(Encoding.ASCII.GetString(bytes)=="USI1","HANDSHAKE_REJECTED");
            uint pid,session;
            Need(GetNamedPipeClientProcessId(handle,out pid),"CLIENT_PID_UNAVAILABLE");
            // The negative case compares the REAL kernel client PID with the
            // still-live parent PID, not an unconditional false predicate.
            uint expectedPid=wrongPid?(uint)Process.GetCurrentProcess().Id:(uint)child.Id;
            result.kernel_client_pid=pid;result.expected_client_pid=expectedPid;
            result.client_pid_matches_owned_child=pid==(uint)child.Id;
            Need(pid==expectedPid,"CLIENT_PID_MISMATCH");
            Need(GetNamedPipeClientSessionId(handle,out session),"CLIENT_SESSION_UNAVAILABLE");
            IntPtr token;
            if(OpenThreadToken(GetCurrentThread(),8,true,out token)) {
                CloseHandle(token);throw Deny("SERVER_ALREADY_IMPERSONATING");
            }
            Need(Marshal.GetLastWin32Error()==1008,"SERVER_TOKEN_STATE_REJECTED");
            Need(ImpersonateNamedPipeClient(handle),"IMPERSONATION_REJECTED");
            try {
                if(!OpenThreadToken(GetCurrentThread(),8,true,out token)) {
                    if(Marshal.GetLastWin32Error()==1347)throw Deny("IDENTIFICATION_LEVEL_REQUIRED");
                    throw Deny("CLIENT_TOKEN_UNAVAILABLE");
                }
                try {
                    IntPtr data=TokenData(token,9);
                    try {result.impersonation_level=Marshal.ReadInt32(data);}
                    finally {Marshal.FreeHGlobal(data);}
                    Need(result.impersonation_level==1,"IDENTIFICATION_LEVEL_REQUIRED");
                    data=TokenData(token,1);
                    string sid;
                    try {sid=new SecurityIdentifier(Marshal.ReadIntPtr(data)).Value;}
                    finally {Marshal.FreeHGlobal(data);}
                    Need(sid==ownSid,"SAME_ACCOUNT_FIXTURE_MISMATCH");
                    result.sid_sha256=Hash(sid);
                    data=TokenData(token,10);
                    try {result.native_logon_id=((STATS)Marshal.PtrToStructure(data,typeof(STATS))).authentication.Hex();}
                    finally {Marshal.FreeHGlobal(data);}
                } finally {CloseHandle(token);}
            } finally {
                // Continuing under an un-reverted identity is forbidden.
                if(!RevertToSelf())Environment.FailFast("REVERT_TO_SELF_FAILED");
            }
            using(var identity=WindowsIdentity.GetCurrent())result.restored_server_identity=identity.User.Value==ownSid;
            Need(result.restored_server_identity,"SERVER_IDENTITY_NOT_RESTORED");
            pipe.WriteByte(1);pipe.Flush();
            Need(child.WaitForExit(8000)&&child.ExitCode==0,"CLIENT_EXIT_REJECTED");
            result.status="OBSERVED_NATIVE_IDENTIFICATION_ONLY";
        } catch(Exception error) {
            result.status="REJECTED";result.reason=error.GetBaseException().Message;
        } finally {
            // Observe cleanup after BOTH positive and negative outcomes. A false
            // default field is not evidence that RevertToSelf failed or ran.
            IntPtr residual;
            bool stillImpersonating=OpenThreadToken(GetCurrentThread(),8,true,out residual);
            int tokenError=Marshal.GetLastWin32Error();
            if(stillImpersonating)CloseHandle(residual);
            using(var identity=WindowsIdentity.GetCurrent())
                result.restored_server_identity=!stillImpersonating&&tokenError==1008&&identity.User.Value==ownSid;
            if(!result.restored_server_identity)Environment.FailFast("SERVER_IDENTITY_CLEANUP_NOT_CONFIRMED");
            if(pipe!=null)pipe.Dispose();
            if(descriptor!=IntPtr.Zero)LocalFree(descriptor);
            if(child!=null) {
                try {if(!child.WaitForExit(3000)){child.Kill();Need(child.WaitForExit(3000),"OWN_CHILD_CLEANUP_FAILED");}
                    result.owned_child_stopped=child.HasExited;
                } finally {child.Dispose();}
            }
        }
        return result;
    }
}
'@ -ReferencedAssemblies @('System.dll','System.Core.dll','System.Security.dll')
if($Client){[UnifiedPipeLab]::ClientRun($PipeName,$ClientLevel);exit 0}
$result=[UnifiedPipeLab]::Run($PSCommandPath,(Join-Path $PSHOME 'powershell.exe'),$ClientLevel,$WrongPid.IsPresent)
$result|ConvertTo-Json -Compress
if($result.status -ne 'OBSERVED_NATIVE_IDENTIFICATION_ONLY'){exit 2}
exit 0
