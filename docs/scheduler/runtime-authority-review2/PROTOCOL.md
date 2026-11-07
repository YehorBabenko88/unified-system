# Issued scheduler records — NEW v1-c3 review2 proposal

PROPOSED / EXACT A2/A4/ROOT ACK PENDING / PRODUCTION UNAVAILABLE.
This explicitly NEW profile corrects review1's scalar fencing and identifier
incompatibilities. Review1/d7 package bytes and all historical checkpoint bytes
are unchanged. There is no automatic conversion, alias, provenance relabeling,
or approval transfer. Request-only cd274d… is still not an issued-grant API.

## Exact checkpoint/fencing dependency

checkpoint-v3-frozen.json preserves A3's COMPLETE raw frozen schema, SHA256
4de720d9391e5a89c0577b5298c283e742fbfe490c4454c184e31c2348589ea4.
The generator verifies that hash and copies the exact structural fencing_token
and instrument_id definitions, without rewriting the frozen schema.

Assignment and WorkerResourceReservation have a TOP-LEVEL fencing_token OBJECT
with exactly these10 fields: cluster_generation, assignment_id, lease_id, node_id,
worker_incarnation_id, leader_lock_index, assignment_revision, lease_epoch,
grant_revision, owner_id. This is the same closed shape as A3 publication_content.
lease.leader_lock_index is a separately named scalar, NOT a fencing token. No
scalar-to-compound compatibility shim exists. Every compound component must equal
the corresponding full-scope/current issued grant component, not merely parse.
The fixture verifier checks these equalities and positive u63 bounds. Actual
native provenance/field meanings/proof remain A2-owned, unavailable here.

Concrete fencing golden is records.json.assignment.fencing_token: generationUUID21,
assignmentUUID5, leaseUUID1, nodeUUID23, worker-incarnationUUID6, leader_lock_index101,
assignment_revision3, lease_epoch7, grant_revision5, owner_id='principal'. All
numeric values are canonical positive decimal STRINGS. UUIDn denotes the literal
00000000-0000-4000-8000-<12-digit-n> fixture, never an enrolled identity claim.
validate_proposal.py also validates this compound directly against the frozen A3
definition and rejects scalar101, changed owner/epoch and legacy opaque node IDs.

cluster_id, cluster_generation, dataset_id, node_id and storage_reservation_id are
canonical lowercase UUIDv4 in this NEW selected profile, matching A3 publication
shapes. job/source/partition/owner remain their declared opaque grammars. UUIDs
must come from admitted registries/issuers; never convert old aliases/hostnames.
instrument_id is explicit null or the exact closed A3 Bybit instrument tuple;
a symbol string alone is not that identity. Other instrument/source profiles are
UNAVAILABLE until separately versioned/admitted; research may explicitly use null.

## Unchanged invariants and explicit key limitation

The complete six-field scope remains in values. Stable partition identity excludes
job and generation and retains cluster-lifetime meaning/nonreuse. Issued ledger/
observation/policy/schedule references remain issuance provenance; unrelated B
allocation/release, ordinary telemetry refresh or policy-cap updates cannot revoke
A merely because a mutable counter advanced. Current admission/accounting/index
checks remain separate. The same parent worker daemon can own concurrent children
only through distinct execution_attempt_id and verified native child proof/session.
PREPARING -> ACTIVE proof attachment remains an actual A2/ROOT dependency.

All compatible resource, lifecycle, UNKNOWN/no-quorum, drain/freshness and
publication/supersession ordering rules from review1 PROTOCOL49eb1aad0545ea809aaee53dcddaa7838f01f061e2131e469df61ed05e886525
remain design requirements, except the identity/scalar representations explicitly
replaced above and budget clarification below. Schemas/fixtures here have NEW
review2 identities and hashes. They do not reinterpret review1 records.

ROOT selected the shared global UUID/idempotency direction under existing
N/authority-v1, with generation-independent tombstones and distinct frozen Mux
binding/digest namespaces. A2's forthcoming authoritative key/preimage/golden
layout is the TARGET. scope-key-vector.json is an illustrative A5 comparison
fixture ONLY, never an alias or substitute for A2's native partition-key digest.
Actual namespace/key/record/proof/descriptor ACK is still PENDING. Do not start
shared API edits or wire a producer using an A5 illustrative hash.

## Budget/policy/lifecycle mapping

runtime-storage-binding-review2.md (outside this package) supersedes review1's
policy-counter wording. storage_budget_revision is immutable ISSUANCE BUDGET
revision, not necessarily the producer's separate policy revision. Trusted issued
descriptor must bind both independently if distinct. Current own lifecycle and
actual current accounting/CAS indexes remain separate SAME-transaction checks.
Golden budget17, policy23 and usage9 are deliberately unequal; B may advance usage
without changing A's issuance basis. No current counter is backfilled into A3
checkpoint bytes. A3 mapping32dfe49a51e66d19a62ba2deb4dbd349ba3e3b8fd5d71c0ed11000ec2f9651be
and A4 mapping469284063a0551e3d1f2c0c26b4b7f577ec660d4cf8527cc6b004959f593a3e4
are design dependencies, not proof of an existing producer implementation.

## Ledger, vectors and release gates

The ledger measures exact synthetic serialized native arrays: publication26ops/
4035bytes, cross-node supersession27ops/13799bytes before enumerated closure
dependencies. Record sample sizes: assignment2180, reservation1840, observation1216,
ledger949 bytes. These are finite examples, NOT maxima, actual native producer
totals, valid atomic transition goldens, byte-debit results or load qualifications.
Native keys/session/global-index/proof attachment and A4 full closure/issuance/
lifecycle/policy/accounting layout may add/change operations and encoded sizes.
No splitting/truncation to fit native atomic bounds is permitted.

Fixture checks:4 record examples,31 negative cases,2 unrelated-reservation/refresh
cases,2 stable-key cases and1 policy cap; compound10 structural match and no scalar
alias. Storage review2 separately has11 semantic vectors, including coupled renewal
continuity preserving immutable issuance and rejecting an uncoupled current token. These tests do not prove
identity provenance, actual storage/grant proof, current authority or native races.

P0 remains exact joint APIs/keys/preimages/issued descriptors/child proof/freshness/
drain and stable identity admission. P1 actual Consul race/overlimit/no-quorum/
restart/rejoin tests and Windows runtime. No full API, publication or fleet ACK.
