# F28 scoped local adoption closure

Exact Grid PR279 `2f94da511681811588e0f850a0a0e9dc4479c8b8`, tree `3e9664296a225d2ba20f594f73b1495c18fe8185`, module5b972/Core3dd. F28 is now FIX_VERIFIED_LOCAL_ADOPTION_ACKNOWLEDGED for this exact local successor. The prior19fa failure remains historical; no release/deployment or old-head correction is inferred.

| Requirement ID | Repository / PR / exact HEAD | Test / verification | Environment | Expected | Actual / status | Evidence | Severity / correction |
|---|---|---|---|---|---|---|---|
| A8-F28-ADOPTION | Grid PR279 /2f94da5 above | Bind exact local correction to both scoped owner ACKs and prior A8 own13 | Read-only original files and received Integration Owner acknowledgment | Same module/source/API; local cleanup accepted; native freeze excluded | PASS scoped documentary closure; zero new runtime tests | [Root received ACK](Root-received-adoption-ACK.txt), [original A5 ACK](A5-original-fixed-ACK.json), [hash verification](original-evidence-verification.json) | F28 local fix/adoption acknowledged; remove from open P2 count only in this scope |

A8 independently executed13 unique tests at the exact source in phase131; this phase does not rerun them. Root explicitly adopts the local API/source correction using A8's result and does not claim a Root13 rerun. A5's original ACK SHA3b127332, focused receipt SHA4f9d4946 and script SHAb2975b35 were independently read, hash-checked and retained. Exact source/module bindings and local=True/native_freeze=False agree. A5 reports two own focused cases; these are neither A8 tests nor additive unique coverage. The A5 script was not executed by A8 and its historical process execution was not independently replayed. The receipt's core_dependency_sha256 refers to authority_runtime_v1.py/cfb32; the ACK separately identifies coordination.py Core3dd, avoiding aliasing those dependencies.

Both ACKs are LOCAL source/API/cleanup only, under Root-private-path/ACL and cooperating-owner lifecycle prerequisites. They do not establish Root credentials, native registration/session issuance, worker binding, current resource holds, clock health, positive effect admission or final native API freeze. F27 Root consumer gate remains open. No proxy2 result is transferred to the combined2f source, no hosted/physical test is accepted, and no source pin elsewhere is changed automatically.

RELEASE_MANIFEST_STATUS: not approved for release or production.
NODE_INVENTORY_STATUS: not requalified.
CONTRACT_STATUS: F28 exact local correction/adoption ACK complete; native freeze NOT_GRANTED.
OFFLINE_TESTS: prior A8 phase13113 PASS retained; new runtime tests0.
WINDOWS_CI: NOT_RUN here.
PHYSICAL_TESTS: BLOCKED.
P0_P1_P2: 8 open P1 /3 P2; F28 exact local scoped fix acknowledged. Absence of P0 not proven.
EVIDENCE: original ACK/receipt/script hashes above and phase131 own evidence.
NEXT_ACTIONS: qualify actual Root consumer/broker client custody, explicit source pair and mandatory hosted evidence.
GO_NO_GO: NO-GO; TAILSCALE_REMOVAL BLOCKED.
