# ADMINIT acceptance preparation

**Preparation only. Owner grant: null. Physical execution: false. Inventory,
PowerShell 5.1/7 parser/native execution, public API observations, and physical
acceptance: NOT_RUN.** Do not connect to ADMINIT, install anything, execute the
collector, change services or databases, or run physical scenarios until a
separate explicit grant after cloud development. No actual instrument is claimed
available by this document or its unit fixtures.

Use `adminit_acceptance.prepare(release_sha=EXACT_RELEASE_COMMIT,
publisher_sha256=EXTERNALLY_PROVISIONED_PUBLISHER_PIN, run_id=UNIQUE_RUN_ID)`.
The output is the ADMINIT-specific preparation manifest. Both pins are required;
a publisher fingerprint inside a package cannot establish its own trust. Bind
this preparation to the separately verified `unified.release.v3` manifest and
immutable artifact hashes. Never infer release admission from CI green alone.
`owner_grant` stays null and `physical_execution` stays false in this preparation
schema. A future execution tool must independently verify a separately issued,
scoped, expiring owner grant; this ledger cannot grant it.

## Local inventory preparation

`Collect-AdminitInventory.ps1` contains only local reads and JSON stdout. It has
no remote endpoint arguments or transport. It does not create files, start
programs, install dependencies, query network peers, or modify services. **Do not
invoke it now.** Its eventual output contains local host/service information;
keep it private and publish only reviewed, sanitized summaries and hashes.
Do not use existing credentials or collect environment variables/secrets.

After a separate grant, verify local host identity against owner inventory and
record OS/build, Python/Node/PostgreSQL/Git versions, executable hashes and
signature trust independently. The collector reports OS caption, edition SKU, build, version and architecture.
Dependency candidates use fixed absolute local C: paths, with file-version
metadata only: Python at C:\Python313, Node at C:\Program Files\nodejs,
PostgreSQL18 at C:\Program Files\PostgreSQL\18\bin, and Git at
C:\Program Files\Git\cmd. It never searches PATH or executes dependency
binaries. Missing candidates/version metadata block; other installation layouts
require a reviewed local-path change, never automatic PATH discovery. Versions
are observations only; compatibility and publisher trust need independent checks.
The C: drive must be fixed/local. Ancestors are checked in order; blocked/reparse
parents stop all descendant access, including the PostgreSQL data check. Unknown
namespace existence is reported as null and blocks. These portable lexical and
metadata checks do not provide native confinement against concurrent namespace
replacement; future execution requires independent native write confinement.
Check 4 logical CPUs, 8 GiB RAM and 20 GiB free C: space as **proposed isolated
test minimums**, then measure actual workload capacity. Insufficient or unknown
values block. Service names with case-insensitive `UnifiedAdminitTest-` prefix
conflict. The fixed `C:\UnifiedAdminitTest` namespace and `postgres-data` child
must not preexist or traverse a reparse/link namespace. Independently recheck
path identity at any future write; inventory has no race-resistant write grant.
Choose unoccupied loopback-only ports after grant; never reuse the production
PostgreSQL service, credentials, data directory, port or database. PostgreSQL
initialization and fault injection belong only to a new test data directory.

## Phase A–G ledger

Every phase initially remains NOT_RUN. Each claimed record requires exact
ADMINIT node, release SHA, run ID, observation timestamp, PASS/FAIL, evidence
SHA256 and detached-signature SHA256. Keep the actual evidence bytes and
signatures separately. An independent verifier must check signatures against the
external publisher/owner policy and bind observations to the real run/host.
A hash of a signature is only a reference. Self-consistent claims, including
fabricated PASS claims, remain RECORDED_UNVERIFIED; failed or missing phases
block. No accepted record changes deployment authorization.

