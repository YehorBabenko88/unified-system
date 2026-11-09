# PR279 independent failed-entry correction acceptance

Exact Grid Draft PR279 HEAD `2f94da511681811588e0f850a0a0e9dc4479c8b8`, tree `3e9664296a225d2ba20f594f73b1495c18fe8185`, parentb0. Independent GitHub metadata confirms this current Draft head. New assignment module SHA `5b972b6d81eeaf6f2283584c5b0482552fa9bf0717a4379838900a72da791491`; Core3dd is byte unchanged. Five paths changed; the sole runtime change catches failed __enter__ ownership validation, closes retained own handles, preserves the original exception and adds a note on cleanup-report failure. No persistent database/lock file deletion is added. Source/safety review preceded execution.

| Requirement ID | Repository / PR / exact HEAD | Test | Environment | Expected | Actual / status | Evidence | Severity / correction |
|---|---|---|---|---|---|---|---|
| A8-F28-LOCAL-FIX | Grid PR279 /2f94da5 above; support Unified1f6 | Full current13-case suite, including new failed-entry regression | Own fresh no-hardlinks Windows CPython3.12.10 -I -B, temporary synthetic stores | Entry error retained, body not executed, both FDs closed before contender, contender acquires without manual close, rows unchanged | 13 unique PASS /0 skip | [Original test log](stderr.log), [driver result](stdout.log), [primary source receipt](receipt.json) | F28 local correction verified; owner source adoption/Root-A5 ACK remain separate |
| A8-F28-CLEANUP-ERROR | Same new case/source | Actual sidecar entry fault; injected close-report error after real close | Same own store | Original entry exception and cleanup note survive; next child acquires after removal of only own sidecar | PASS within the new case | [Executed wrapper](executed-wrapper.py), [own child observations](own-child-observations.json) | Not an actual OS close syscall failure or extra unique test |
| A8-EXACT-HEAD-279 | Same PR | Connector metadata and primary Git | Read-only GitHub/Git | Draft head/tree agree | PASS for this PR at observation | [Original metadata](GitHub-PR279.original-metadata.json) | No fresh global six-repository verification |

The current suite reran all13 methods on this exact source. Four bounded own child calls returned0 with statuses DENIED,ACQUIRED,ACQUIRED,ACQUIRED; they are included in13, not four extra tests or native PID identity proof. The new path-mutation entry fault uses actual os.fstat failures to show both descriptors are closed before its contender starts, without manual parent close. The sidecar case removes only its known own fault and retains the original exception after actual close plus a simulated reporting exception. Persistent DB/lock files are not deleted by the adapter. Old phase12812 PASS and phase129 actual19fa defect evidence remain immutable; no historical result is rewritten.

821 Grid and1519 support files matched Git raw bytes before/after with no extras. Committed guard plus additional A8 primary verification completed. Parent HTTP/connect/DNS guards recorded zero calls; they do not propagate to the reviewed local-only child code. All own child calls returned and own temporary resources were retired. No Consul, native registration/session/job write, worker, protected diagnostic, provider or office/network action was executed. Core3dd matches the prior component fix by bytes, but A8 did NOT rerun the two proxy/native-read cases on this combined HEAD and does not transfer phase1302 PASS or owner combined-source2 PASS to it.

F28's cleanup defect is fixed in this independently tested local successor. Overall finding status retains owner source-pair adoption/Root-A5 acceptance pending; old selected19fa source remains defective until explicitly advanced. Native registration freeze is not granted. F27 consumer custody remains open. Owner13, owner proxy2, historical partial RED and coACK claims were not independently authenticated here; only own13 is counted. No new actionable defect was established by this scoped review.

RELEASE_MANIFEST_STATUS: no approved release or implicit source-pin adoption.
NODE_INVENTORY_STATUS: not requalified.
CONTRACT_STATUS: corrected actual local API verified; owner/Root-A5 source adoption pending, native freeze NOT_GRANTED.
OFFLINE_TESTS: full current13 PASS /0 skip; proxy2 NOT_RUN at this HEAD.
WINDOWS_CI: hosted NOT_RUN here.
PHYSICAL_TESTS: BLOCKED.
P0_P1_P2: 8 open P1 /4 P2 retained pending adoption; F28 local fix verified, overall adoption gate pending. Absence of P0 not proven.
EVIDENCE: original logs, source maps, child observations and exact PR metadata above.
NEXT_ACTIONS: Root/A5 explicitly acknowledge corrected source/API pair; independently qualify consumer/broker custody and exact hosted evidence.
GO_NO_GO: NO-GO; TAILSCALE_REMOVAL BLOCKED.
