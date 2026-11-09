# F32 successor: exact PR69 source-only review

Draft PR69 exact HEAD `453cb6d60efbdb8a34a7237053d69b6d631ed488`, tree `31c70d248c5c1bd4ced335c8a1b437d592dc5b12`. Independently confirmed against original GitHub metadata, Git commit/tree, and all1668 raw primary files in an own clean review clone; no extras. Bounded four-file diff from461 reviewed. No helper/project import, application/fault test, Job/native API, SDK or browser execution by A8.

| Requirement ID | Repository / PR / exact HEAD | Test / Environment | Expected | Actual / Status | Evidence | Severity / Required correction |
|---|---|---|---|---|---|---|
| A8-HEAD-142 | unified-system / PR69 /453 above | Exact original metadata, object tree and raw files / isolated clone | Exact source binding | PASS_SOURCE_BYTES,1668 primary/no extras | [metadata](GitHub-PR69.original-metadata.json), [source verification](source-verification.json) | No new mismatch |
| A8-F32 | Same | Bounded AST/control-flow review / source only | Shared cleanup deadline; no restarted wait windows; overrun forbids PASS | SOURCE_CORRECTION_ACK; independent runtime qualification NOT_RUN | [exact diff](exact-source-diff.patch), same AST | P2 pending runtime qualification; new immutable package required |
| A8-REGRESSION-142 | Same | Two added test sources / not executed | Helper cap/expiry and expired own fallback regression | NOT_RUN_BY_A8; owner103 and A5 source ACK not transferred | Exact diff | No native lifecycle or aggregate runtime proof |
| A8-PACKAGE-C | New candidate not supplied | Concrete package/invocation/isolation review | Bind corrected source to actual new manifest | BLOCKED_PENDING_PACKAGE; no execution admission | This report | Preserve b frozen, separately review c |

The execute finally captures cleanup_started and one cleanup_deadline=cleanup_started+10s. Job wait and each retained Popen wait get min(cap,positive remaining) through cleanup_seconds. At expiry those ordinary waits reject rather than obtain a fresh budget. Watchdog.finish accepts a finite timeout0..1 and gets at most the actual remaining interval. Orphan fallback still attempts terminate on only retained direct Popen objects; its subsequent wait is capped by remaining time and becomes0 after expiry. Capture.save similarly passes remaining capped2 to each existing reader join, including0 after expiry, then refuses unjoined readers. The real execute callsites pass the shared deadline, even though helper default arguments retain compatibility behavior for separate callers.

After own cleanup/joins the receipt records work_elapsed_ns, cleanup_elapsed_ns and family_elapsed_ns. Any observed work>20s, cleanup>10s or family>30s sets a failure and time_budget=EXCEEDED before final result selection. Existing uncertainty/nonzero exits/watchdog expiry/capture errors still prevent PASS. No failure is reclassified by a later kill. If watcher remains alive its Job handle is retained rather than closed under it. No new PID reopen, borrowed-handle operation, forced Resume, service action or package mutation is introduced.

This corrects the identified fresh-per-stage-budget source gap. It is a cooperative deadline and observed overrun rejection, not proof that native calls, process scheduling or OS freeze cannot exceed the interval. wait_empty still polls/sleeps and native termination/query/close can run beyond a requested timeout; the later elapsed check forbids successful acceptance of such an observed overrun. If OS/controller stalls permanently there is no completed receipt. Package/source verification before the family timer, final package verification and receipt writing outside it are not included in an end-to-end30-second claim. Exact-boundary elapsed values are accepted by the final > comparison; normal stage checks retain their own earlier deadline denials.

The two added regression sources check cleanup_seconds cap and expiry, and that expired fallback calls own terminate then wait(timeout=0). Their names alone do not establish that every actual native lifecycle phase was exercised. A8 did not run them, import modules or authenticate owner RED/GREEN103 receipts. Root103 LOCAL_NOT_HOSTED and A5 scoped ACK remain distinct evidence classes.

bootstrap1b3c, package5bd7, assembly, corrected materialize451ad and export6e7 are byte-identical to461. Only launcher/supervisor, one test file and source-review documentation change. No additional high-confidence actionable source defect was found in this bounded diff. The prior700c/c20d core ACK does not silently extend to new runtime behavior; this new453 source ACK is explicit and limited to reviewed control flow. Frozen package b contains the older launcher/supervisor and remains unexecuted/unqualified; it cannot inherit the453 correction without a new immutable assembly. No implementation was edited by A8.

RELEASE_MANIFEST_STATUS: new c manifest/externalSHA/invocation pending; prior b bytes verified only.
NODE_INVENTORY_STATUS: no new physical inventory, ACL, token or headroom admission.
CONTRACT_STATUS: F32 SOURCE_CORRECTION_ACK at453; runtime qualification pending.
OFFLINE_TESTS: independent static/source-byte checks only; application/helper/fault tests NOT_RUN_BY_A8.
WINDOWS_CI: owner103 not A8/hosted mandatory acceptance; F26 unchanged.
PHYSICAL_TESTS: NOT_RUN_BY_A8; physical fault injection BLOCKED.
P0_P1_P2:7 open P1 /7 P2 retained; F31/F32 source corrected, independent runtime qualification pending; absence of P0 not proven.
EVIDENCE: exact original GitHub metadata, raw primary inventory, bounded diff and AST; no runtime receipts accepted here.
NEXT_ACTIONS: Root supplies newly assembled c/external manifest SHA/exact invocation and fresh isolation evidence for separate review. Do not modify or execute b.
GO_NO_GO: NO-GO. TAILSCALE_REMOVAL_ACCEPTANCE: BLOCKED. Source ACK is not execution admission.

Evidence preservation: exact-source-diff.patch retains original Git patch context lines and line endings. The whitespace checker flags its literal blank context lines; this raw evidence is intentionally unchanged. Formatting checks exclude only this patch; checksum/raw-primary verification includes it.
