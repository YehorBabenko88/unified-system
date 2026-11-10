# Narrow native-session and receipt successor — review3

2026-11-10. PROPOSED DESIGN ONLY / NO-GO. Review1 f9b17f... and review2 de0100... remain immutable. This packet replaces only proposed job and phase-receipt schemas and corresponding FORMAT_ONLY values; all other review1 design requirements/limitations remain subject to explicit owner adoption. No exact codec, API, native result grammar or runtime is approved.

## A4 session correction accepted

A4 static review receipt SHA256 `8b7a44fecd9d1c279aeb78395a37b7f33210bbcdf0477ab25b9cb78e9e4a58b5` was read in full and its bytes hash matched. The initial proposed session definition incorrectly constrained native SessionID variant to [89ab]. Corrected session-typed fields job.original_actor_session_id and phase-receipt.actor_session_id use exact previously pinned native syntax: lowercase ASCII36hex groups8-4-4-4-12 with no version/variant restriction, plus mandatory runtime canonical UUID roundtrip. Source definition pin: `RESEARCH-NATIVE-SESSION-CORRECTION-REVIEW1/lease-lock.schema.json` SHA256 `9bdb1084004fcc6cfb76fa0f1bce0013b6a26a9b288cbb71c82db621feb4f4d0`, independently hashed here. Unrelated client/job/actor UUIDv4 definitions are unchanged. Actual server/session/lock equality establishes authority; syntax and a historical ID never do.

Pure FORMAT_ONLY controls use historical native-format ID cee8705d-033c-168f-2d94-3dfd00149167 and an ordinary canonical UUID; both syntax/roundtrip checks accept. Uppercase, compact and newline-suffixed forms reject. These checks issue/validate no session, perform no RPC and transfer none of the earlier actual session evidence into current native qualification. The historical record is only the provenance of the parser correction.

## Receipt pairing and semantic gate

Inherit review2 operation conditionals: QUEUE PLUS_ONE/jobseq1/prev0; CANCEL_QUEUE MINUS_ONE/jobseq2/prev1. Review2 pure checks retained separately: 2 positive receipts / 6 selected wrong delta/sequence/predecessor rejects. Schemas alone cannot prove quota previous+1/overflow, exact old ledger state, original/actor/job/current receipt/native joins. The complete mandatory semantic join contract and negative vectors in review2 CONTRACT-ADDENDUM.md still apply and remain NOT_RUN at runtime. P1 join gate is not fully closed or FIX_VERIFIED; no adoption from these schema checks.

Both review3 job and receipt schema names are explicit successors, not in-place replacement of current records. FORMAT_ONLY plan copies update just these identifiers and remeasure the full serialized candidate. All identities and indices remain unissued, strict expiry proof absent, policy disabled, no physical keys/grants. Old rights/observation/custody/commissioning/response/worst-case bounds remain OPEN. Never send candidate native-shaped JSON or invoke a private pipeline.

## Custody outcome precision

NOT_SENT means only this local attempt has not been sent. DEFINITIVE_REJECT means only this one unambiguous attempt received a definitive rejection with no prior unresolved send assumed. Neither establishes original-wide absence, never-committed state or terminal rejection if an earlier attempt is UNKNOWN. Retain exact original/attempt history and conservative debt; no retry/rekey/refund or pending-original eviction. A later known commit remains known while current authorization/disclosure can be unavailable.

Proposed standalone custody32768-byte receipt/4MiB DB/64records remain unqualified budgets, not a native C3 16KiB widening or complete Journal row/hash-chain/SQLite/WAL bound. Full encoded layers and append/durability/cancellation/cleanup must be measured and co-ACKed. Capacity exhausted => reject before effects; never discard pending UNKNOWN custody. Original native13 and T/P/S/D remain unchanged.

Root D4-TIME option1 stays strict and unsatisfied; current broker's non-UTC profile requirement remains incompatible. Logical mutations DISABLED. Implementation base NONE_APPROVED. No runtime source edit, new issuer/broker/authority/Scheduler, schema activation, native/Job/browser/physical call, resource/publication/read/release permission. Owner scoped review required at this exact successor hash.
