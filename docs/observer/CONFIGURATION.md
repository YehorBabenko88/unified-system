# Input configuration v1

The config is a bounded JSON object with `schema: unified.observer.config.v1`
and a `sources` list. Each file source specifies `id`, `kind`, absolute `path`,
exact40/64-hex `source_version`, optional `ttl_seconds`, `interval_seconds`,
`admitted_axes` and `mode`. No credentials belong in this file. A source version
must match its exported producer version; filesystem mtime is not an observation.

Canonical snapshot fields are exactly `schema`, `source_version`, `observed_at`,
`facts`. The schema is `unified.observer.source.v1`; UTC timestamps are required.
Each fact has `section`, `subject`, `field`, `scope`, `status`, `value`. Only the
Observer's closed field/value sets are displayed. Raw diagnostics, paths, tokens,
internal addresses and free-form source bodies are not copied into notifications.

Modes: SYNTHETIC, UNQUALIFIED, QUALIFIED. Mode is a separately reviewed source
policy, not cryptographic proof or an Authority grant. Explicit PASS scopes must
be admitted individually. PHYSICAL_ACCEPTED additionally needs a QUALIFIED
A8 acceptance source; verified publication needs a qualified COMMITTED report.
LOCAL_UNATTESTED and COMMIT_UNCONFIRMED remain blocked for verified publication.

Mission export schema is `unified.observer.mission-export.v1`: exactly four fields
`schema`, `source_version`, `observed_at`, `projection`. Projection uses the existing
Mission Controller detached JSON data, optionally same-sequence continuations.
Only sequence, bounded status counters and whitelisted Root task fields are
shown. Requirements, descriptions, private evidence references and full receipts
are never displayed. Export provenance and age remain visible; this is not a
direct live-journal reader, new Mission Controller or autonomous coding agent.

Agent2 BLOCKED_COMMUNICATION can be supplied as an explicit AGENT_STATE fact.
It persists as last known state with STALE once evidence expires. Source failure
never means resumed, and the Observer never delivers prompts to that agent.
