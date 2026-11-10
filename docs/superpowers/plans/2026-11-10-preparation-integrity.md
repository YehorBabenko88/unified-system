# Existing preparation journal integrity fix

> Execute inline using existing Scheduler component. No new journal, issuer, native API or wire change.

**Base:** PR75 HEAD72117a0ba641f8a4287742f9278f4bee7a5005a6. This is not a qualified native runtime base.
**Owner:** Agent5. Private code change in scheduler_components/durable.py only.
**Spec:** Owner02285186 continuation; preserve UNKNOWN debt/no refund across recovery. Public constructor and method signatures unchanged.

## Reproduced defect and cause
Stored local rows were decoded but never checked against the same canonical scope/spec codec and held identity invariants used on creation. A syntactically valid zeroed UNKNOWN resources record caused live competing prepare to omit conservative debt. Reopen/view also accepted incomplete UNKNOWN request identity. Own disposable SQLite only; no office/production corruption or native fault injection.

Original regression: four tests, three expected assertion failures and one valid roundtrip control. RED saved externally as AGENT5-PREPARATION-INTEGRITY-RED.log SHA159fc36508e371055ecc8b5034966a5ecac4c77d04cc7fd18098fb3e20dee92d.

## Implementation
- [x] Validate exact persisted columns, canonical scope/spec, nonempty u63 resource vector, canonical local UUID request/hold identities and complete held node/incarnation fields.
- [x] Validate on reopen and _row; validate every held row BEFORE using its quantities in competing capacity calculation.
- [x] Failed reopen closes its own connection. Invalid rows are never repaired/deleted/converted into free capacity; valid originals, events and UNKNOWN identities are retained.
- [x] Verify new targeted regressions plus existing pure preparation and closed integration tests: 53 pure/local PASS, zero skips, CPython3.12.10 on Windows. Original process-crash subprocess test is not selected by this no-child cohort; remains in original suite.
- [x] Fresh source review found no actionable issue in the private validation/test changes; source-only, no reviewer test execution.
- [ ] Exact-source evidence, own feature PR and A8/hosted review; no merge/deployment.

## Limits
Validation is structural consistency, not tamper-evidence or native authority: an attacker who rewrites a row to another completely valid record cannot be detected by this change. It does not add schema migration, backups, encrypted storage, capacity qualification, a hash ledger or protection against hostile namespace replacement. Existing local SQLite is advisory preparation only. StrictOption1/logicalDISABLED/startDENY remain unchanged.
