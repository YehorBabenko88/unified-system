# Operator identity and distributed control plane

Status: PROPOSED CONTRACT; source inspection only, runtime NOT_WIRED,
authentication NOT_IMPLEMENTED, physical acceptance NOT_RUN, production NO_GO.
Baseline Unified `1c1ee336178b2ad9d807bb1c691acda95201f188`; inspected Grid
`5765fac688e31c412ef78cebc4b201743dd62d78`, Terminan
`7ed3708df53c8850fd11fc8331440bdfee99aa3e`. No credential, account, service,
network or database changes accompany this document.

## Existing mechanisms to retain

* Unified `lifecycle.py`, `lifecycle_api.py` and `fleet_snapshot.py` already
  validate read-only PLAN_ONLY snapshots. Extend their adapters after review;
  do not turn a planning snapshot into runtime authority.
* Unified `fleet_control.py` explicitly models disposable SQLite state and
  caller-supplied votes. It is not HA, an identity registry or production audit.
* Unified runtime source entry, release boundary, service activation and owned
  process health remain release/process admission gates. Their boolean callbacks,
  environment metadata and offline credential files cannot authenticate humans.
* Terminan `unified_server.py` retains loopback Host/Origin checks, request bounds
  and existing Saved/R4 guards. `r4_session.py` says SYNTHETIC_ONLY explicitly.
  Module-health bearer nonce authenticates an owned process, not its user.
  `server.py` rejects remote bind pending authentication. Preserve that denial.
* Grid `telegram_bot.py:allowed` permits a bounded read-only operation allowlist;
  chat membership alone is insufficient. `telegram_idempotency.py` and migration
  49 atomically bind sender, delivery and operation and reserve completion audit
  capacity. Reuse the invariants; its `authorized` boolean is not a reusable
  authentication factory and Telegram identity is not an owner credential.
* Grid `enrollment.py` gives node roles from server-authorized enrollment. Keep
  machine enrollment distinct from human permissions.
* Grid `command_receipts.py` reserves before effects and refuses pending outcome
  replay or unsafe eviction. These local receipts complement, but cannot replace,
  replicated command admission and aggregate CAS.
* Existing Grid Consul session/index, KV transaction CAS and SQL executor/projection
  fences own coordination. No second leader service, scheduler or authority DB.
  The HA ADR's independent Windows watchdog and legacy-write cutover remain P0.

## Human and machine identity

`actor_id` is an opaque stable cluster operator identifier. A trusted backend
binding maps an authenticated human identity to this id and current grant
revision. Do not derive it from the server process SID, request JSON, a role
header, node certificate, module nonce, environment flag or Telegram chat.
Principal kinds HUMAN, NODE and SERVICE are disjoint. NODE/SERVICE cannot receive
human grants or claim SystemOwner even when their process runs as administrator.

Proposed first provider is Windows integrated authentication through an admitted
SSPI/Negotiate adapter which verifies the remote human security context and maps
it to a pre-enrolled operator. This is a proposal, not a claim the six machines
share a domain or usable trust relationship. Domain/workgroup identity authority,
server identity/SPN/trust configuration, channel binding, replay protection and
credential delegation policy must be established in a separately reviewed setup.
Do not add SeImpersonate privileges, DisableLoopbackCheck, registry bypasses or
NTLM relay/channel-binding exceptions to make a prototype work. A mature admitted
provider adapter (for example pyspnego or sspilib after dependency review) is a
qualification candidate; custom cryptography or fake JWTs are excluded.
If that deployment cannot support a single verified identity namespace, use a
reviewed standards-based human identity provider rather than inventing tickets.

Only the admitted startup factory may construct the verifier and session service
from reviewed source/release inputs and actual OS/provider verification. A caller
cannot inject a truthy verifier, serialize an authenticated context, or activate
mutations through configuration. Missing provider, trust, grant registry or audit
availability means AUTHENTICATION_UNAVAILABLE and no mutation. Offline test
fixtures remain visibly non-authoritative and cannot enter the runtime factory.

Terminan stores no password or node secret. Prefer integrated authentication;
where a provider needs refresh material, use per-human Windows Credential Manager
via a reviewed adapter, never localStorage, URL, logs, plaintext config or shared
machine/service vault. Bind opaque sessions to human, provider, grant revision,
expiry and revocation epoch. Store only token digests server-side; rotate refresh
tokens atomically and revoke on reuse, logout or grant change. Use TLS with actual
admitted server identity; no fabricated certificates, pins or test bypasses.
Browser cookies require Secure, HttpOnly, SameSite and explicit CSRF protection.

## Backend capability policy

| Role | Maximum permitted capabilities |
| --- | --- |
| Viewer | Redacted status, snapshots, progress and authorized audit reads |
| ResearchOperator | Viewer plus approved research/history/subscription/paper intents; no real orders |
| ClusterAdministrator | ResearchOperator plus reviewed node schedules, resource policy and non-destructive cluster administration |
| SystemOwner | Explicit owner grant; identity/grant changes, recovery, critical lifecycle and purge intents subject to step-up and concrete confirmation |

Role labels do not bypass action/resource checks. Each route and downstream
executor checks the current human grant, scope, quorum and fence. Unknown actions
deny; owning a node or service confers no capability. Critical actions, including
full purge and owner grant/recovery changes, need fresh owner authentication and
an independently submitted concrete confirmation bound to actor, session,
command digest, dry-run inventory hash, revision, expiry and one-use nonce.
An old login, UI checkbox, `confirmed=true`, AI instruction or role field is
insufficient. No actual purge implementation is introduced here.

## Command contract and HA reconciliation

Proposed external envelope, strict bounded canonical JSON with unknown fields
rejected and the HA ADR's 32 KiB limit applied to the entire envelope:

