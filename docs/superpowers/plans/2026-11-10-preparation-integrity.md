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

## ROOT selective integration on PR81

Integration base: e869d8365c7e54ed3da3739d9cdf15948f37f022, tree 8de558ea63b82a0b710a1dcea3459996057cb216. Owner ACK covers the private guard and six-case regression only. The regression is relocated byte-for-byte to tests/test_preparation_integrity.py. No gateway_worker, Agent5 workflow, native integration base or 53-case result is imported.

ROOT reproduced the six-case regression against the old guard: six cases, nine failing subtests and one error, zero skips. Original log SHA256: 04ac4481aa11461e728c4d3d6e6f333d0188ea1539d3d7707a1841428a359449.

Expanded local qualification executes all 30 existing Scheduler tests plus the six new regressions, including the existing own-child crash test. First isolated Python run had ten ZoneInfoNotFoundError subtest errors because Europe/Berlin data was unavailable; no assertion failures. Original environment RED SHA256: 2a491fbea5c2e3835e253aaba5c7bc7f700814a5949005f56bab494e6b9ec2e4.

After explicitly selecting existing tzdata 2025.2 data, matching docs/ci/requirements-unittest.lock, all 36 tests passed with zero skips. All 627 existing package data files were checked against their local RECORD; Berlin bytes SHA256 a7fd9932d785d4d690900b834c3563c1810c1cf2e01711bcc0926af6c0767cb7. This is local installed-data verification, not a fresh wheel provenance qualification. No dependency installation or source schedule change occurred. GREEN log SHA256 ae4614f096499cc2a342de6f3457a1cb28f90a046e1d3ef4d93e1388fcda164f. Checked source bytes unchanged before/after; no remaining Python threads.

Hosted qualification, independent integrated review and native admission remain pending. Local preparation capacity is not cluster authority. Public submit remains DENY.

Additive CI qualification is implemented separately from the unchanged historical 30-case workflow/inventory: Windows and Ubuntu CPython 3.12.10, exact old30+new6 IDs, eight pure negative guard controls, full raw source before/after, hashed tzdata2025.2 wheel/data, bounded own-child execution and artifact digests. Feature qualification runs on PR events; main push remains covered without a duplicate feature push run. ROOT executed the eight pure controls plus four Mission workflow controls: 12 PASS, zero skips. The full new driver/worker/watchdog path is not yet locally qualified: the fixed existing LS5 Git executable has link count two, and the new ordinary-singlelink prerequisite correctly refuses it. No installed Git file, link or policy was changed. Prior 36-case local results used the explicit local test harness and are not a PASS for this new CI driver. Hosted matrix and exact-source independent review remain pending.
