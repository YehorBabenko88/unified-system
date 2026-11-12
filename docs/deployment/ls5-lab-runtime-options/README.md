# LS5 persistent LAB runtime: A/B decision and gated plan

**Recommendation: B, CONDITIONAL. Current status: NO-GO for installation.**
This is a documentation proposal, not an executable installation or an authority
grant. No account, service, ACL, database, listener, network setting or provider
access is changed by this PR. Evidence is scoped as of 2026-11-12; read-only
resource observations are not current availability or database authorization.

## Source boundary

The inspected Unified protected-service component is
`1b42d4cb1392eaf11af8d32ed34fcdcd65ffc5d2`, tree
`4b9363afba7b8ff61b4c059e62a173074379db6c`. It is **not an assembled, approved
Collector release**. Grid PR285 source
`573e3ff84b50941f5929e9c69b37a01fca60ccdb` is a separate route: its legacy SYSTEM
scheduled-task installer is not the Unified LocalService installation path.
Neither source is adopted into this docs branch. Freeze the integrated candidate,
role, entrypoint and immutable capsule before any installation decision.

## A versus B

| Concern | A: dedicated nonadmin user | B: LocalService plus dedicated service SID |
|---|---|---|
| Identity | Suitable existing account and launch channel are unconfirmed. Creating an account or assigning rights requires a separate concrete plan. | Built-in identity avoids a new password/account, but service registration and exact service-SID ownership still require admission. |
| Existing launcher | The developer pilot checks a non-elevated token; a filtered Administrators-member token may pass. This does not prove dedicated nonadmin membership or unattended launch. | Existing protected bootstrap requires LocalService and exactly one enabled service SID. A regular user is rejected; do not weaken this gate to support A. |
| Persistence | A foreground/logon-only launch does not establish reboot-independent operation. | Suitable headless architecture, but current contract is MANUAL/STOPPED, AppExit=Exit, no SCM failure actions or triggers. It does not provide boot/recovery persistence. |
| State and secrets | Dedicated state; admitted code must remain unwritable. No broad operator-profile access. | State access is per-service-SID, not a broad LocalService write grant. Code, dependencies and protected activation material remain sealed to the exact contract. |
| Database | Windows identity confers no database role or authorization. | Same. Require a separately owned, authenticated, non-superuser database boundary; do not adopt an installed service, occupied port or existing database. |
| UI and health | Interactive UI remains a separate user application. | Headless Session0 backend must not depend on desktop prompts. Authenticated loopback health is not proof of raw capture or durable publication. |
| Network/isolation | Nonadmin is not complete resource containment. | Service SID type 1 is not a restricted-token/network sandbox. Ordinary outbound sockets remain possible; application permissions, TLS, quotas and fencing remain required. |
| Stop and recovery | Console closure is not proven graceful retirement or reconciliation. | SCM state is not application health. NSSM signal delivery, owned-child/database retirement and restart reconciliation need actual qualification. |

Choose B as the target architecture for the protected headless Collector. Keep A
as a separately qualified development/pilot option. This selects a design; it
does not select an installed runtime, qualify Session0 or authorize deployment.

## Release-critical blockers

1. **Entrypoint/profile:** the existing fixed service argv is
   `-I -S -B service_entry.py`, selecting full protected runtime by default, not
   `--data-first`. A data-only Collector needs a versioned reviewed launch profile;
   do not substitute arguments inside the admitted plan or start full runtime as
   a workaround.
2. **Capture wiring and policy:** `data_first_service -> owned_worker_service ->
   Worker` does not forward `raw_capture_factory`. The data-first policy is
   `BYBIT_PUBLIC_GET_ONLY`; it does not admit WebSocket/raw capture. The existing
   authenticated loopback health endpoint does not close that missing edge.
   Agree the capability/profile, owner factory and A4 sink/context contracts
   first. A3 proposal hash `b2bfbfb840d1ea2d5dc5980ed8c5309d9b365272c5f9bdb6ade5e232e6aaf1ef`
   is source-only; forwarding alone is not provider admission. A2-dependent
   authority actions remain blocked. Adapter lifecycle, writer ownership and
   restart readmission also remain open; no unreviewed shutdown API is assumed.
3. **Operational logs:** ProcessDriver sends module stdout/stderr to DEVNULL.
   The exact admitted NSSM fields do not include AppStdout/AppStderr/rotation.
   State/snapshots or a permitted logs directory are not a complete bounded
   logging contract. New settings need reviewed compatibility, not silent edits.
4. **Permanent operation:** manual start, Exit behavior and no service recovery
   do not meet unattended persistence. Boot/recovery needs a separately reviewed
   versioned extension and explicit qualification.
5. **Actual Windows/runtime boundary:** real token/service SID, Session0,
   staged runtime/dependency permissions and imports, TLS trust, graceful STOP,
   child retirement, owned PostgreSQL and crash/logoff/reboot reconciliation
   remain unqualified. An interactive developer runtime is not service runtime
   proof. Never register Python directly as if the pinned service host were
   unnecessary.

