# Retired history preservation negative probe

Requirement: preserve historical data; no unauthorized deletion, replica/pin/consumer safety.
Repository: bybit-cluster-grid; PR262 source HEADa17f1db6b9aa04c105d2e993496026a83849ecfd; treed45f5bf45d08f7d336fc82e376cc88915c57d84b; file grid/instrument_lifecycle.py:64, Git blob74d462ee6865ec88ed72749b3c87803bb00ff7b5. Existing pre-fixture source path, not introduced by PR262 fixture correction.
Environment: independent Windows exact-LF source import; only in-memory fake connection/pool, synthetic retired symbol, no database, socket, real order or physical action.

Expected safety invariant: no deletion based solely on retirement age and absence of queued/running strategy jobs without separately admitted retention/replica/consumer protection.
Actual: FAIL, A8-F13 P1 OPEN. Exact unmodified function records SELECT retired candidates, strategy busy query returning false, then six DELETE statements: five raw/derived history tables plus instruments. No retention approval, pin/reference/last-copy check is present in this function. Ordinary coordinator ACTIVE refresh invokes it at grid/coordinator.py:953 after prior discovery/reconcile operations succeed. Missing/default runtime is not asserted ACTIVE; currently Trading rows are not initial SELECT candidates. No claim that every install executes purge or that production deletion occurred.

Original Agent3 audit/evidence was inspected, then independently reproduced on the newer exact candidate. Its Windows CRLF SHA256 differs from this LF checkout; matching Git blob establishes source identity rather than pretending raw hashes equal. A3 corrective Draft/source pin is forthcoming; no production implementation edited by A8. Required correction: disable the narrow deletion path pending an explicit separately approved retention protocol, then review exact fix/tests; no real DB scenario authorized. Actual PostgreSQL durability, concurrency races and deployed state NOT_RUN.

Evidence: retired-history-probe.json contains all fake calls/source hash/result; reproducer ../probe_retired_history.py. Overall NO-GO;7P1/2P2open; physical fault injection and Tailscale removal BLOCKED. Issue passed to ROOT and A3 owner.

Later bounded correction: F12 independently resolved at084ef2ec3b42131b12af44103f2d21845bf1c0f7, revision5 SHA0ef0dde1f6b238e87b60e2e21eeb13466f6b5e39c3815d91b39890134c982bdd. A8base and PR26 linkage corrected, historical pins separately labeled; all allocation paths unchanged. Fresh ACK only A8 own prefix, no global or prior ACK transfer. No tests rerun for three documentary-only paths. F13 remains OPEN pending exact fix. Current total7P1/1P2; overall NO-GO.
