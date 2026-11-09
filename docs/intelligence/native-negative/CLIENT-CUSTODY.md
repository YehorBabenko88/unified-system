# Isolated negative Gateway client custody

This is an explicit source successor, not an upgrade of Root034/Grid539 evidence.
It pins Grid2792f94/Core3dd/assignment5b97 and imports the exact A2 broker327
file481724 (local-only nonissuing invalidation). No new broker or authority.

The actual fixed Core constructor disables ambient proxy routing. Gateway entry
requires the actual owned open AsyncClient, trust_env=False, no redirects,
ordinary default transport and no mounts. The same client/config identities are
required before authentication and native cleanup. These checks are not a Root
credential, worker/resource proof or boundary against hostile Python mutation.

The caller must exclusively own the borrowed authority/client/config lifecycle
throughout the call AND cleanup. No concurrent rebind/reconfigure/close is
supported; shutdown waits for cleanup. Entry checks do not protect every native
await against concurrent mutation. A fault test replaces a client only at a
controlled error-return boundary after a real unmodified native read.

If custody is lost, call only the fixed synchronous local invalidation API.
Never use a replaced client for cleanup or fall back to bulk close. Preserve
the original operation error with explicit native-cleanup UNKNOWN. The local
SID latch precedes audit, retains tombstones and is not a server-retirement
receipt. A separate safe fixture read shows that the native SID still exists.

Normal healthy cleanup retains the prior bounded native best-effort API. Its
return is not a strong retirement receipt. Core authentication mutation retry
semantics are unchanged: ambiguous creation can leave UNKNOWN SID custody.
No exactly-once auth or automatic orphan adoption/rollback is claimed.

All prior16 cases remain mandatory plus four entry-custody negatives and one
actual lost-custody cleanup case. The test proxy is own loopback, counts requests
only, retains no headers/tokens/bodies, and its owned server thread is joined.
The direct target runtime and all145 mandatory CI component cases are preserved.
Hosted/A8 acceptance of this NEW source is separate. No admitted jobs, quota,
worker resources, committed result publication or authenticated scientific view.
Public submit DENY; physical/production/provider sends remain blocked.
