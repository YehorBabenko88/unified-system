# Physical acceptance accounting

This ledger records required outcomes; it does not execute tests, verify machine
identity, authenticate evidence or authorize deployment. A deployment runner and
an independent verifier are still required. The project remains incomplete.

`python -m unified_system.physical_acceptance ledger.json` accepts exactly:

```json
{
  "inventory": ["pc-1", "pc-2", "pc-3", "pc-4", "pc-5", "pc-6"],
  "release_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "run_id": "office-acceptance-unique-run-id",
  "records": []
}
```

The example identities are placeholders, not discovered machines or acceptance
evidence. Use the actual owner-provided inventory only after deployment
preparation. Five or six unique nodes are required; two-node acceptance cannot
qualify the fleet. Each node must have a record for all 15 `SCENARIOS` in
`unified_system.physical_acceptance`.

Each record has exactly `node_id`, `scenario`, `release_sha`, `run_id`, `result`,
`environment`, `evidence_sha256`. `result` is PASS or FAIL;
`environment` must be PHYSICAL_WINDOWS, with a referenced evidence SHA256.
Run/release/roster mismatches, duplicates and records labelled as synthetic are
rejected. A fabricated PHYSICAL_WINDOWS label cannot be detected by this ledger;
that is why every record remains unverified and can never grant acceptance.
The hash is a reference only: the ledger does not read or authenticate evidence.

No records yields NOT_RUN. Partial records or any failed case yield BLOCKED.
A complete set of claimed successes yields RECORDED_UNVERIFIED, never physical
PASS. `physical_acceptance_confirmed` and `deployment_authorized` remain false.
The CLI returns 1 for every valid ledger (it is not an admission gate) and 2 for
invalid input. JSON duplicate fields, nonfinite values and oversized input fail.

Actual evidence must come from all physical hosts and bind service/release
identity, run identity, observed timestamps and test artifacts to authenticated
node identities. Verify failover, node loss, reboots, network interruption,
rolling updates, rollback, DB backup/restore, migrations and duplicate prevention
on those hosts. Linux tests, synthetic fixtures, signed claims without observed
test evidence and unverified logs do not substitute for this work.
