# PR277 independent local custody acceptance

Exact Grid HEAD `19fae71db66a24f7be7bfa8d1682e1831c4720c4`, tree `b25ad56e1a6b160279867bf34248150328391178`, module SHA `d128cdc5f6b787e3a0ff664c3af6c5d73cdef7a751e974cb990cade3ac39394a`. Support Unified exact `1f6b0b5c231853607f5bec780f1544cd32bf577d`, actual Journal9f170. Five paths changed relative to b513: local runtime adapter, tests, driver inventory and API documentation. Source/safety review preceded execution. All 20 pre-existing top-level/method definitions from Grid539 have equal ASTs; this is not native regression execution. Core868/runtimecfb are unchanged and F27 remains open.

| Requirement ID | Repository / PR / exact HEAD | Test | Environment | Expected | Actual / status | Evidence | Severity / correction |
|---|---|---|---|---|---|---|---|
| A8-LOCAL-CUSTODY-277 | Grid PR277 /19fae71 above; Unified1f6 support | Full committed 12-case suite: six schema/identity DATA, three Journal/replay, three actual local adapter groups | Own fresh no-hardlinks Windows CPython3.12.10 venv, -I -B, temporary synthetic stores | Closed DATA semantics, OS single-writer exclusion, unchanged Journal on denied contender, later acquisition, refusal of unsafe paths/sidecars/links, restart UNKNOWN/no automatic retry | 12 unique PASS /0 skip | [Original test log](stderr.log), [driver result](stdout.log), [primary raw receipt](receipt.json) | Scoped LOCAL PASS; no Root role/native freeze |
| A8-LOCAL-PROCESS-LOCK | Same sources | Two actual own subprocess calls within the suite | Same local temporary Journal | Contender denied while lock held, then acquire after owner closes | Both returned0; DENIED then ACQUIRED/effectfalse; records unchanged asserted | [Original captured child outputs](own-child-observations.json), [executed wrapper](executed-wrapper.py) | Part of the 12 cases, not two extra unique tests or PID identity qualification |

The adapter holds an actual nonblocking lifetime OS lock and retained local file descriptor, verifies ordinary single-link path/file identity and persistent header, refuses foreign pre-existing database adoption and sidecars, and uses fixed Journal methods. Tests exercised actual hardlink/path/sidecar refusal, context close idempotence, retained original error including a reported cleanup failure, restart with unresolved attempt and refusal of mutation retry. Format-only local CONFIRMED SID reports are unissued DATA, not actual Consul sessions or registration proof. Existing earlier sidecar preflight test uses a real owned sidecar plus mocked Path.exists=False; it is not an actual dangling-symlink experiment.

815 Grid and1519 support files matched primary Git raw bytes before and after, with no extras. The committed source guard and additional A8 raw verification both completed. Parent HTTP/connect/DNS guards were never called. These parent guards do not propagate into subprocesses; exact reviewed child source imports only the local Journal/adapter and performs no native call. CPython's venv redirector is a bootstrap executable here, not a claimed native PID identity witness. No native Consul, worker, registration write, session issuance, qualifier, provider or office fault was executed. Old25 native cases were NOT rerun and are not transferred to the new module hash.

The kernel lock excludes cooperating adapter processes; server-selected private path/ACL, Root-only lifecycle and protection from privileged bypass remain deployment prerequisites. No credentials or Root role are established by the local adapter. Root/A2 owner12 receipts, their separate coACKs and historical RED artifacts were not independently authenticated in this phase; A8's own original execution is linked above. No new implementation defect was established in this scoped review.

RELEASE_MANIFEST_STATUS: no approved release or implicit source-pin upgrade.
NODE_INVENTORY_STATUS: not requalified.
CONTRACT_STATUS: actual local source/API reviewed only; native registration freeze NOT_GRANTED.
OFFLINE_TESTS: full current12 PASS /0 skip, two subprocess observations included.
WINDOWS_CI: NOT_RUN here.
PHYSICAL_TESTS: BLOCKED.
P0_P1_P2: 8 open P1 /3 P2 unchanged; absence of P0 not proven.
EVIDENCE: original logs, wrapper, child observations and raw source maps above.
NEXT_ACTIONS: independently qualify Core proxy fix, broker/client custody and any future one-shot native adapter before native registration admission.
GO_NO_GO: NO-GO; TAILSCALE_REMOVAL BLOCKED.
