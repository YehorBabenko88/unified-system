# LAB_SIMULATION startup admission (Workstream C, unified-system#153)

Separate, explicitly authorized path for local laboratory simulation. `lab_runtime --execute`
and the protected Windows service activation are **unchanged** and still refuse.

| Requirement (owner decision) | Enforcement |
|---|---|
| Only loopback | children bind 127.0.0.1; DSN must be `postgresql://user:pw@127.0.0.1|localhost:port/db` |
| Only own temporary resources | `mkdtemp(unified-lab-*)`, 0700, owner marker + (dev, inode); cleanup refuses anything else |
| No real trading | authorization must say `trading_authorized:false`; env `UNIFIED_TRADING_AUTHORIZED=false`, `PAPER_ONLY` |
| No production credentials | child env is allow-list only; credential-like names refused (`BYBIT`, `SECRET`, `PASSWORD`, `*_DSN`, …) |
| Explicit permission | operator authorization JSON, ≤24 h, bound to the exact components digest |
| Verifiable identity | sha256 of every admitted file per module; child re-verifies its own package before importing; links, `__pycache__`, `.pyc` refused |
| Child lifecycle | stdin lifeline: when the supervisor closes it (or dies) admission is revoked and the child exits; then terminate/kill fallback |
| Clean stop and cleanup | report records LIFELINE/TERMINATED/KILLED, exit codes, cleaned=true |
| Fail-closed | any mismatch → nothing started (or everything stopped and cleaned) and `BLOCKED:` |

Runtime checks on every `require_current()`: not revoked, before deadline, temp identity
unchanged, no admitted file changed (size/mtime/inode).

Local evidence (2026-11-25, Linux): market_data (strattester@3850995 tree) + math@9e6acbd + Terminan@353d16b:
both modules ready with authenticated health 200, unauthenticated health 401/503, Terminan read path
`CONNECTED_UNQUALIFIED`, both stopped by LIFELINE with exit 0, temp removed, `BYBIT_API_KEY` not forwarded.

Limits: no market rows yet — market_data returns `SOURCE_PROVENANCE_UNAVAILABLE` until qualified
provenance data exists (next: C2 temporary PostgreSQL lifecycle with synthetic provenance rows; C3 paper
strategy via Math). Dependency site-packages are not hashed. Release: NO_GO.
