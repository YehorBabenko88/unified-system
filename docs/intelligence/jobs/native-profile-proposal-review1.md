# Minimal actual synthetic research profile — joint proposal review1

PROPOSED; requires exact ROOT/A2/A4/A7 ACK. Not runtime admission.
A5 owns composition only. Existing three-voter disposable Consul is the ONLY
consensus/authority. No standalone job ledger, fake lease issuer or boolean cap.

## Existing source primitives and permitted reuse boundary

Source inspected at Grid40e9c8dc274a2746018bc1aa08d103cd0187cecc:
- grid/coordination.py ConsulSessionAuthority.acquire/validate/renew/release:
  actual session/create, KV acquire, consistent captured leader index and TTL
  deadline. Reuse actual same-instance handle in A2 fixture, never reconstruct.
- grid/coordination_commands.py CoordinationCommands.submit/get_command:
  existing guarded original-command/idempotency/receipt pattern. Reuse its
  approved generation/principal/CAS ordering concept inside A2 owner, not claim
  its old operation codec supports research or alias its existing receipts.
- grid/coordination_event_v3.py EventAuthority.prepare_session/submit:
  actual eventordered GRANT/RENEW/REVOKE/COMPLETE and session/index transactions.
  Frozen lifecycle.v3 is NOT complete resource/storage Assignment v1. It cannot
  be called a research grant merely because it can write an assignment-shaped
  record; exact migration/composition is an A2 decision.
- authority_runtime_v1.py RuntimeLayout and measure_native_plan: exact native
  key derivation and bounded transaction measurement, not issuance.
- authority_assignment_v1.py private _read/_leader_fence/_transaction provide
  captured consistent read, actual generation+leader check-session/check-index,
  bounded native Txn. Public execute/reconcile explicitly CLOSED. They are not
  public arbitrary KV access; A5 will never build/send raw authority operations.

## Narrow vertical scope

ONE immutable engineering-only synthetic OHLCV input, one request/job/child,
one actual A7 meta.ohlcv.untouched_levels.v1 computation using pinned pure Meta
f3c01a23fa5baaeeeb28eb8e9397e72b5ef4d5a1/treec155c935a801fa98b7c78219c9798ce1f1be8848.
No training/native Math bootstrap/orders/financial claims. A7 review1 request
and result are a separate explicit codec, not the old local Math-labeled plan.
Rows1..256/request128KiB/output1MiB are A7 proposed bounds; actual process CPU/
memory/latency/output measurements and containment must qualify them. A5 public
limits cannot be declared load-validated by these numbers alone.

ROOT provisions real disposable identities, current native policy/ACLs and
measured node observations through owner issuers. Synthetic DATA is permitted;
synthetic identity/lease/storage proof is not. Read-only capability cannot grant
SUBMIT_RESEARCH. No manual fixture-seeding of fake issued records as authority.

## Required owner mutations and exact transition plan

1. ROOT/A2: actual research principal+quota policy and provider. A2 persists
   full original submit intent/globalUUID/idempotency under existing command
   authority and checks captured current identities/policy in native transaction.
   All raw operation codecs/results and actor/quota mapping need exact approval.
2. A5 plans one placement from actual fresh observations and requested resources.
   A2 implements the missing ASSIGN issuer: actual node/incarnation/child-attempt,
   capacity/resource ledger holds and current storage reservation binding, monotonic
   assignment revision distinct from lease epoch, immutable issued records and
   original receipt in one bounded transaction. A4 supplies actual scoped holds.
3. A2 implements missing current DISPATCH verification/owner-only proof over
   assignment/session/epoch/revision/attempt/freshness/holds and original command.
   A5 contains verified owned disposable child, never invokes a research callback
   solely because it is callable or a read cap returned non-None.
4. A7 implements exact pinned execute_synthetic_research with strict bool cancel
   observation before/after bounded Meta call. After-return cancellation is still
   guarded at commit. It returns raw artifact+digest, no registry receipt.
5. A7 supplies exact existing result_persistence.persist_report_fenced and
   provenance.execute_owned/ReadOnlyResultsApp candidate source. Actual owned
   store.stage/promote, lease verifier and experiment identity binding are NONE
   until qualified; these are NOT existing A4 APIs. A4 explicitly has NO admitted
   result/experiment registry or promote API. ObjectStore.put/local copy/codec
   is not fenced result publication. No replacement registry. A2 implements actual
   result publication authorization with all eligible closure/hold/debit checks,
   original command/receipt and same assignment/cancellation order. A5 never writes
   storage publication or marks COMPLETED from computed bytes alone.
6. A2 implements exact owned cancellation operation on same assignment order;
   committed result remains historical. Status derives actual durable command,
   assignment and result evidence under current read policy, no second status ledger.
   Restart uses actual original lookup/reconcile and a new incarnation/current child;
   UNKNOWN keeps same intent/UUID/key and uncertain charges. No new-submit retry.

Initial positive profile may omit renewal/resume ONLY as an explicit unsupported
operation: actual lease must remain valid throughout; expiry/cancel/loss discards
uncommitted output and yields unavailable/UNKNOWN. Do not renew by synthetic clock,
claim a short task cannot expire or use default always-valid lease callbacks.

## Owner implementation requests and executable acceptance

A2: confirm exact reuse vs successor of frozen v3; implement issued Assignment,
current dispatch, durable command/result proof, owned cancel/status/reconcile and
native current policy/leader/generation checks. Publish typed request/results,
keys, proof lifetime, actual transaction operation/encoded-byte ledger <=64/32768.
A7: exact existing result registry candidates and actual store.stage/promote
plus genuine lease-proof implementation/source or explicit NONE.
A4: actual storage reservations/closure/replica policy and same-Consul publication; one disposable volume may NOT
silently reduce required two-copy policy. If unsupported, publication stays closed.
A7: exact callable source, exception/result/cancel contract and pinned deterministic
vector; strict nonbool/awaitable/error cancellation refusal, no authority callback.
ROOT: three-voter stand owner, actual provider/registry/policy issuance and lifetime,
exact six-repo source pins, approved experiment mapping and qualified contained child.

First real acceptance must capture actual native grants and records then compute,
commit, read original result, restart/reconcile and replay without duplicate effects.
Faults: kill worker after grant/before-after result bytes; old incarnation writes;
quorum loss with UNKNOWN; sameUUID changed intent; expiry; cancel/publication both
orders; disclosure/owner/quota denial; actual storage/resource exhaustion. No
mock success, fixture observation DTO or local-only closure PASS is this milestone.