```
schema, command_id, actor_id, idempotency_key, generation,
aggregate_type, aggregate_id, expected_revision, action, payload
```

`command_id` is UUID. The server derives canonical `actor_id` from the verified
human session. A submitted actor assertion must match that value or be rejected;
it never authenticates the caller. `expected_revision` is the aggregate's
durable revision and maps exactly to the HA bridge's `expected_version`; do not
accept independently supplied aliases or requests containing both names. Legacy
translation exists only inside the admitted adapter. `generation` prevents replay across
restores/reinitialization. Revisions are bounded integers with booleans rejected.
The root must reconcile this mapping with the HA schema before implementation.

Idempotency scope is `(generation, actor_id, idempotency_key)`, independent of UI
window, session or coordinator. Replicated admission also uniquely binds
`command_id`. Persist the canonical intent digest, actor/grant admission revision,
aggregate expected revision and durable receipt together under the existing
Consul transaction/CAS boundary; command identifiers also carry immutable
principal/generation ownership and cannot be claimed by another principal.
Same binding and digest returns the prior
receipt; reused key/id with another digest or actor yields IDEMPOTENCY_CONFLICT.
Changed expected revision is a changed intent; a conflict requires refresh and
a deliberate new command/key. Never silently retry a stale write as a new intent.

Authorization is rechecked before disclosure/replay and at fenced effect
execution. A retry cannot revive revoked authority. A reserved command with an
unknown effect stays UNKNOWN/PENDING_RECONCILIATION until its existing executor
receipt is reconciled, never executes again solely because a response was lost.
Exactly-once external effects are not promised. The SQL projection is recoverable
and fenced under the existing Grid path, not another source of truth.

## Proposed API ownership and client behavior

New reviewed coordinator routes, all NOT_IMPLEMENTED:

| Surface | Purpose |
| --- | --- |
| `POST /control/v1/sessions` | Provider-backed human login; no JSON credentials or self-selected roles |
| `DELETE /control/v1/sessions/current` | Audited revocation, no service stop |
| `POST /control/v1/reauth` | Fresh provider ceremony and action-bound challenge |
| `POST /control/v1/confirmations` | Separate concrete owner confirmation after reviewed dry run |
| `POST /control/v1/commands` | Strict authenticated intent admission |
| `GET /control/v1/commands/{command_id}` | Authorized durable operation receipt/progress |
| `GET /control/v1/snapshot` | Consistent authorized snapshot and resume cursor |
| `GET /control/v1/events` | Bounded resumable authorized event delivery |

Snapshot includes cluster generation, durable revision, event sequence, producer,
observation time, freshness bound and explicit quorum observation. Snapshot and
cursor are captured at one consistent boundary. Events carry generation,
sequence, aggregate revision and receipt reference. Reconnect resumes after the
snapshot cursor; duplicate events are harmless, a gap/expired cursor/generation
change forces a new snapshot. Domain revision, event sequence, Consul index and
leader epoch have separate meanings; none is silently substituted for another.

LIVE requires an authenticated current snapshot plus contiguous events within
the freshness bound and quorum confirmed by the authority. STALE marks expired
data; RECONNECTING marks bounded failover retry; OFFLINE means no authenticated
endpoint; NO_QUORUM requires an authenticated authority observation and forbids
mutations. Network failure alone does not prove no quorum. Display last revision,
observation time and reason; stale values never retain a live badge.

Terminan tries only admitted LS5/PC4/PC3 endpoints, verifying each server identity.
On unknown submit outcome, query the same command receipt before resubmitting the
same envelope. Do not create a new key on reconnect. Operation progress is durable
backend state, not a browser timer. Opening/closing any number of Terminan windows
never starts/stops coordinator duties or services. Per-operator preferences are
separate revisioned state; they do not confer authority or own job lifetime.

## Audit, recovery and acceptance gates

Admission and every terminal result require durable replicated audit capacity;
no mutation on unavailable quorum/audit. Record actor/provider reference, session
digest, grant revision, command/digest, object revision, fence, decision, time and
recovery/confirmation references without credentials. Retain receipt replay
tombstones; no age-only eviction. Export verifiable evidence to an independently
protected destination before any approved destructive lifecycle operation.

Owner recovery uses a separately pre-enrolled recovery factor and reviewed
quorum-backed recovery policy. It creates a bounded recovery intent, verifies the
human factor, records immutable audit, revokes affected sessions, and commits the
new grant revision before use. No default owner, local admin override, deleted
database bootstrap, environment ticket or audit-disabled break-glass path. Loss
of all admitted recovery factors is BLOCKED pending an explicitly designed
offline ceremony; this document does not grant anyone an owner identity.

Planned offline contract tests: forged JSON actor/role; service-owner escalation;
expired/revoked session; replayed step-up/confirmation; payload/key mismatch;
same-intent two-window race; stale aggregate conflict; lost-response reconciliation;
cursor gaps/generation reset; audit capacity failure; no-quorum denial; UI close
without backend stop; recovery audit failure. Provider integration tests must use
real OS/provider evidence in an isolated environment before physical admission.
No local model result qualifies distributed persistence or human authentication.

File scope proposed for the next reviewed step: additive
`unified_system/operator_control_plane.py` for non-authoritative strict contracts
and `tests/test_operator_control_plane.py` for bounded offline contract tests.
Runtime auth/session factory, Grid authority/schema edits, Terminan remote binding,
real credentials and destructive executors are excluded until their prerequisites
are implemented and reviewed. LAN transport/private pins belong to the transport
workstream; HA ADR belongs to its owner. Commercial signing may independently be
TRUSTED_RELEASE_BLOCKED; LAB unsigned status never unlocks operator authority.
