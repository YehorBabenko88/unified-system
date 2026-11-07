# Fail-closed authority adapter fixtures — not native integration

Base cd0286dee5fc41cb7a35b0b6ac431a7ebfc25dfb, isolated own worktree.
The three modules are an explicitly untrusted local contract harness. No actual
A2 Assignment/reservation/publication producer exists at this review point.
No endpoint, positive result/proof ABI or root admission has been approved.

`budgets.validate_reservation_binding` checks closed local fixture roles and u63
arithmetic only. It is NOT the proposed native record schema codec, cannot prove
an issued grant/lifecycle/hold, and always reports native_proof_verified=false and
publication_authorized=false. It does not equate issuance budget, policy, usage,
reservation or native-index counters. DRAINING arithmetic is not operation policy.
The native candidate record schemas remain separate proposals under review.

`PublicationAdapter` exposes proposed async commit/reconcile signatures but always
raises ACTUAL_PUBLICATION_BACKEND_UNAVAILABLE. It accepts no injected backend or
boolean. This explicitly unavailable boundary is not a supported actual A2 API.
Real binding will require a new exact reviewed producer ABI; no fake successful
callback or sync/async facade may open it.

`inspect_checkpoint_object` reads and hashes actual owned local bytes with a
32768-byte bound. It does not parse Agent 3 schema or expose a recovery cursor.
Proof-dependent recovery always rejects. Original checkpoint bytes, including
unknown exact commit-time claims, are never rewritten. No actual checkpoint
recovery, no-quorum race, supersession race or stale-writer native PASS is claimed.

RED: missing all three modules in the allocated worktree produced three import
errors before implementation. Targeted tests then cover local arithmetic churn,
revocation/exhaustion/counter rejection, denied claimed COMMITTED/quorum flags,
unavailable reconciliation and actual missing/corrupt checkpoint byte rejection.
These fixtures do not exercise Consul, office storage, providers or workers.

Preserve the frozen PR34 and Stage1 runners/inventories. On this additive fixture
branch, discover all storage tests with unittest; the previous runner's exact43
inventory is historical and deliberately not edited. Exact new inventory/source
binding must be separately published before a Draft PR acceptance claim.

P0: exact A2 typed native producer, actual authority/issuer/session/attempt proof,
A4 admitted budget-basis/issued/lifecycle/accounting/closure records, measured same
transaction contribution and recovery receipt proof. P1: real isolated native
fault tests and hosted exact source evidence. Production and physical NO-GO.
