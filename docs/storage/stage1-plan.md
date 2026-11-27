# Storage Stage1 implementation plan

> Execute inline under executing-plans and TDD. Concrete ROOT allocation already authorizes this independent nonproduction slice; no extra human confirmation requested.

Goal: strict typed untrusted claims, immutable byte hash/length/framing checks and nonexecuting retention/pin/last-copy plans.

Spec: ROOT Stage1 allocation in Agent4 chat; owner V3 checkpoint schema4de720d9/protocol79efbcb7 and publication review4 mapping570437ac. Base2df6f5c2f77f4d883bad1a8623dd8375db529be0.

Constraints: only unified_system/storage/{__init__,contracts,segments,retention}.py, tests/storage/**, docs/storage/**. Stdlib Python3.11+. No product file/DB/network/listener/factory mutations. Parsed claims and byte matches never become authority; plans never execute effects. Test-only filesystem fixture adapters stay tests/storage.

Review focus: bool/number/string coercion; malformed duplicate/deep/oversized JSON; hash match without framing/identity; alias/corrupt replica counts and pinned dependencies; checkpoint unknown time versus unconfirmed commit.

Task1 contracts/segments:
- Write tests for strict typed SegmentClaim and InstrumentIdentity, exact fields/canonical decimal counters and hash; unknown input denies.
- Run RED (missing module/behavior) and retain source-bound evidence.
- Implement SegmentClaim validation, verify_segment_bytes(bytes,claim) bounded JSONL framing/hash/length/count/identity/range checker. Return BytesCheck with authority_verified false; no path or I/O API.
- Add V3 fixture compatibility checks of exact owner fields and no promotion; no duplicate checkpoint codec implementation.
- Run GREEN and record explicit discovered case IDs. Commit scoped source+tests.

Task2 retention:
- Write RED for plan_retention facts with research/dependency pins, gaps in closure, corrupt/unavailable/aliased survivor claims and last-copy boundaries.
- Implement frozen typed RetentionFacts/ReplicaClaim/RetentionPlan, candidate-only KEEP or QUARANTINE_CANDIDATE decision with always executable=false and missing actual authority/proof gate. Never accept caller bool as effect permission, never count existence-only replica claim as verified copy.
- Run GREEN with disposable fixture bytes corrupted/truncated to exercise verifier; no destructive cleanup executor.

Task3 evidence/review:
- Run Stage1 suite plus baseline/project unittest suite, disclose existing failures/skips separately.
- Produce exact case inventory, source hash/tree binding and local RED/GREEN logs; document no runtime replication/backup/physical acceptance.
- Independent review, resolve meaningful failures tests-first, commit/push feature and DraftPR, attach PR and send ROOT/A8 exactHEAD/tree/evidence.

Ruling: skill plan/ledger paths placed in work/ during pending native creation, later copied to owned docs/storage; no edits outside allocated repo paths. Native request is never duplicated. Runtime ACK is not a prerequisite for tests. No mutation or delete is implemented.
