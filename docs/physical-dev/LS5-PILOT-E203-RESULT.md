# LS5 disposable pilot: exact e203 result

MASTER MISSION: IN_PROGRESS / NO-GO. Observation published 2026-11-10;
execution originals are dated 2026-11-09 UTC. This document grants no admission.

## Immutable candidate

- Unified source: `e203c0bbeaa176a843a7d80b2eadfefe8fce7385`.
- Source tree: `7ca3b471eb7ee2411eb83da68f8e068ee42c803c`.
- Package manifest SHA256: `c0e5fe1d5a25f4d88488bbf5d33c9b5f47770890bf60b9c26cdacfa0aabd5886`.
- Package: 19,567 files, 1,008,127,478 bytes. Protected package unchanged.
- Activation plan SHA256: `55abda936872053a297e572ef2def80df33d5cf7d7ea791aeea2d3c6ee5d32df`.
- Original smoke receipt SHA256: `e5b44b54233b04d4c2d56d8641beae9c8d476e526ea756bddbca29a635ad9d37`.

The later evidence-publication commit is not the executed source. Local source
qualification recorded 106 distinct pure tests, zero skips and 1,668 raw files
before/after; this is not hosted or native worker qualification.

## Actual execution

The existing Strattester -> MetaAnalyse path completed in an ordinary owned LS5
process, exit 0. Its fresh artifact is 2,070 bytes with SHA256
`f4997d7d26211676cd8664e53d7999f8b71f203510f3b9a275b439c403e03940`.
Request/envelope and original logs are preserved under
`release/physical-dev/ls5-20261109/failed-e/`. This is synthetic BTCUSDT and
LOCAL_UNATTESTED, not verified market history or a committed Storage result.

Full disposable smoke FAIL_OR_UNCONFIRMED: Terminan produced a generic failed
render receipt, no successful DOM/screenshot evidence. The work watchdog ended
the owned renderer with exit 73. Work 20.0489629s exceeded 20s; cleanup 0.0023232s
and family 20.0512861s were below their 10s/30s limits. Outer verification and
controller duration 106.141s is a different scope.

Both primary identities/nonadmin tokens and new Job membership/limits were
recorded before GO. Primary exits were [0,73]; final active processes 0. Total
process count 31 is cumulative, not proof of exceeding the concurrent limit 16.
USER CPU 6.625s was below 10s; kernel CPU 7.96875s is outside that USER cap.
Peak Job COMMIT 336,195,584 bytes was below 1GiB. Neither CPU nor memory is an
established failure cause. Browser-specific cleanup was confirmed; whole-smoke
strict cleanup remained nonPASS because of the watchdog/nonzero exit.

Renderer root cause remains UNKNOWN (A8 F36 P2). Source-only bounded phase/error
diagnostics and cleanup of issued browser/context handles are assigned to A6.
No increased budgets, weaker sandbox or repeated execution of this candidate.
Any retest requires a new reviewed GitHub source and immutable package/state.
Earlier c/d RED originals remain alongside e and are never overwritten.

## Hosted and independent evidence

Runs 42716081580 and 42716071876 succeeded on Windows 2022/2025 at exact e203.
Original logs prove 15 distinct regression tests per job, 60 executions total,
and PASS_COMPONENT_STOPPED_SERVICE_ONLY. Artifact digests were verified. This
does not prove service start, source-proof admission, installation closure,
physical deployment or the full mandatory Windows/Ubuntu matrix. See the scoped
report under `release/physical-dev/ls5-20261109/hosted-e203-stopped-service/`.
Other workflows' prior QUEUED observations are snapshots, not current guarantees;
the general queue root cause remains UNKNOWN. No reruns or cancellations.

A8 original-result review: audit commit
`b398fa84f26e2cac46b070ae3cd402da0e9bc36a`,
`docs/audits/agent8-20261106/phase150/report.md`, SHA256
`11170bae93139e269e5bb41749f323d93c9f5e98da260dd176a27880dc68c982`.
It independently reviews Root's small originals, not an A8 physical execution.

## Remaining gates

Native commissioner/resource admission, real authority/Scheduler quota and
Assignment/fencing, committed Storage publication, authenticated scientific
Terminan READ, full hosted CI/F26 and distributed physical acceptance remain
open. Production backup is not verified; disposable rollback stops only owned
processes and preserves every file. No production credentials/provider sends,
network/security changes, office fault injection, main merge or Tailscale
removal. TRUSTED_RELEASE remains BLOCKED_NO_TRUSTED_PUBLISHER.
