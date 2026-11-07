# Callable single-node pilot composition — proposed owner seams

Scope: only single_node.py, test_agent5_single_node.py and this document, explicitly
allocated by ROOT. Continue existing PR24/worktree/base; no shared factory/API,
old contract, authority implementation, storage publication or office process edit.

Owner directive: Root189a00ed, release/directives/20261107-physical-pilot/
OWNER-DIRECTIVE.txt raw1dc4bad55cc8d65919e416b1093d7a609181bb9ee997d61031862cab70ad2bf5.
LS5 local/offline preparation only under stage gates; office quorum2/3 unchanged.
Existing Consul needs a separately admitted isolated namespace, not a second
authority or implicit single-node office quorum. Full production is not admitted.

## Implementation plan and callable surface

1. RED tests: default denial, wrong namespace/node, missing actual owner capability,
   malformed native proof, synthetic Assignment rejection, forged grant rejection,
   UNKNOWN identity retention, durable containment without current quorum.
2. Add PilotContext and SingleNodeScheduler composition of existing SchedulerRuntime
   and AttemptRegistry. Constructing it never opens a service, connection or process.
3. attach_owned_worker(worker_ref:bytes, process_proof:bytes) calls the ROOT native
   owner to resolve an already-owned worker adapter; caller cannot supply an arbitrary
   WorkerPort object. No spawn helper or SyntheticWorker import/production fallback.
4. submit/reconcile check current capabilities INSIDE each operation, including
   after durable handoff. Worker start repeats actual owner checks and forwards
   original intent/grant; the worker must verify again before execution/effects.
5. drain persists intent even when attachment/native control is unavailable; local
   pause requires actual native ownership and does not require quorum or storage
   success. No pause acknowledgement means no physical drain PASS.
6. Verify new MODEL tests separately, preserve old52 inventory/tests/CI unchanged.
   New hosted acceptance needs ROOT allocation/integration; no test count transfer.

Context is LS5, SINGLE_NODE_LOCAL_OFFLINE, registered cluster/generation/node/
parent-incarnation UUIDs and exact existing authority.config.namespace
`unified/<cluster_id>`, selected from a separately admitted local deployment.
The selector does not create/configure an authority or grant namespace admission. Context values,
readiness dictionaries, references and port presence do not prove identity or
admission. The callback contracts below are proposals needing A2/A4/ROOT ACK.

## Exact proposed dependencies (no implemented backend assumed)

ROOT admission owner: require_current_pilot(context, operation)->None must verify
current stage authorization, LS5 identity, exact release/install manifest, namespace
admission, backup/rollback/alternate admin gates and local/offline containment.
Readiness data and boolean returns cannot satisfy this guard.

A2 authority adapter PROPOSAL: execute/reconcile/verify_outcome/require_dispatch
are EXISTING A5 consumer Protocol names, NOT implemented A2 assignment backend
methods. require_single_node_capability(context, operation)->None is also NEW
and unapproved. A2 must verify the
actual isolated namespace/topology and current admitted runtime capability, then
perform grant/resource/storage checks in its sole native transaction. No local
precheck replaces publication/supersession ordering. Request codec remains the
existing request-only profile; it is never interpreted as review2 issued Assignment.
Actual issued compound grant verification/mapping must be implemented by A2.

A4 storage adapter: require_single_node_capability(context, operation)->None and
require_dispatch_reservation(context, original_command, actual_grant)->None must
verify actual issued descriptor, distinct budget/policy, current own hold and
delegation/lifecycle/accounting. This supplementary pre-start check is not commit
authorization. Atomic A2/A4 publication/debit and immutable proof remain mandatory.

ROOT native owner: attach_owned_worker(context, worker_ref, process_proof)->WorkerPort
and require_current_attachment(context, worker_ref, process_proof, worker)->None.
Opaque nonempty bytes are only inputs; owner must verify actual signed/current
process ownership, node/parent+child identity, source/release/namespace binding and
revocation. It supplies the owned adapter and revalidates each start/query/pause.
No serialized fixture proof/reference is an attestation; no caller worker injection.

All require_* methods must raise on missing/stale evidence, not return booleans.
Python method shape/None alone is not proof: only admitted owner implementations
supplied by ROOT's composition are eligible. No such actual composition is supplied
by this module. Local unit owner doubles are explicitly MODEL_ONLY and never issue
or accept an execution grant; their worker start counter must remain zero.

The wrapper also uses require_single_node_capability on the A4 adapter for current
storage-provider readiness. None-returning require_* methods are a proposed API
convention, not locally verifiable proof of genuineness: only actual source-admitted
owner implementations are eligible in ROOT's composition. The module does not
manufacture an attester, signed capability, real provider or fallback authority.

Local single_node_context recovery metadata binds the complete context including
namespace and parent incarnation. It is written only after owner attachment checks,
under the same SQLite journal transaction; it never grants authority. A different
namespace/context or legacy unscoped attempts cannot silently adopt that journal.
Restart with a new incarnation needs explicit native rejoin/reconciliation design;
no reset/migration/refund is implemented here. Unattached containment may mark a
matching unscoped local intent draining, but cannot touch an existing foreign
context or claim that any physical worker actually paused.

