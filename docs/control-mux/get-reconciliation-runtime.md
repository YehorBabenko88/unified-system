# Isolated real GET reconciliation runtime

Base0c21256e30aeb3a4184dda97a2bebf24c047acd0/tree3a7568acf3a6bc5fd99a6986db554daa9e3919cf; feature/agent2-control-mux-get-20261107. Historical PR32/33 refs and exact08d evidence are preserved. No second consensus, native provider implementation, role/permission, shared identity schema, installer or production listener is introduced.

## Actual callable and evidence flow

ControlMuxRuntime.handle now recognizes GET /control/v3/commands/<canonical UUIDv4>. This is an explicit in-process/isolated HTTP composition only. Default ControlMuxApp and missing-native composition remain503; Root/native/browser/office attachment is NOT admitted. Current X-Request-ID queryUUID must differ from original pathUUID, and never claims/writes a mutation request/key index. GET rejects body, Content-Type, nonzero/noncanonical Content-Length, duplicate headers and mutation-only idempotency/epoch headers.

The existing native GET_COMMAND operation resolves current AdmittedContext; no RECONCILE permission or role extension. MuxAuthority.reconcile_document(current_context,originalUUID,queryUUID) performs the current four fixed Root identity checks, including bounded actual provider callbacks. The same consistent native read transaction checks actual identity indices and captured request index, original command, original receipt and original response indices. The HTTP200 wrapper is built from those SAME captured records. There is no second read/merge after validation and no leader/lease-provider call for history. Actual quorum/consistent read remains mandatory.

The new reconciliation.py pins the unchanged a7c9730... review2 schema and implements its exact semantic constraints with shared validate_original before204. It checks original method/path/body/profile/duplicated IDs and epochs, original key/digest links, operation/result matrix, exact response bytes/hash and full16384byte cap. Native receipt index is positive actual captured ModifyIndex, never inferred from wall time, claims or a predicted commit. Original mutation201/202/204 stays inside the immutable receipt; current GET is200. No current target state is substituted for historical bytes.

For implemented OPEN/SUB/CLOSE final native receipt commits, pure require_fit checks the actual original preimage/body/result with worst19digit index SIZE before final transaction. That local discarded preflight document never observes/stores/returns the max index, never grants permission and never becomes evidence. Unsupported/oversized future outputs cannot commit a terminal result through this path; bounded PENDING debt is not silently released. Current actual implemented outputs fit. Positive ACK204/contained close204 remain unimplemented; original204 semantics are validated by frozen model vectors, not an invented writer.

## Exact internal GET native-denial ABI

NativeAdmissionError(kind) in commands.py accepts only exact strings UNAUTHENTICATED, SESSION_EXPIRED, FORBIDDEN, UNAVAILABLE. Consumers accept only the exact exception class and closed kind; subclass/malformed/foreign/untyped failures deny503. This is internal trusted provider error classification, not proof/admission or a client-selectable field. Four provider method signatures remain unchanged; only actual callback boundaries resolve/revalidate/identity_binding/verify_records can preserve these classifications. Parsing/hash/record/Consul faults cannot become401/403. Existing mutation error policy is unchanged.

| Current lookup cause | Existing wire response |
|---|---|
| Actual typed invalid human session | 401 UNAUTHENTICATED |
| Actual typed verified human expiry | 401 SESSION_EXPIRED; uncertain clock is unavailable, never assumed expired |
| Valid native session denied GET_COMMAND/RBAC | 403 FORBIDDEN / ROLE_DENIED |
| Actual owner/actor disclosure mismatch | 403 FORBIDDEN / NONE, no original evidence |
| Missing provider/untyped/unknown failure | 503 AUTHENTICATION_UNAVAILABLE or ADMISSION_UNAVAILABLE / PROVIDER_UNAVAILABLE |
| Clean missing original index or clean PENDING | 503 ADMISSION_UNAVAILABLE / NONE |
| Corrupt/conflicting/missing-linked terminal evidence | 503 ADMISSION_UNAVAILABLE / RECEIPT_AMBIGUOUS |
| Actual authority/quorum/index-check uncertainty | 503 ADMISSION_UNAVAILABLE / PROVIDER_UNAVAILABLE |

Valid current queryUUID is echoed in current GET errors, including early/later401/403/503. Invalid/missing queryUUID isnull. A bounded metadata-only extraction supplies correlation even when no native provider exists; it reads no unadmitted body/authority. Errors contain no fabricated original digest/receipt, no original rejection is stored and no new idempotency entry is created.

Root/A6 direction ACK covers this mapping only; exact new class/module/source and actual native implementation need fresh review before attachment. The current Root provider is absent. Tests of typed expiry/denial use explicitly synthetic native causes and do not establish actual Windows session expiry/authentication.

## Tests and limits

Mandatory inventory: prior18unit retained +15new =33. Real HTTP/Grid/Consul inventory: prior42retained +30GET/classification groups =72, with16typed native-cause subchecks (four causes at four callback boundaries) additionally recorded under four group IDs. Frozen semantic supplement remains24models; source guard negatives8 unchanged. New exact source results must be generated independently; no old08d/A6/A8 PASS transfer.

Actual cases cover201/202 wrappers/native indices, no app leader, later current authorized session with original session unchanged, clean missing/PENDING, cross-owner403/NONE, current policy lacking GET_COMMAND403, revoked identity, provider unavailable, typed/unknown/malformed/subclass/wrong returns/stub failures, client identity-header nonauthority, unchanged private KV/debt, original body/epoch/profile hash-consistent corruption, missing terminal response, real native409 index races and one-of-three no-quorum. A typed-looking post-read storage fault must remain503 rather than impersonating an expired native session.

A currentCLOSED test explicitly injects that future current-state marker into the private ledger and restores it; it is not a product CLOSED transition or evidence of containment/release. Receipt-index race explicitly deletes/recreates SAME receipt bytes as a fault. Consul same-valuePUT leaves ModifyIndex unchanged, independently observed10/10/12 after an actual changed value. These are trusted-state consistency tests, not protection against malicious authority writers. All original failed RED/harness runs are preserved separately.

Only owned ephemeral127 HTTP/Consul test processes are created. The fixture's explicit lease renewals happen outside GET, with all handles stopped afterward. No services, security configuration, physical nodes, provider sends, key/certificate operations, merge or deployment. Office voters LS5/PC4/PC3 stay2/3. No READY/LIVE/ACK204/release, snapshot/barrier or worker grant is invented.

Exact new source qualification, Linux/Windows CI, fresh Root/A6/A8 review and separate native/physical admission remain required. Production NO_GO.
