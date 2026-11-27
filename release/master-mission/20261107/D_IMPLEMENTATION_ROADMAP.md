# D — Implementation roadmap

1. Preserve canonical baseline and ownership; reconcile exact component SHAs before integration.
2. Agent 7 fixes existing Math helper overflow in separate branch; original PR115 diagnostic remains untouched.
3. Agent 3 closes persistent book availability semantics after consumer/contract ACK; qualify the narrow PR268 independently on Windows.
4. Agent 2/4/5 close authority/assignment/storage APIs; no boolean capability placeholder substitutes supported admission.
5. Agent 1/2/Root close native identity, key/IPC, Control multiplex and shared egress enforcement.
6. Agent 6/7 bind backend domain identity, revision and financial units to actual UI; keep unavailable fields explicit.
7. A8 independently verifies exact integrated source and required hosted artifacts.
8. Root performs gated sequential pilot; no parallel office installs or fault injection.

For each actual defect: reproduce → preserve original logs → regression → fix → CI → review → candidate update → retest. No merge or production deployment is authorized by this roadmap.
