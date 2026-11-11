# Observer install, run and rollback plan

Status: code and offline tests only. No LS5 listener, Windows Service, node access,
database connection or real Telegram delivery is admitted by this document.

## Admission and first foreground observation

1. Freeze the exact feature HEAD/tree and source receipt. Review the separate
   Draft PR, dedicated Windows/Ubuntu results and A8 evidence. The rest of the
   MASTER CI is independent; Observer unit PASS does not close those gates.
2. Qualify an existing nonadministrative local account, Python executable and
   state directory ACLs. Do not change UAC, ESET, Firewall, SSH or network policy.
3. Supply a read-only source export, its exact producer version and trustworthy
   observed timestamp. An export is a timestamped observation, not independent
   live-journal polling. Observer never opens the input as SQLite.
4. Use an absolute new directory for Observer state and an absolute JSON config:

   `python -I -S -B -m unified_system.observer --config <absolute-config> --state-dir <new-owned-state> --once --export-dashboard`

   With `-I`, install the reviewed package into an isolated application environment
   first; the repository test runner supplies an explicit exact-source capsule.
   No pip/network installation or Windows Service creation is automated here.
5. Inspect `dashboard.html` in the owned state directory and the bounded result.
   Default notifications are DISABLED. `--mock-notifications` is explicitly mock
   delivery, not Telegram. No listener starts unless separately selected.

## Independent runtime

The foreground CLI uses a serial polling loop and handles SIGINT/SIGTERM. Its
optional listener is fixed to `127.0.0.1`, with GET-only `/`, `/api/status`,
`/healthz` and `/app.css`; no command or repair routes exist. Listener activation
requires the separate owner permission and local resources/rights qualification.
Port8769 is a proposed default, not an observed address or opened port.

Sources are bounded to16. Snapshot polling defaults to60s; fields expire using
their own policy TTL. Facts are capped at512, individual source bytes at1MiB,
fact rows at4KiB, CI history at16 rows/source, and a GitHub page at10 rows.
The dashboard explicitly labels bounded CI reporting rather than full-matrix
qualification. Raw or unqualified report claims never issue native permission.

Owned SQLite uses a distinct application ID/schema/state marker,8MiB page budget,
2MiB cache and18MiB directory budget. Foreign/linked/WAL database headers are
rejected before connect. State has at most256 pending/unknown notifications,
512 visible events and8192 deduplication identities. Sent event compaction cannot
erase deduplication. At dedupe capacity, operator archive is required rather than
silently resending. No existing source or trading database is migrated or pruned.

Notification rate reservations persist across restart: default one attempt/minute
and60/day. Definitive mock not-sent stays queued with backoff. A lost response or
crash during SENDING becomes UNKNOWN and is not automatically retried. Messages
use closed templates; event rows retain their transport mode. Test bot credentials
must remain outside repositories/state/logs. Actual Telegram delivery needs its
own protected credentials, destination and network admission.

Optional GitHub HTTPS readers use exact public repository GET URLs, verified TLS,
no redirects or ambient proxies, bounded responses and observed read deadlines.
No token is discovered automatically or reused from Codex/Git. The initial CLI
config accepts only file exports; live read admission and persisted global GitHub
rate accounting are a separate qualification before operational API polling.

Application byte/count/cache bounds are not an OS CPU/RSS hard limit, hostile
interpreter sandbox, strict kernel deadline or full DLL-origin qualification.
Before LS5 admission, measure resources and slow-client/shutdown behavior and
qualify the chosen account/environment. No physical PASS is inferred from CI.

## Safe stop, recovery and rollback

Stop only this foreground process with its normal stop signal. The runtime stops
starting new polls and closes its own optional server and state connection. Never
restart network services or other applications. Retain state and evidence.

Restart the same reviewed version with the same owned state. Foreign schema,
corruption, disk exhaustion and unconfirmed delivery fail closed; no repair or
automatic resend is performed. Roll back code to a previously reviewed exact
artifact. Preserve the current state before selecting a separately approved
compatible state copy; do not overwrite a newer database or delete user data.
Windows Service installation, service-account provisioning and automatic startup
remain a future separately approved installation action.

## Protocol sources

Telegram test adapter follows the HTTPS JSON `sendMessage` response `ok` contract:
[Telegram Bot API](https://core.telegram.org/bots/api#sendmessage). No actual bot
request was made during offline tests. Live delivery and provider quotas remain
separate evidence.