Callable usage by ROOT's eventual admitted composition:
`pilot = SingleNodeScheduler(context, existing_attempt_registry, admission=...,
authority=..., storage=..., native=...)`; then
`pilot.attach_owned_worker(actual_owner_reference_bytes, actual_live_proof_bytes)`.
Only after actual owners admit it may ROOT invoke submit/reconcile; drain is a
separate containment path. No example fixture/reference above enables execution.

## Missing actual gates and qualification

Currently missing: A2 exact authority-v1 API/key/proof/namespace and real grant
adapter; A4 actual issuance/current hold/delegation descriptors; ROOT native owned
worker attester/control adapter and current stage capability; installable immutable
manifest, backup/rollback and alternate administrative channel. No worker/job is
started here. Default behavior is UNAVAILABLE; unverified inputs do not become
COMMITTED authority. Existing SQLite is local intent recovery only.

Separate gates remain actual Consul transactions/quorum, native process/key/IPC,
local Storage/Control endpoints, Windows service/restart/logoff and physical pilot.
Home worker/Terminan qualification is separate; this initial composition targets
LS5 only and does not qualify PC1/LS7 or other nodes. No provider sends, security/
network/Tailscale edits, physical services, office jobs or full production admission.

## Exact owner response before freeze

ROOT: require_current_pilot and native attachment/current-attachment methods have
NO actual implementations; no API ACK or dispatch admission. None-or-raise is only
the proposed success convention. True/False, Protocol stubs, method presence,
opaque bytes and readiness references do not establish admission. Actual owners
must verify live capabilities inside operations, not cache an admission boolean.

A4: explicitly REJECTED require_single_node_capability/require_dispatch_reservation
as currently supported/admitted API signatures. They remain an UNAPPROVED candidate
in this preparation module. Exact typed context/proof/operation enum, issuer/
resolution and current lifecycle/delegation contracts must be agreed first.
Independently inspected A4 PR34 HEADcd0286dee5fc41cb7a35b0b6ac431a7ebfc25dfb:
ObjectStore.create/open/put/read/verify and backup.copy_inventory/verify_restore
exist as isolated byte primitives. Neither proposed capability method exists;
none of these byte primitives or their receipts may be cast into admission.

A2's additional capability method likewise has NO exact API ACK here. Existing
office quorum2/3 is untouched; single-node naming never waives actual topology,
session/fencing, current reservation or ROOT stage checks. Pre-start storage
observation is supplementary; actual SAME-A2-transaction hold/assignment checks
remain mandatory. Pending revalidation does not release a hold or erase original
intent. UNKNOWN never requests a new execute/start/key.

The18 single-node cases are MODEL_ONLY, with zero worker starts. Existing52 IDs,
inventory, workflow and contracts remain byte-unchanged. Hosted52 evidence cannot
be relabeled as hosted18/new native acceptance. Shared runtime integration is
BLOCKED pending actual owner implementations and exact agreement of these seams.

## A2 actual inventory correction and synchronous ABI limit

A2 evidence A5-SINGLE-NODE-A2-ACTUAL-SEAMS-REVIEW1.json raw
9e1ce799668fa5b8f074d8b2a6b02ddae56fb66d13053e64529c7c75b3e7b602
and typed response4b947551892c5b254a9dbd3bd13a9c1ff5d0050d69cddb8521e14bbf22d2eb23
were raw-read/verified. A2 explicitly REJECTED these names as an existing assignment
implementation; no runtime/source ACK. Grid acquire/renew/validate/release are
async lease primitives, CoordinationCommands research-control is metadata,
EventAuthority effect_status is UNWIRED, Mux metadata receipts are not worker
execution grants. RuntimeLayout/key/size helpers likewise do not issue grants.

This composition is synchronous. Async functions/callable objects and returned
awaitables are rejected, never treated as proof/worker/receipt/pause success.
Unstarted plain coroutines are discarded without awaiting; no asyncio.run,
background bridge, event-loop fallback or timeout-success interpretation exists.
An actual bounded owner facade or async consumer needs separate exact ABI review
and implementation; neither is allocated or provided here.
Suspended awaitables remain owner-managed: this wrapper does not cancel/close them
or execute their finally blocks as a fallback/release mechanism.

Proposed closed operation labels for owner review: ATTACH, SUBMIT, EXECUTE,
RECONCILE, RECONCILE_COMMAND, VERIFY_OUTCOME, DISPATCH. They are proposal labels,
not a published native wire enum. Historical reconciliation/verifying a receipt
checks ORIGINAL immutable intent/identity/disclosure, without current worker or
storage liveness or rebasing issuance to current indices. It never gains dispatch
permission. Current dispatch independently requires all current owners and actual
worker revalidation. New-incarnation rejoin/migration remains a separate blocked
contract; no automatic journal adoption is introduced.

The18 case IDs remain unchanged: added subchecks cover True/False, awaitables and
async-callable rejection without unawaited-coroutine warnings, exact namespace
syntax and historical reconciliation after worker proof loss/without attachment.
Missing current dispatch proof still prevents every model worker start.
