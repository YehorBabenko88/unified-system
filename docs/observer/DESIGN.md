# Unified Observer v1

This independent read-only monitor consumes explicitly configured exported JSON
snapshots and optional GET-only GitHub/status readers. It does not import or call
Scheduler, Authority, Supervisor mutation APIs, SSH, installers or trading code.
The existing supervisor API explicitly reports unqualified observations; its
availability is never installation, worker, token or physical acceptance evidence.

The implementation uses Python 3.11+ standard library only. Snapshot adapters are
the default: opening the live Mission Controller SQLite journal is deliberately
unsupported, including apparently read-only connections that could create WAL
sidecars. A timestamped exported projection is a separate input, never authority.

Each fact carries its own section/subject/field, status, source ID, exact source
version, raw input SHA256, observation time, policy TTL and last successful time.
An explicit source policy lists which field scopes it may report as PASS. An
unqualified PASS becomes UNKNOWN. Synthetic sources cannot assert physical
acceptance or committed publication. LOCAL_UNATTESTED never becomes COMMITTED.
Expired facts become STALE independently; source failure cannot refresh them or
manufacture node disconnection. No status is inferred from a neighbouring axis.

The only writes are in a new marked Observer state directory. Owned SQLite state
persists facts, bounded events, rate reservations and an outbox. An in-flight send
at crash/restart becomes UNKNOWN and is not automatically retried. Definitive
not-sent delivery backs off; successful or ambiguous delivery remains deduplicated.
Alerts use closed templates and safe identifiers, not source bodies, paths,
addresses, credentials or diagnostics. Telegram is opt-in with explicit test
credentials and separate network admission; mock transport is the initial mode.

The dashboard and health API are GET-only WSGI. The optional foreground server
binds only 127.0.0.1; default execution opens no listener. Polling is serial and
bounded, with at most sixteen sources and minimum intervals; no repair actions.
LS5 service installation and physical/network admission remain BLOCKED.

Ownership: unified_system/observer, tests/observer, docs/observer, tools/observer,
and a dedicated new observer-offline workflow only. Shared APIs stay unchanged.

## Implementation plan

- [ ] Write and execute failing offline model/store/notification/API tests.
- [ ] Implement strict facts, scoped sources and stale handling.
- [ ] Implement owned bounded state, recovery and notification delivery states.
- [ ] Implement serial runtime, read-only dashboard and foreground CLI.
- [ ] Add read-only adapter tests, mutation-denial and resource-boundary checks.
- [ ] Run exact offline suite; save original RED and GREEN evidence.
- [ ] Commit separate feature branch; Root reviews source/cohort before one push.
- [ ] Independent A8 and hosted qualification; no physical PASS transfer.

## Remaining admission

Real Telegram test delivery needs protected test credentials/destination and an
explicit network permit. Existing authenticated health endpoints/read-only source
credentials, approved source-scope policies, LS5 nonadmin execution and state ACLs
must be qualified separately. This feature never grants native or trading access.
