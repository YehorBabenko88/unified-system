# Storage binding addendum — proposed trusted-resolved-record contract

This clarifies the d7ea091 issued-record proposal after A4's exact-byte design
review. The original13-member runtime-authority-review1 package is unchanged;
manifest727b0993ab6bf6ac0a9d226fe1465e9fb3fe6799612067a645a76fc0005bdb01.
Fresh A2/A4 API ACK remains PENDING. No storage API or publication is implemented.

## Distinct revisions

Assignment.storage.storage_budget_revision means the **issued storage budget
POLICY revision**, not current mutable usage-ledger revision or native ModifyIndex.
Changing unrelated job B's usage/debit must not change this policy revision or
invalidate unchanged job A. Publication checks current policy compatibility:
the default is exact policy revision equality; a policy change requires an explicit
A2/A4 revalidation contract before it can be accepted. No silent grandfathering.

Current usage ledger revision and native ModifyIndex are separate A4 values. A2
reads their actual current values and CASes actual byte debit in the SAME native
transaction as publication. A valid issued policy binding alone cannot authorize
an over-budget debit, extend a lease or prove object integrity.

## Reservation lifecycle: trusted resolved binding

No additional Assignment field is silently introduced into the frozen proposal.
Instead, A4 must provide this explicit alternative contract before native wiring:

* storage_reservation_id identifies ONE immutable issued grant for its entire
  retained lifetime; never reused/reissued for another scope, grant or budget.
* The issued grant binds the complete six-field scope, issuer/admitted schema,
  issued budget policy revision, storage entitlement and immutable grant digest.
  Exact issuer fields, digest preimage and record schema remain A4-owned pending.
* A separate/current lifecycle record carries its monotonic reservation_revision,
  current allowed state and any usage binding. These mutable fields cannot rewrite
  immutable issuance. Native ModifyIndex remains trusted read metadata.
* A2 resolves actual issued+lifecycle records, verifies their full binding and
  current admissibility, and includes the resolved lifecycle revision and actual
  native index in publication authorization's verified evidence/transaction checks.
  The caller cannot provide its own permission via a revision/index/path/boolean.
* Invalidation/revoke, rejoin or lifecycle transition between resolution and native
  commit makes the index/session check fail. UNKNOWN reconciles original intent;
  it does not refresh permission, allocate a new reservation or refund budget.

If A4 cannot guarantee immutable issuance under this ID, this alternative is
UNAVAILABLE: a NEW versioned Assignment schema with an explicit issued reservation
revision/digest binding must be agreed first. There is no fallback to checking
only the existence of a mutable ID or independently writing storage after a check.

## Joint transaction and tests

Publication checks current assignment/lease/epoch/fence/parent+child identity and
current reservation lifecycle/session/index, policy and usage records; writes
checkpoint/head, actual allocation/debit and immutable receipt atomically through
A2. Supersession mutates the SAME partition assignment key. A4's lifecycle/budget
checks are additional to that order, never an independent publication authority.

The existing synthetic operation ledger's storage reservation check represents a
logical dependency, not a promise that A4 can encode this in one native operation.
Separate immutable issued grant/lifecycle/policy/usage records add actual checks
unless the frozen native builder safely coalesces them. Counts26/27 are fixture
encoding measurements, NOT qualified actual native totals or production limits.

runtime-storage-binding-fixtures.py checks six deterministic semantic vectors:
unchanged policy across B usage, policy change, lifecycle invalidation, immutable
grant mutation, native index race and unknown resolution. It issues no proof and
does not call Consul or storage. Actual source/provenance/native race tests remain
mandatory before FULL_API_ACK and runtime admission. Production default UNAVAILABLE.
