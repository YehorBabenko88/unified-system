# A8-F28 independent failed-entry cleanup reproduction

P2 OPEN. Exact Grid PR277 HEAD `19fae71db66a24f7be7bfa8d1682e1831c4720c4`, tree `b25ad56e1a6b160279867bf34248150328391178`, module d128cdc5. Its __enter__ calls _ensure_owned and returns self without cleanup if validation raises. Python does not call __exit__ when __enter__ fails. This source observation was reported by A5/Root, then independently reproduced by A8 with actual own files/processes.

| Requirement ID | Repository / PR / exact HEAD | Test | Environment | Expected | Actual / status | Evidence | Severity / correction |
|---|---|---|---|---|---|---|---|
| A8-F28-ENTRY-CLEANUP | Grid PR277 /19fae71 above; Unified1f6 Journal support | Own sidecar fault after construction, before actual with entry; actual competing process | Own Windows CPython3.12.10, temporary synthetic Journal | Entry rejects unsafe sidecar and releases its owned handles/lock | FAIL: expected sidecar error, body not entered, _closed False and both held FDs still open; actual contender denied on retained lock | [Executed probe](executed.py), [original output](stdout.json), [raw source receipt](receipt.json) | P2 OPEN, separate local cleanup successor required |
| A8-F28-EXPLICIT-RECOVERY | Same source/probe | Remove only the known own sidecar and explicitly close owner | Same isolated store | Lock released after explicit cleanup | Actual next child ACQUIRED/effectfalse; both child calls returned0 | Same original output | Diagnostic recovery control, not an automatic fix or extra unique application PASS |

A8 constructed the real adapter and retained the synthetic original, then created a known owned sidecar. Failed with-entry raised SIDECAR_REQUIRES_EXPLICIT_OWNER_RECOVERY. Actual os.fstat succeeded for both retained FDs and a separate process was denied EXCLUSIVE_ROOT_JOURNAL_OWNERSHIP_UNAVAILABLE. After explicit owner close another process acquired the same Journal. Finally cleanup closes only own descriptors and removes only the known own sidecar; the temporary directory is retired. No native RPC, session, worker, provider, office or networking fault was executed. The CPython venv bootstrap is not native PID identity qualification.

815 Grid and1519 support primary files matched raw Git bytes before/after with no extras. This is one focused actual reproduction with two child observations; the full12 suite and old25 native cases were not rerun. Phase128's observed12 PASS remains valid for those covered cases, but it did not cover failed context entry. Normal-path local API review does not establish unconditional entry cleanup. A5 source-only receipt and Root owner claims are not counted as A8 execution.

Required correction: a separate local successor must release this object's owned descriptors if __enter__ validation fails, while re-raising the original entry error and preserving it if cleanup also reports failure. Do not delete persistent database/lock files or operate on foreign resources. Add actual failure-before-body regression, assert closed state and contender acquisition after safe removal of the test's own fault, and qualify exact source with primary pre/post checks. Native freeze remains blocked independently by F27 and other gates.

RELEASE_MANIFEST_STATUS: no approved release.
NODE_INVENTORY_STATUS: not requalified.
CONTRACT_STATUS: normal local scope retained; unconditional failed-entry cleanup NOT_ACCEPTED.
OFFLINE_TESTS: defect reproduced by one focused actual local probe; prior12 not rerun.
WINDOWS_CI: NOT_RUN here.
PHYSICAL_TESTS: BLOCKED.
P0_P1_P2: 8 open P1 /4 P2; absence of P0 not proven.
EVIDENCE: exact probe, original output, source maps above.
NEXT_ACTIONS: send finding to A2/Root and independently review separately committed cleanup successor.
GO_NO_GO: NO-GO; TAILSCALE_REMOVAL BLOCKED.
