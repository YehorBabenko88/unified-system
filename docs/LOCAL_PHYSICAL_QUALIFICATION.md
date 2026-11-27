# LS5/PC4 local research qualification

Owner authorization in the 2026-11-02 handoff covers isolated local experiments
on LS5 and PC4 only. It does not authorize ADMINIT or other office computers,
real exchange orders, production credentials, remote merges, or branch deletion.
Hosted CI entrypoints keep their original host restrictions. Never impersonate
GitHub Actions to execute them locally.

The first local diagnostic uses fresh directories below
`C:\Projects\UnifiedWorkspace\.local-runs\btc-20261102-01` on LS5 and
`C:\Projects\UnifiedLocalTests\btc-20261102-01` on PC4. Its exact Git bundles
are cloned without hardlinks; `core.autocrlf=false` is persisted in each capsule
before subsequent checkouts. SourceFence verifies raw capsule bytes and pins.
No installed office service or database is reused as test storage. Separate
loopback PostgreSQL clusters are initialized, queried and stopped. Native Job
diagnostics use the existing helper without invoking hosted CI scripts.

## Health deadline allocation

Native LS5 MetaAnalyse readiness revalidates the exact source tree on every
request. Measured checks exceeded the default 0.5-second process-driver deadline.
Combining `rev-parse HEAD --show-toplevel` saves a process launch while retaining
both identity checks. Index and untracked-source inspection remain separate:
combining their output permits ambiguous filenames on POSIX.

An operator-pinned program policy may explicitly set
`"health_timeout_seconds": 1.0` for MetaAnalyse. Omission still means 0.5 seconds.
Values must be finite numbers from 0.05 through 1.0; booleans are rejected.
The total positive increase over 0.5 seconds across all programs is at most
0.5 seconds. Both socket inactivity and absolute transport shutdown use the
selected deadline. The builtin profile keeps its four-second freshness limit;
its baseline budget including the allowed extra time totals 3.75 seconds.
Native process capture, output limits and hosted execution gates are unchanged.

This is a local diagnostic policy, not publisher admission, signed installer
acceptance, service enrollment, HA qualification, or a production trust bridge.

## Evidence boundaries

Keep six-profile readiness/authorization/stop smoke evidence separate from the
market experiments. The coordinator's database gate remains INFRA_ONLY; a
healthy API does not prove a connected market-data pipeline.

BTCUSDT linear candles are observed public REST data. Preserve raw responses,
database hashes, first/last timestamps and gaps; an empty pre-first-observation
range is not evidence that no earlier exchange history ever existed. Candles
are not historical trade tape. Live WebSocket trade, ticker and kline captures
run for 600 monotonic seconds per host and retain unfinished paper labels.
Receive-minus-exchange timestamps are not calibrated one-way network latency.

The existing 28 legacy Grid strategy variants run as offline research on the
same minute history on both hosts. The last 20 percent is a fixed chronological
holdout; no parameters are chosen from it. Legacy results include taker fees but
omit funding and slippage and allow concurrent entries, so their USD totals are
not funded-portfolio returns or promotion evidence. Keep every variant, including
negative results. No real exchange order or account API is needed.

Before claiming a new qualification, retain the exact source revisions, wheel
lock and archive hashes, pip check/import results, test logs, all failed attempts,
cleanup results and the experiment-driver bytes alongside the final reports.
