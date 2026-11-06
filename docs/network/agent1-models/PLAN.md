# Network safety model preparation plan

Goal: deterministic test-only simulator and negative tests, MODEL_ONLY, without production transport or effects.
Authority: explicit A1 independent negative-test allocation; full product design approval still pending.
Base: b12c6c24eeb2c59aa099f1c516d77508f36b20a6 / tree41912cd64982d152417dcf74b250bc056142a450.

Files: tests/network_model/model.py (synthetic discrete-time mechanics), test_safety.py (independent invariant oracles), run_evidence.py (bounded report), docs/network/agent1-models/{PLAN,README,EVIDENCE}.md, optional own CI. No other edits.

1. [ ] Write tests first; capture expected import/behavior RED.
2. [ ] Integer token buckets, atomic node/class/aggregate debit, bounded queues, control/live/bulk selection. Pin exact boundaries and no partial debit when constrained.
3. [ ] Six-node ten-instrument deterministic event scenario: bounded latency/loss, cost charged on attempted sends; LS5 loss does not expand surviving rates; restart empty byte buckets and gradual rate recovery.
4. [ ] Shared synthetic quota ledger with persistent reservations/debt/cooldown/dedup, no-quorum and closed gates, UNKNOWN freeze and conservative corrupt/rollback restart. Test repeated failover/restart without resets.
5. [ ] Seeded and adversarial interval oracles; report counts/queue bounds without calling them actual network enforcement. No real provider numbers or fixtures implying office identity.
6. [ ] Run GREEN, independent branch review, fix meaningful findings with RED/GREEN, commit and Draft PR targeting agreed component base, local/hosted evidence distinguished.

Review focus: partial debit on blocked class, same-NAT duplicate allowance, queued-memory growth, restart/window uncertainty refund, old time after restart. All get explicit negative cases. No sockets, subprocesses, network configuration or office probes in model code. Temporary state uses only test-owned directories.

Ruling: plan saved in allocated docs path rather than shared superpowers path. Inline execution is routine authorized test preparation; no duplicate human design question. Native worktree API returned no result and git confirmed no new worktree; explicit Git fallback used allocated path. Baseline targeted legacy tests separately recorded, not model or physical proof.
