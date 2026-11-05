// Hosted negative-only executable. No users, credentials, certificates or network.
using System;
using System.Collections.Generic;
namespace Unified.OperatorAuth {
 internal sealed class NegativeOwner : IContextOwner {
  internal bool Disposed;
  internal bool Acquired;
  internal NativeContextOrigin origin = NativeContextOrigin.InboundAcceptCompleted;
  public NativeContextOrigin Origin { get { return origin; } }
  readonly ContextHandle handle;
  internal NegativeOwner(bool nativeInvalid) { handle = nativeInvalid ? new ContextHandle { Lower = new IntPtr(-1), Upper = new IntPtr(-1) } : new ContextHandle(); }
  sealed class Lease : ContextLease {
   readonly NegativeOwner owner;
   internal Lease(NegativeOwner value) { owner = value; }
   internal override ContextHandle Handle { get { return owner.handle; } }
   public override void Dispose() { owner.Disposed = true; }
  }
  public ContextLease AcquireReadLease() { Acquired = true; return new Lease(this); }
 }
 internal static class NegativeQualification {
  static SubjectRejected Rejected(Action action) { try { action(); } catch (SubjectRejected error) { return error; } throw new Exception("NEGATIVE_CASE_ADMITTED"); }
  public static int Main() {
   try {
    var executed = new List<string>();
    var enrolled = new EnrolledIssuer("S-1-5-21-1-2-3", new Guid("00000000-0000-0000-0000-000000000007"), new [] {"S-1-5-21-1-2-3-1001"});
    Rejected(() => CompletedContextSubject.InspectCompletedContext(null, enrolled));
    executed.Add("ABSENT_OWNER");
    var outbound = new NegativeOwner(true); outbound.origin = NativeContextOrigin.Outbound;
    Rejected(() => CompletedContextSubject.InspectCompletedContext(outbound, enrolled));
    if (outbound.Acquired) throw new Exception("OUTBOUND_LEASE_ADMITTED");
    executed.Add("OUTBOUND_OWNER");
    foreach (bool nativeInvalid in new [] {false,true}) {
     var owner = new NegativeOwner(nativeInvalid);
     SubjectRejected error = Rejected(() => CompletedContextSubject.InspectCompletedContext(owner, enrolled));
     if (!owner.Acquired || !owner.Disposed) throw new Exception("LEASE_NOT_RELEASED");
     if (nativeInvalid && error.NativeStatus != unchecked((int)0x80090301)) throw new Exception("NATIVE_INVALID_HANDLE_NOT_OBSERVED");
     executed.Add(nativeInvalid ? "NATIVE_INVALID_CONTEXT" : "EMPTY_CONTEXT");
    }
    Rejected(() => new EnrolledIssuer("S-1-5-21-1-2-3", Guid.Empty, new [] {"S-1-5-21-1-2-3-1001"}));
    executed.Add("EMPTY_GENERATION");
    string inventory = "[\"" + String.Join("\",\"", executed.ToArray()) + "\"]";
    Console.WriteLine("{\"schema\":\"unified.native-subject-negative.v1\",\"compile\":\"PASS\",\"invalid_context\":\"REJECTED\",\"subject_extraction_positive\":\"NOT_RUN\",\"tls_cbt\":\"NOT_QUALIFIED\",\"runtime_factory\":\"DENY\",\"authentication\":\"NOT_QUALIFIED\",\"negative_cases\":"+inventory+",\"native_invalid_handle_observed\":true}");
    return 0;
   } catch { Console.Error.WriteLine("NATIVE_SUBJECT_NEGATIVE_QUALIFICATION_FAILED"); return 1; }
  }
 }
}
