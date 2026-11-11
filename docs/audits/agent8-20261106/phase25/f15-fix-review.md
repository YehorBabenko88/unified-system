# F15 scheduler CI raw-source correction independent review

Requirement: raw committed source binding before/after tests, independent of Git index flags, no ID/skip weakening.
Repository: unified-system Draft PR24; HEAD6bcf5475023a8f6a9733d02ad899064d0d83be95; treeef776ac4c484967d53dd172469ce77534ebb2216; previous175b48a2a0d2882669172abc5774bd71b42e2215; PRbase2df6f5c2f77f4d883bad1a8623dd8375db529be0.
Environment: independent Windows raw-LF clones, Python3.12 and isolated tzdata2026.6; each negative fixture in a fresh auditor-owned clone. No developer source mutation, network/backend/office/native service action.

PASS offline exact-source: delta only dedicated workflow plus two docs. All product/test/inventory blobs unchanged. Git LF settings apply before checkout; source captures HEAD tree, resolves protected Git blob OIDs and compares raw bytes plus SHA256/length, checks ordinary parents/files and reparse attributes, required/extra protected files. Inventory read only after raw admission. Exact30inventory/no-skips/logSHA/evidence.v2 retained.

Independent exact embedded CI block clean30/30PASS0skip/error, all8protected files valid and equal before/after; log hash verified. Eleven negative controls reject: original hidden durable comment; hidden test comment; hidden inventory whitespace; hidden workflow comment; hidden CRLF source; missing source; nonregular source; unexpected protected Python; hidden post-test source mutation; substituted ID withsame30; skip. Pre-source faults execute0tests. Hidden post-test fault executes30then rejects source_after with passedfalse. Every receipt/log is retained and checked. Original F15RED phase24 remains preserved.

F15 FIX_VERIFIED_OFFLINE_EXACT_SOURCE only at6bc. This proves regular protected raw input binding under the trusted ephemeral-runner model, not hostile same-user/native execution attestation or full import/runtime/dependency integrity. No source normalization forgiveness. Phase24 local journal semantic review remains bounded to unchanged product blobs; no new authority/storage/worker integration inferred. Hosted exact-head runs in hosted-snapshot.json remain separately NOT_QUALIFIED; no old175b/942e success transfer.

No new blocking issue identified in this correction scope. Overall NO-GO6P1/1P2; mandatory hosted Windows/runtime/physical and Tailscale removal gates remain blocked/unqualified. Evidence: f15-fix-review.json; clean and11control receipts/component logs/stdout/stderr; source runner ../recheck_scheduler_f15.py. Closure sent to A5 and ROOT; A8 edited audit files only.