| Phase | Future evidence required after separate grant |
| --- | --- |
| A | Explicit scoped grant; inventory; no conflicts; exact clean sources; external publisher/signature/artifact verification; dependency versions; isolated paths and ports. |
| B | Install only receipt-listed test files/services; dependency order and all six module health/readiness; administrative stop; uninstall and data-preserving cleanup rehearsal. |
| C | Ten confirmed instruments; real historical coverage; reproducible sealed input/result receipts; declared fees/slippage/funding; chronological training/validation/heldout split; availability and no-lookahead checks. |
| D | Read-only public feed; sequence/gap/staleness diagnostics; reconnect and bounded retry; bounded queues/backpressure/drop accounting; paper-only analytics and Terminan visibility; no order endpoint or credential access. |
| E | Controlled faults limited to receipt-listed test processes, test ports, test databases and test-root files; timeout, worker exit, malformed input, disk quota and feed interruption; recovery and no duplicate task execution. |
| F | Immutable verified candidate update; explicit canary; health failure; rollback to preserved known-good test release; schema compatibility and reproducibility; interrupted update recovery. |
| G | P0/P1/P2 defect triage, GitHub source fix and reviewed exact commit; targeted regression plus affected matrix; rerun failed phase and dependencies; independent evidence review and owner decision. |

Never kill unrelated services/processes, disable host firewall/security policy,
interrupt the physical host network, fill the system disk, reboot ADMINIT, or
modify real databases as a fault mechanism. Use bounded synthetic failures
inside the isolated application test boundary. Set duration/CPU/memory/disk/queue
budgets before each future scenario, establish abort/stop criteria, and preserve
logs/receipts. P0 blocks immediately; P1 blocks phase progression; P2 requires
recorded disposition and retest. Do not relabel defects or skip checks for green.

Rollback restores **only the isolated test namespace** from a verified retained
release. Uninstall removes only receipt-listed test services/files, preserves
historical data, backups and evidence, and leaves a manifest of retained data.
Never remove the only dataset/backup copy, active release or recovery bundle.
Existing external services/data require explicit separate scope, never inference.

One ADMINIT cannot establish quorum, split-brain prevention, replicated DB HA,
one-/two-node loss behavior or five-/six-node acceptance. Use the existing
`physical_acceptance` fleet ledger for that separate future work; these A–G
records do not replace its per-node scenarios.

## Ten instruments: observation, not a hardcoded availability claim

Select exactly ten unique symbols only after real public API collection reports
`category=linear`, `quoteCoin=USDT`, `contractType=LinearPerpetual`, and
`status=Trading`. Paginate the actual instruments response, retain capture source,
observation timestamp and response hash, and reject incomplete discovery.
Current Trading status does **not** establish historical availability. Obtain
actual historical responses for every selected symbol and proposed interval;
record launch/delisting limits, bar closure, missing intervals, endpoint retention,
first/last availability, watermarks, revisions and coverage. Do not stretch the
interval or invent bars. Funding/open-interest/trade archive coverage requires
its own endpoint evidence; kline coverage cannot qualify those datasets.

`validate_instruments` checks a ten-item claimed evidence index, exact sources,
Trading/type/quote fields, requested/available bounds and digest shapes. It never
fetches data or confirms the captured responses. `AUTHENTICATED` is the required
real-origin claim; the returned authenticity remains UNVERIFIED until independent
response/source verification. `SYNTHETIC` unit fixtures cannot qualify an actual
instrument. `OBSERVED_COMPLETE` must be backed by gap checks on actual rows, not
just first/last timestamps. Include explicit historical-availability assumptions
in the eventual result, plus fees, slippage, funding, costs and chronological
heldout boundaries. Refit/training must never consume heldout/future availability.
No exchange credentials, account endpoint or real order is needed or permitted.

## Precise public network requirements (static inspection only)

No office or public-feed request was executed for this preparation. Existing
Grid config/provenance and Strattester Bybit client reference:

| Host | Transport/port | Scope |
| --- | --- | --- |
| api.bybit.com | HTTPS 443 | Public `/v5/market/instruments-info`, kline, mark/index/premium price, funding, open-interest and long-short-ratio endpoints used by existing clients. |
| stream.bybit.com | WSS 443 | `/v5/public/linear` market data only. |
| public.bybit.com | HTTPS 443 | Optional `/trading` public trade archive, only when requested datasets need it. |

DNS resolution and TLS trust must follow existing host/network policy. Do not
use mirrors, private/account/order routes or arbitrary redirects. HTTP403 means
blocked, not permission to bypass. Rate-limit/retry/backpressure budgets and
response-size bounds remain enforced. These hosts are separate from the exact
GitHub Actions log/artifact redirect allowlist prepared during Mission3.
