# F13 safeguard exact-source review

Requirement: retired historical data preservation; no automatic deletion or DB acquisition.
Repository: bybit-cluster-grid; Draft PR263; exact HEADec967b3ebb67bb9f04d0d82c78bba5b4245a3333; tree8dce2883766a9b492587a91dda5ff86d881d83ac; basea17f1db6b9aa04c105d2e993496026a83849ecfd.
Environment: Windows independent exact-LF clone; Python auditor venv/pytest8.4.2, synthetic fixtures; loopback-only socket policy for regression child.

Expected: same async signature/default and [] result, preserve all other module behavior, no pool acquire/SQL/destruction.
Actual: PASS in offline exact-source scope. Original independent fake oracle reexecuted: baseline six DELETE, fixed zero pool calls and []; no-acquire sentinel passes default and grace0/365/-1/1000000; None pool also returns[]. Exact three allocated diff paths only. AST equality proves imports/schema/reconcile and all module statements outside purge unchanged; argument AST unchanged. Whole raw tracked Git tree matches committed blobs before/after.

Independently ran the four new safety regression cases against original base:4/4 assertion failures,0errors/skips. Fixed five targeted files:16/16 PASS0skip/error. The preserved-history in-memory fixture retains all six table-record lists. No real database or deletion was used. Existing unrelated tests/assertions remain byte-identical by the complete three-path diff.

F13 FIX_VERIFIED_OFFLINE_EXACT_SOURCE only at this pin. Old deployed/baseline code is not repaired by this review; integration must explicitly adopt reviewed source and qualify relevant CI before any runtime release. New cleanup/retention protocol is absent and unqualified; this safeguard disables only the existing deletion path. Full Grid suite, hosted Windows/PG/native, actual storage durability and physical acceptance NOT_QUALIFIED. Overall NO-GO,6P1/1P2open; physical fault injection and Tailscale removal BLOCKED.

Evidence: history-safeguard-review.json; red/green original stdout/stderr/JUnit; independent reproducer ../verify_history_safeguard.py and original phase14 fake oracle. Issue owner and Integration Owner receive this scoped closure. No production implementation changed by A8.
