// Read-only subject extraction prototype. NOT an authentication provider/factory.
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Security.Principal;
using System.Text;
using Microsoft.Win32.SafeHandles;

namespace Unified.OperatorAuth {
 internal sealed class SubjectRejected : Exception {
  internal readonly int? NativeStatus;
  internal SubjectRejected() : base("NATIVE_SUBJECT_REJECTED") {}
  internal SubjectRejected(int status) : base("NATIVE_SUBJECT_REJECTED") { NativeStatus = status; }
 }
 [StructLayout(LayoutKind.Sequential)] internal struct ContextHandle { internal IntPtr Lower, Upper; }
 // A reviewed native owner must hold its context lifetime/read lock throughout
 // this lease. No serialized handle, HTTP parameter or Python constructor exists.
 internal enum NativeContextOrigin { Incomplete, Outbound, InboundAcceptCompleted }
 internal interface IContextOwner {
  // Trusted owner records this only from its actual AcceptSecurityContext flow.
  // This internal seam is not an OS direction query, bearer proof or bool grant.
  NativeContextOrigin Origin { get; }
  ContextLease AcquireReadLease();
 }
 internal abstract class ContextLease : IDisposable {
  internal abstract ContextHandle Handle { get; }
  public abstract void Dispose();
 }
 internal sealed class EnrolledIssuer {
  internal readonly SecurityIdentifier SamSid;
  internal readonly Guid Generation;
  private readonly HashSet<SecurityIdentifier> humans;
  // Configuration comes from protected enrollment, never request JSON. This
  // internal value alone grants no runtime permission or trusted factory entry.
  internal EnrolledIssuer(string sam, Guid generation, IEnumerable<string> humanSids) {
   SamSid = new SecurityIdentifier(sam); Generation = generation;
   humans = new HashSet<SecurityIdentifier>();
   int count = 0;
   foreach (string sid in humanSids) { if (++count > 1024) throw new SubjectRejected(); humans.Add(new SecurityIdentifier(sid)); }
   if (generation == Guid.Empty || humans.Count == 0) throw new SubjectRejected();
  }
  internal bool HasHuman(SecurityIdentifier sid) { return humans.Contains(sid); }
 }
 internal sealed class CanonicalSubject {
  internal readonly string IssuerSamSid, UserSid;
  internal readonly Guid EnrolledGeneration;
  internal const string Qualification = "TLS_CBT_NOT_QUALIFIED";
  internal CanonicalSubject(SecurityIdentifier issuer, SecurityIdentifier user, Guid generation) {
   IssuerSamSid = issuer.Value; UserSid = user.Value; EnrolledGeneration = generation;
  }
 }
 internal static class CompletedContextSubject {
  const int NegotiateInfo = 12, TokenUser = 1, TokenGroups = 2, BufferLimit = 65536;
  [StructLayout(LayoutKind.Sequential)] struct Negotiation { internal IntPtr Package; internal uint State; }
  [StructLayout(LayoutKind.Sequential)] struct PackageInfo { internal uint Capabilities; internal ushort Version, RpcId; internal uint MaxToken; internal IntPtr Name, Comment; }
  [StructLayout(LayoutKind.Sequential)] struct SidAndAttributes { internal IntPtr Sid; internal uint Attributes; }
  [StructLayout(LayoutKind.Sequential)] struct LsaObjectAttributes { internal uint Length; internal IntPtr Root, Name; internal uint Attributes; internal IntPtr Descriptor, Quality; }
  [StructLayout(LayoutKind.Sequential)] struct LsaString { internal ushort Length, MaximumLength; internal IntPtr Buffer; }
  [StructLayout(LayoutKind.Sequential)] struct AccountDomain { internal LsaString Name; internal IntPtr Sid; }
  sealed class TokenHandle : SafeHandleZeroOrMinusOneIsInvalid {
   public TokenHandle() : base(true) {}
   protected override bool ReleaseHandle() { return CloseHandle(handle); }
  }
  sealed class PolicyHandle : SafeHandleZeroOrMinusOneIsInvalid {
   public PolicyHandle() : base(true) {}
   protected override bool ReleaseHandle() { return LsaClose(handle) == 0; }
  }
  [DllImport("secur32.dll", EntryPoint="QueryContextAttributesW")] static extern int QueryContextAttributes(ref ContextHandle context, int attribute, out Negotiation result);
  [DllImport("secur32.dll")] static extern int QuerySecurityContextToken(ref ContextHandle context, out TokenHandle token);
  [DllImport("secur32.dll")] static extern int FreeContextBuffer(IntPtr buffer);
  [DllImport("kernel32.dll", SetLastError=true)] static extern bool CloseHandle(IntPtr handle);
  [DllImport("advapi32.dll", SetLastError=true)] static extern bool GetTokenInformation(TokenHandle token, int kind, IntPtr data, uint length, out uint needed);
  [DllImport("advapi32.dll")] static extern uint LsaOpenPolicy(IntPtr system, ref LsaObjectAttributes attributes, uint access, out PolicyHandle handle);
  [DllImport("advapi32.dll")] static extern uint LsaQueryInformationPolicy(PolicyHandle handle, int kind, out IntPtr buffer);
  [DllImport("advapi32.dll")] static extern uint LsaFreeMemory(IntPtr buffer);
  [DllImport("advapi32.dll")] static extern uint LsaClose(IntPtr handle);
  [DllImport("advapi32.dll", CharSet=CharSet.Unicode, SetLastError=true)] static extern bool LookupAccountSid(string system, byte[] sid, StringBuilder name, ref uint nameLength, StringBuilder domain, ref uint domainLength, out int use);
  static void Need(bool condition) { if (!condition) throw new SubjectRejected(); }
  static SecurityIdentifier BoundedSid(IntPtr memory, uint bytes, IntPtr sid) {
   Need(bytes >= 8);
   long offset = sid.ToInt64() - memory.ToInt64(); Need(offset >= 0 && offset <= bytes - 8);
   byte revision = Marshal.ReadByte(sid), count = Marshal.ReadByte(sid, 1);
   Need(revision == 1 && count <= 15 && offset + 8 + count * 4 <= bytes);
   return new SecurityIdentifier(sid);
  }
  static T ReadToken<T>(TokenHandle token, int kind, Func<IntPtr,uint,T> read) {
   uint needed; bool initial = GetTokenInformation(token, kind, IntPtr.Zero, 0, out needed);
   Need(!initial && Marshal.GetLastWin32Error() == 122 && needed >= IntPtr.Size && needed <= BufferLimit);
   IntPtr data = Marshal.AllocHGlobal((int)needed);
   try { uint actual; Need(GetTokenInformation(token, kind, data, needed, out actual) && actual <= needed && actual >= IntPtr.Size); return read(data, actual); }
   finally { Marshal.FreeHGlobal(data); }
  }
  static SecurityIdentifier LocalSam() {
   PolicyHandle policy; var attributes = new LsaObjectAttributes(); attributes.Length = (uint)Marshal.SizeOf(attributes);
   uint status = LsaOpenPolicy(IntPtr.Zero, ref attributes, 1, out policy);
   using (policy) {
    Need(status == 0 && policy != null && !policy.IsInvalid); IntPtr data = IntPtr.Zero;
    try { Need(LsaQueryInformationPolicy(policy, 5, out data) == 0 && data != IntPtr.Zero); var domain = (AccountDomain)Marshal.PtrToStructure(data, typeof(AccountDomain)); Need(domain.Sid != IntPtr.Zero); return new SecurityIdentifier(domain.Sid); }
    finally { if (data != IntPtr.Zero) LsaFreeMemory(data); }
   }
  }
  static void RequireUserAccount(SecurityIdentifier user) {
   byte[] sid = new byte[user.BinaryLength]; user.GetBinaryForm(sid, 0);
   uint names = 0, domains = 0; int use;
   bool initial = LookupAccountSid(null, sid, null, ref names, null, ref domains, out use);
   Need(!initial && Marshal.GetLastWin32Error() == 122 && names > 0 && names <= 256 && domains > 0 && domains <= 256);
   var name = new StringBuilder((int)names); var domain = new StringBuilder((int)domains);
   Need(LookupAccountSid(null, sid, name, ref names, domain, ref domains, out use) && use == 1 && !name.ToString().EndsWith("$", StringComparison.Ordinal));
  }
  internal static CanonicalSubject InspectCompletedContext(IContextOwner owner, EnrolledIssuer enrollment) {
   Need(owner != null && enrollment != null);
   Need(owner.Origin == NativeContextOrigin.InboundAcceptCompleted);
   using (ContextLease lease = owner.AcquireReadLease()) {
    Need(lease != null); ContextHandle context = lease.Handle;
    Need(context.Lower != IntPtr.Zero || context.Upper != IntPtr.Zero);
    Negotiation negotiation; int status = QueryContextAttributes(ref context, NegotiateInfo, out negotiation);
    try {
     if (status != 0) throw new SubjectRejected(status);
     Need(negotiation.State == 0 && negotiation.Package != IntPtr.Zero);
     var package = (PackageInfo)Marshal.PtrToStructure(negotiation.Package, typeof(PackageInfo));
     Need(package.Name != IntPtr.Zero && String.Equals(Marshal.PtrToStringUni(package.Name), "NTLM", StringComparison.Ordinal));
    } finally { if (status == 0 && negotiation.Package != IntPtr.Zero) FreeContextBuffer(negotiation.Package); }
    TokenHandle token; status = QuerySecurityContextToken(ref context, out token);
    using (token) {
     Need(status == 0 && token != null && !token.IsInvalid);
     SecurityIdentifier issuer = LocalSam(); Need(issuer.Equals(enrollment.SamSid));
     SecurityIdentifier user = ReadToken(token, TokenUser, (memory, bytes) => BoundedSid(memory, bytes, Marshal.ReadIntPtr(memory)));
     Need(user.AccountDomainSid != null && user.AccountDomainSid.Equals(issuer));
     Need(!user.Equals(new SecurityIdentifier(issuer.Value + "-501")));
     RequireUserAccount(user); Need(enrollment.HasHuman(user));
     ReadToken(token, TokenGroups, (memory, bytes) => {
      uint count = unchecked((uint)Marshal.ReadInt32(memory)); int first = IntPtr.Size == 8 ? 8 : 4, size = Marshal.SizeOf(typeof(SidAndAttributes));
      Need(count <= 1024 && first + (long)count * size <= bytes);
      for (uint i = 0; i < count; i++) {
       var group = (SidAndAttributes)Marshal.PtrToStructure(IntPtr.Add(memory, first + (int)i * size), typeof(SidAndAttributes));
       SecurityIdentifier sid = BoundedSid(memory, bytes, group.Sid);
       Need(!sid.IsWellKnown(WellKnownSidType.ServiceSid) && !sid.IsWellKnown(WellKnownSidType.AnonymousSid));
      }
      return true;
     });
     GC.KeepAlive(owner);
     return new CanonicalSubject(issuer, user, enrollment.Generation);
    }
   }
  }
 }
}
