# Qualification inventory repair after exact-source hosted failures

Original source: PR77 `dd4ef015d9ed20065ccdc2c563e80046015d9193`.
Original Gateway runs42846229238 and42846159426: all four Windows/Ubuntu
jobs pass source controls, then reject discovered25 test IDs against the
qualifier's fixed24 expectation before fixture execution. Earlier Root/A8
wording that the dedicated entrypoint selected only24 was incorrect: it discovers
the entire module, then validates24. Original reports are preserved; A8 phase163
explicitly retracts the earlier source-review interpretation (F38).

The repair preserves all24 prior GatewayIdentityTests and explicitly requires
the new strict regression as the25th ID. Discovery remains whole-module;
uniqueness, exact set equality, no skips, raw source guards, runtime assertions,
certificate/hostname checks and TLS policy remain. Both post-run count and output
metadata advance to25. Guard controls retain missing/duplicate rejection and
add missing-prior/extra checks; omitting the new strict case is rejected.
Root's five pure contract checks against original source produced two failures;
the successor passed all five. No TLS fixture was executed by those checks.
A2 granted Root exclusive ownership of the two qualification files for this fix.

Original Supervisor run42846228841: both Windows/Ubuntu jobs reject122
discovered IDs versus121 expected before tests execute. The only added ID is
MissionTests.test_owned_temp_alias_is_resolved_before_guarded_journal_creation.
All121 previous IDs are retained; the explicit list now contains122. No test is
removed, renamed or skipped. No production or service operation is modified.

Separate PR78 component inventory lineage correction binds prior_inventory_sha256
to the actual raw145-case v5 predecessor atdd4:
22b52b8ee2eaeb752ae1ec0c3899185253bafdec73e17ed7f79aa00e379dfaf3.
The older inherited144-case digest was stale metadata; all145 preserved IDs and
16 added pure IDs remain unchanged. This does not qualify full161 execution.

Original report SHA256:
e240865404df79f3a150a5307eb0ea3712dc6914833f38a33ac17b0521dd745f.
Read-only retrieval used14 GETs, no retries; original six failed-job logs and
Supervisor artifacts/digests remain retained separately. Raw source-control
hash-mismatch text was expected negative-control output, not evidence of actual
source corruption. Public correlation index: DD4-ORIGINAL-RED.json.

Hosted qualification of the repaired successor remains pending. The original
failure stacks establish inventory configuration defects, not a native transport,
installation or application failure. F26/LAN RCA remains UNKNOWN; F38 is a distinct
Gateway qualification blocker. No full CI, native, physical or system PASS is
claimed. Strict D4 Option1/logical DISABLED/public submit DENY remain unchanged.