## What the evidence actually establishes

- Root observed **7 actual AST-selected source-function controls PASS**, with
  inert identity/read boundaries. They test narrow existing predicates, not
  full-module execution, real Windows tokens, Session0 or service behavior.
- A separate **3-check stdlib SQLite primitive** fixture observed unchanged
  source bytes, a reopened synthetic backup row and integrity_check=ok. It is not
  Collector/Storage implementation, process restart, PostgreSQL, power-loss or
  service proof.
- Independent source review covered **20 pinned inputs: 17 source files and 3
  metadata inputs**, across distinct service/pilot cohorts. No runtime execution
  or installation approval follows. Independent A8 DATA review verified the
  sealed Root report and 11 references, original 7-control log/result and the
  primitive receipt/retained bytes; A8 did not rerun those checks or query SQL.
- A8 separately verified MWI PR83 exact
  `d6293f75db7fcc8eed0900521a1ba6bd46b3468e`, tree
  `8001dc401a578b3e726bf0930d94c6b6f6472813`: original run `43280945601`, Ubuntu
  job `131401719455` and Windows job `131401720713`, **142 unique OK per OS,
  zero skips**. Artifact API returned **0**: no ZIP, JUnit, runtime-origin or
  source-pre/post artifact proof is invented. This scoped source/hosted result
  does not admit real training, service deployment or Collector composition.

Exact evidence pins and scope labels are in [source-evidence.json](source-evidence.json).
Private inventory, paths, accounts, addresses and credentials are intentionally
absent. Integrity hashes identify evidence; they do not authenticate a runtime
or authorize its execution.

## Staged actions: none authorized or executed here

Every stage requires source-bound evidence. FAIL stops the current operation;
UNKNOWN blocks advancement and remains distinct from PASS. Approval of this
document cannot satisfy any operational approval below.

| ID | Required action and exact approval input | Required completion evidence |
|---|---|---|
| P1 | Freeze integrated source, data-only argv/profile, runtime/dependency hashes, raw factory, A4 sink, logging and shutdown contracts. | Immutable candidate/capsule and independent source review; no unresolved capability widening. |
| P2 | Generate PLAN_ONLY using existing deterministic installation/service naming. Bind an absent NEW root, exact code/state/raw/log/checkpoint/tmp paths, service identity, ACLs, owned DB/ports, authenticated loopback listener, resource ceilings and rollback receipt. Secrets use protected references, never command-line/report values. | Reviewable exact names, hashes, paths, ports, commands and before-state; placeholders are not an approval request. |
| P3 | Separately authorize bounded disposable Windows qualification under real LocalService, mock provider only. Include token/ACL/Session0, exact imports/trust, logging, own DB identity, STOP/timeout, retirement and restart reconciliation. | Actual host/source-bound positive and negative results, original failures preserved. No changes to office network configuration. |
| P4 | Only after exact owner approval: stage verified bytes exclusively into NEW owned paths, seal reviewed ACLs, register only the receipt-owned service MANUAL/STOPPED. | Installed raw hashes/ACL/config match the plan; no start and no existing service/database adoption. |
| P5 | Separately approve new owned database/role/auth and protected activation provisioning. Backend changes require agreement before installation. | Exact owned identities, non-superuser/loopback contract and protected-secret handling; no existing database writes. |
| P6 | Separately approve one bounded provider-DENY offline start/stop and exact authenticated listener binding. | Actual Session0 health, logs/raw/checkpoint ownership, graceful stop and owned-child/database retirement. |
| P7 | Only after source, network, quota, provider-time, instrument, sink/resource gates and explicit provider admission: bounded public-data capture for one approved instrument. | Exact raw bytes/metadata/gaps/checkpoint/recovery/shutdown; no private endpoints or orders. Broader history/instruments remain separate. |
| P8 | Separately review a versioned boot/recovery configuration and obtain permission for reboot/fault tests. | Actual unattended restart and reconciliation; no blind retry after uncertain sends/publications. |

No users, passwords, groups, logon rights, SSH, UAC, security policy, firewall,
endpoint protection, Tailscale, router, DNS or adapter changes are included.
Excluded administrative systems and pre-existing databases remain untouched.

## Rollback contract

Record before-state and exact receipt ownership before any future action. On
failure, block the next stage, preserve originals/state/checkpoints and stop only
owned work through verified shutdown. Do not scan or kill by process name/PID,
restart networking, delete retained data or adopt another service.

Restore code/config only from a retained immutable compatible capsule after
read-only validation; never downgrade a database schema in place. Disabling or
unregistering a service requires a separate approved rollback action for the
exact receipt-owned identity, retaining state. If normal STOP is unavailable,
escalate to explicitly approved owner recovery. Unknown sends/publications and
cooldowns remain fenced until reconciliation; rollback never renews authority.

**Installation A: BLOCKED. Installation B: CONDITIONAL DESIGN ONLY.
Service/runtime/physical/provider admission: NO-GO.**
