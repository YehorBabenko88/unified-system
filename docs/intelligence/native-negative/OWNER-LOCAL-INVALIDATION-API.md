# Actual local-only principal invalidation

Separate broker source successor from31105; original1f971/Root034 evidence and
pins remain immutable. Paired Grid source is explicitly
2f94da511681811588e0f850a0a0e9dc4479c8b8, Core3dd proxy correction and fixed
local custody module5b97. No wire/schema/native13/scopes/context issuer change.

Implemented fixed SYNC method:

```python
ResearchIdentityBroker.invalidate_context_local_only(broker, context) -> None
```

Require exact actual ResearchIdentityBroker and exact ResearchPrincipalContext
in THAT broker's private inventory. Obtain its retained native SID from that
inventory; if already invalid, return None. Otherwise add SID to _invalid FIRST,
then append one bounded LOCAL audit decision. It performs ZERO awaits, authority,
client, config, peer, clock, policy/session or network operations. It deliberately
does not call _context: clock/TLS validation can fail during cleanup, and cleanup
must still latch an expired/closed-peer owned context. Unknown/foreign context
denies without changing any valid owned context.

Audit exception propagates AFTER the latch. Subsequent calls are idempotent in
invalidation state and skip duplicate audit, even after a first audit failure.
No session/capture/context inventory or tombstone is discarded. This local latch
invalidates old captures, future capture and the existing final checks of an
in-flight capture. It does not destroy/revoke/retire the actual native session,
prove remote expiry, roll back a commit, refund holds, close global state, mint
a capability/issuer/grant, or return serialized evidence. None is NOT permission
or a native-retirement receipt.

Existing async invalidate_context is unchanged and remains a distinct native
attempt path. NEVER fall back to it or bulk close through a replaced/unknown
client after custody loss. Root caller must preserve original operation error,
attach cleanup failure/UNKNOWN when appropriate, and maintain exclusive actual
authority/client/config lifecycle throughout call AND cleanup. Entry checks
alone do not prove mid-await custody. This new helper does not make concurrent
reconfiguration supported or retroactively establish past request routing.

## Actual tests

Three new actual disposable Consul/mTLS cases reuse the genuine Root-commissioned
P2 principal/profile/session source, never issued job/worker/Assignment rows:

- After an actual session and capture, rebind only the test-owned authority to
  an OWN unknown proxy-trap client. Make authority RPC/config and broker peer/
  clock access fail if touched while calling the fixed local helper twice.
  It returns None, trap0; restore ONLY the known own original client before
  fixture teardown. Old capture and future capture deny. A separate admitted
  safe fixture client reads actual native session info and proves SID STILL
  PRESENT. This is not retirement/permission. Own proxy thread/client are closed.
- An UNISSUED exact-type context lookalike without private inventory denies;
  original captures remain valid. Fill the actual bounded audit sink, observe
  audit failure AFTER latch, then idempotent repeat and invalid old capture.
  Another actual valid owned context/capture remains unaffected. No mock grant.
- An actual owned HTTP response observer reads the UNALTERED principal-session
  lock body, invokes the sync local latch at that awaited boundary, and the
  actual capture_current final check raises ResearchIdentityDenied. No capture
  returned; actual native session remains present. No response/proof is faked.

New26 exact-ID driver reruns the prior23 plus these3 on the same exact new
Unified/Grid pair; qualification/log/source closure are reported separately.
Three independent owned three-voter stands are used by the full suite, all
retained process handles retired. New3 selected owner-checkout RED790cdfee was
missing-method AttributeError; it is partial provenance, not a fresh raw-source
RED. Original failed log is preserved rather than relabelled.

Root co-ACKed this minimal API direction; A8 source/test review and exact new
Root consumer source adoption remain separate. No16/23/25 predecessor PASS or
Grid proxy2 count transfers. Windows/Linux workflow explicitly pins Grid2f94;
hosted/Linux PASS unclaimed. Resource/job/worker/publication/effect/publicsubmit
gates remain closed, production/physical NO-GO, no merge or deployment.
