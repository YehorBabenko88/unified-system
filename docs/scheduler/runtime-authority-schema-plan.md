# Issued authority record proposal plan

ROOT requested concrete NEW Assignment, WorkerResourceReservation and
CapacityObservation schemas plus native key/check/write ledger. Keep these
distinct from request-only command-v1-c3-review1 and from admitted native APIs.

1. Generate closed canonical draft2020-12 schemas using exact string units/u63.
   Include a fourth NodeResourceLedger: concurrent reservations cannot safely
   debit telemetry observations alone. Native ModifyIndex belongs to read proof,
   not an unknowable self-index embedded in a record before its commit.
2. Create deterministic bound examples and validate positive/cross-record negative
   cases, including mismatched scope/revision/epoch/incarnation/units/storage,
   staleness and resource arithmetic. Parsing remains untrusted.
3. Propose domain-separated scope keys and persistent monotonic counter. Explicitly
   identify current assignment/resource keys both supersession and publication
   must check/mutate. A2 remains sole native builder/key owner; A4 owns storage.
4. Measure operation counts and serialized native JSON bytes for fixed fixtures
   and closure expansions, without claiming native execution/load acceptance.
5. Send immutable proposal hashes to ROOT/A2/A4; incorporate joint ACK before
   production APIs or adapters. Existing52-test CI inventory stays unchanged.
