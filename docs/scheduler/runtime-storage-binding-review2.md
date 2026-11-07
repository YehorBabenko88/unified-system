# Storage binding review2 — distinct issuance budget and policy references

PROPOSED / exact A2/A4/ROOT mapping ACK pending / runtime UNAVAILABLE.
This NEW addendum supersedes review1's wording that equated storage_budget_revision
with a policy counter. Review1 SHA99c1415b36ee76a88937724cd5a8b8593f6183063c1799c4b3884ff190beb816
and all old schema/checkpoint bytes remain unchanged; no legacy backfill/alias.

Verified dependencies: A3 NEW checkpoint mapping raw
32dfe49a51e66d19a62ba2deb4dbd349ba3e3b8fd5d71c0ed11000ec2f9651be;
A4 proposed budget mapping469284063a0551e3d1f2c0c26b4b7f577ec660d4cf8527cc6b004959f593a3e4.
These are design dependencies, not an implemented producer contract.

Assignment.storage.storage_budget_revision is the immutable **issuance budget
revision**: the admitted budget/policy issuance basis of that exact reservation.
It is NOT necessarily a separately maintained policy revision, current accounting
revision, own-reservation lifecycle revision, native ModifyIndex or wall clock.
Equal decimal strings across these domains do not prove identity or compatibility.

If the actual A4 producer distinguishes issuance budget revision from policy
reference/revision, its immutable issued reservation descriptor MUST bind both
as separately named dependencies. A2 resolves and verifies both independently.
The existing Assignment field binds the issuance budget revision only. The policy
dependency can be carried by the trusted resolved descriptor; it is never guessed
from the Assignment budget counter. Without that explicit admitted descriptor,
this mapping is UNAVAILABLE. No field names for an existing runtime are asserted.

Concrete semantic golden: issuance budget revision='17', separately issued policy
reference='policy-alpha', policy revision='23', usage-ledger revision='9', own
lifecycle revision='3', native ModifyIndex=101. These are distinct counters/roles.
Unrelated B advancing usage to'10' leaves A's issued17 and policy23 unchanged.
Changing current policy to24 does not reinterpret17; it requires explicit approved
revalidation or invalidation/rejection under the current policy. Default fixture
rejects a changed policy without such a contract. Equal17/17 would not establish
that budget and policy fields were aliases either.

storage_reservation_id remains a never-reissued immutable issuance identity.
Trusted A2 resolution verifies complete cluster/generation/job/dataset/source/
partition, budget owner/node/volume incarnation, assignment/worker/attempt/lease/
fence and granted-byte bindings under A4's actual descriptor/proof schema. Current
own reservation state/lifecycle revision/index and current accounting feasibility
are separately checked; immutable issuance does not permit a revoked, released,
exhausted, foreign or superseded hold. If immutable issuance cannot be enforced,
a new explicitly issued reservation-revision/digest binding schema is required
before admission, not an existence check or silent fallback.

## Renewal continuity: issuance fence versus current delegation

The immutable descriptor's fence has the explicitly named logical role
issuance_fencing_token: historical issuance provenance, never rewritten during
renewal. A separately current lifecycle/delegation record must bind the exact
current compound fencing token. Current authority must match that current token;
the historical issuance token alone never authorizes an effect.

Pure renewal retaining the entire grant tuple/session does not require new
issuance. A nonbreaking grant_revision change may retain the reservation ONLY
under an explicitly admitted continuity transition: same complete immutable
scope/assignment revision/ID, owner/node/worker/attempt, lease ID/epoch and leader
binding, unchanged storage entitlement and issuance budget/policy dependencies;
atomically update current assignment/grant, dependent worker reservation and
current storage lifecycle/delegation token/revision in the SAME A2 transaction.
The issuance descriptor/digest stays unchanged. An uncoupled token update rejects.

Changing those immutable identity/lease/entitlement bindings requires a newly
issued reservation and explicit authority transition; no in-place descriptor
rewrite. If the producer lacks the current-delegation/continuity contract, even
a grant_revision-changing renewal requires new issuance or remains UNAVAILABLE.
No reservation is refunded/rekeyed merely because renewal outcome is UNKNOWN.
These are proposed logical roles, not claims of implemented A4 field names/API.

The SAME sole A2 transaction checks current generation/leader/native sessions,
current assignment and child proof, own hold and all closure dependencies, current
policy and accounting indexes; writes checkpoint/head/outbox, actual debit and
immutable receipt atomically. Supersession CASes the same partition assignment key.
All real records/indices come from A2 trusted reads. Additional descriptor/policy/
lifecycle/accounting records add actual operations unless safely coalesced by the
frozen native builder. A5 synthetic encoding counts are not qualified native totals.

Accounting CAS loss may require fresh current accounting/hold validation under the
SAME logical intent. UNKNOWN must reconcile original UUID/key/bytes before replay;
never substitute current counters into immutable checkpoint bytes or create a
second debit. No quorum: no new mutation or guessed commit success.

runtime-storage-binding-review2-fixtures.py checks eleven synthetic vectors including
different budget/policy values and explicit alias rejection. It is not native
authorization, receipt verification, storage publication or load acceptance.
