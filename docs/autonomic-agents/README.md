# Unified Autonomic Guardian — independent offline research v0.1

**Scope:** developer-only, source-only, seven offline proposal-only guardians. Not deployed.

## Motivation and upstream review

- [KorroAi/mue-x](https://github.com/KorroAi/mue-x): observe/diagnose/evaluate
  loops, persistent memory, agent coordination, rollback ideas. Its automatic AST
  self-mutation and broad permissive shell/network guard are **not** imported.
- [ashishpatel26/500-AI-Agents-Projects](https://github.com/ashishpatel26/500-AI-Agents-Projects):
  examples of code review, SQL/data analysis, unit-test generation, triage.
  No third-party agent is implicitly trusted or installed.

The agent loop does not require Codex, an LLM, GitHub or internet.
It does **not** learn to fix novel code defects without a qualified local model.
It cannot repair connectivity when the LAN itself is unavailable.

## Seven observation domains

| Role | Inputs | Proposed-only response |
|---|---|---|
| Infrastructure | node status, timestamp | diagnose LAN/SSH and stale heartbeat |
| Data integrity | claimed hashes, gaps, provenance | independent readback, fenced dataset |
| Strategy | candidate contract, simulation mode | reject candidate, request regression |
| Statistics | counts, numeric validity | recompute immutable-derived outputs |
| Exchange | public-data connection/cooldown | authorized reconnection proposal |
| Load | lease, CPU/RAM | existing Scheduler owner reconciliation |
| Mathematics | numerical check/residual | preserve counterexample, Math owner review |

Operator-provided snapshot schema: `unified.autonomic.snapshot.v1`.
The snapshot is **not** a physical scan. Reported hashes are untrusted claims,
not independent file verification. Missing sources produce UNKNOWN incidents.
Data/strategy/Math outputs are not admitted to runtime/market decisions.

## Run a local, bounded diagnostic

From repository root on Python >=3.11:

```powershell
python -B -m unittest discover -s autonomic_guardian/tests -v
python -B -m autonomic_guardian --snapshot example.json --journal guardian-owned.sqlite
```

Optional continuous **foreground** monitoring (no service installation):

```powershell
python -B -m autonomic_guardian --snapshot example.json --journal guardian-owned.sqlite --loop --interval 30
```

Use an operator-owned directory; no credentials in snapshots. To use actual
infrastructure, existing approved producers must first export bounded, causal,
schema-validated observations. Do not give this agent production DB credentials.

## Explicitly NOT implemented/admitted

No native node access; no new SSH/Tailscale, network, exchange, SQL or
PostgreSQL connection; no filesystem repair, data deletion/rewrite, PID/process
kill, service restart, provider reconnection, dynamic workload migration, model
auto-promotion, real trade, code mutation, GitHub write or OS installation.
The SQLite journal is a *local internal hash chain*, not a tamper-proof log.
No Windows LocalService/Session0, service SID or 24/7 launch is qualified.

## Roadmap and gates

G0 source/tests → G1 approved read-only producer adapters → G2 bounded
repair proposals with replay and a local permission broker **outside**
agent-writable code → G3 isolated simulation of corrective actions →
G4 operator-approved action templates (scoped to receipt-owned services only) →
G5 separate native Windows/LS5 admission and independently qualified recovery.

For safe automatic actions later, a separate policy engine must enforce:
signed exact-source action identity, service ownership, least-privilege token,
scope, rate/quota caps, fencing/lease, preconditions, idempotency, side-effect
receipts, verification, rollback and an independent kill-switch. Agents cannot
grant themselves permissions or weaken mandatory guards.

**MASTER MISSION and all existing Draft PRs remain unchanged.**
