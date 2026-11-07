# Phased isolated executable acceptance preparation — 2026-11-07

Overall NO-GO. Audit register remains6P1/2P2; F16 globallyOPEN. This preparation creates no new release, runtime adapter, provider, native identity or production authority. Physical and Tailscale removal gates stay BLOCKED.

| Phase | Status | Independent qualification |
|---|---|---|
| MODEL | NOT_RUN | Fresh Review4 functional model suite was not executed; inventory bookkeeping is not model acceptance |
| CODE | PASS, narrow harness scope | Primary raw source/binary checks, exact mandatory inventory and owned-process cleanup only |
| ENDPOINT | BLOCKED | Real primitives passed separately; admitted real ConsulMux/LAN/HTTP integration entrypoint has not been supplied |
| WINDOWS | BLOCKED | Execution host is Windows3.12; mandatory hosted Windows matrix/artifacts remain unqualified |
| PHYSICAL | BLOCKED | No office fault injection, provider sends or native provisioning authorized |

| Requirement ID / repository | PR / exact source | Test name / environment | Expected | Actual | Evidence / status / severity / required correction |
|---|---|---|---|---|---|
| CODE-SOURCE / unified-system | PR30 1541af3b0e99fdb671f59c205696faab40e283e4 tree30d32ab7b75eadcca46b41ae6809415665ef1413; PR31 7a0365bd0161ec619019157cf04672b513c495c6 tree597dbbdad1861f3e872f867dba30ad2667566d15 | Exact raw inputs before/after; own Windows clones | Match primary Git blobs; no reparse input | All286LAN/291Control tracked files match before/after | source-before.json/source-after.json PASS; existing gate severity unchanged; no current consolidated candidate transfer |
| ENDPOINT-CONSUL / audit harness | No product PR; owned binary1.22.2 SHA41762ef5b98c8dd9b6852df6cfbceed37e7f0acc5760856be33100f1092475e1 | Actual3persistent voter processes/BoltDB, distinct loopback ports, real HTTP API | Oneleader,3voters; CAS0 commits once; duplicateCASfalse;3consistent reads match | PASS; original voter/index/value-hash evidence retained | consul-consistent-cas.json +3logs PASS primitive only; Consul ACL/TLS disabled in this disposable lab, no operator/peer-auth qualification |
| ENDPOINT-MTLS / unified-system | PR30 exact above | Real ephemeral CA/certs and paired product loopbackTLS;3selected unittest cases | Real payload/credit/accounting, pin/SAN/EKU/expired cert negatives | 3PASS,0skips; no successful synthetic provider | mtls.stdout.log/mtls.stderr.log PASS primitive only; does not carry ConsulMux/HTTP or qualify fragmentation |
| ENDPOINT-HTTP-CLOSED / unified-system | PR31 exact above | Actual loopback HTTP server wrapping default ControlV3App, forged Authorization | HTTP503/AUTHENTICATION_UNAVAILABLE, no resources/native admission | PASS; exact bounded error body retained | http-closed.stdout.log PASS closed endpoint only; actual authenticated read/session/RBAC still missing |
| ENDPOINT-INTEGRATED / consolidated candidate | Exact real adapter pin not supplied | Consul-backed ControlMux over admitted transport/HTTP | Real chain with original receipts and no mock success | BLOCKED, not run | Existing F05/F06/P1 runtime gaps; Root/A2 publish exact callable entrypoint and approved mandatory case registry |
| CODE-CLEANUP / audit harness | Harness rawSHA in receipt | Stop only3Popen handles owned by invocation | Every owned process exited, preserve data/logs | PASS all_owned_stopped=true; PIDs recorded | phased-acceptance.json PASS; no service/system/fleet changes |

The mandatory inventory contains10IDs:1MODEL notrun,3CODE pass,3real primitive endpoint pass,1integrated endpoint blocked,1Windows blocked,1physical blocked. skip_inventory=[]; BLOCKED/NOT_RUN were not omitted or counted as passes. Reporter tests5PASS/0skip reject missing/substituted mandatory IDs, mock endpoint qualification, SKIPPED mandatory status and primitive-to-integrated PASS transfer. Those formatter/gate tests are not product tests.

Execution: `work/audit-venv/Scripts/python.exe -I -B outputs/run_phased_acceptance.py --execute --output outputs/NEW_EMPTY_PHASE_DIRECTORY`. Default paths deliberately bind the independently reviewed component clones and cached hash-pinned Consul binary. Each invocation creates a fresh work/ scratch directory and fresh empty evidence directory. No existing storage is opened. Consul config fixes client/bind/advertise/join addresses to127.0.0.1 and disables remote execution/script checks/update checks; subprocesses use CREATE_NO_WINDOW. Python endpoint children reject nonloopback bind/connect via an audit hook. Only owned handles are killed in finally; process data/logs retained. Credentials/certificates remain ephemeral test inputs and no private key material is exported.

Historical phase33 first run is preserved, including its exact executed harness. It reported inventory bookkeeping as MODEL-REGISTRY with an explicit no-functional-model qualification. Final phase34 corrects classification to CODE-INVENTORY, adds MODEL-CONTRACTS NOT_RUN and explicit five-phase summary, then freshly reruns all real primitives. No old witness is silently relabelled or numeric result transferred.

Review4 immutable root360c5cdc9dae88416d69f8765f3dff5ab8828945 is recorded as a DESIGN pin only; its original manifest is retained and hashed. No fresh model/source/runtime acceptance follows from that ACK or manifest. Preparation uses older separately identified component pins; the next consolidated candidate needs new exact source and artifact binding.

Evidence: [full receipt](phased-acceptance.json), [artifact hashes](artifact-sha256.json), [real Consul evidence](consul-consistent-cas.json), [negative reporter tests](reporter-negative-tests.log), source-before/after and original endpoint/process logs alongside this report. Harness ../run_phased_acceptance.py; negative tests ../test_phased_acceptance_gate.py.

Next: Root/A2 supply exact consolidated SHA/tree, actual ConsulMux composition entrypoint/launch args, current auth and authority receipt boundaries and mandatory case IDs/platforms. Add tests against that real published path without adding an audit-owned successful authority provider. Preserve UNKNOWN/no-quorum/restart fencing semantics and real skip inventory; no physical/provider/native provisioning activation.
