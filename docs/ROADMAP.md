# Delivery gates
G0: Offline contracts, mocks, deterministic regression and exact-head CI.
G1: Read-only source adapters pinned to immutable source SHA and bounded snapshots.
G2: Installer dry-run, signed lockfile, dependency closure, compatibility matrix.
G3: Explicitly authorized physical read-only acceptance with evidence manifest.
G4: Separately authorized operational integration. Trading, ACL, services, migrations and G1 Execute/Cleanup remain forbidden without independent owner approval.

No green CI may be presented as physical acceptance. A synthetic SHA256 is not producer authentication. Current event cursor is in-memory and requires a snapshot on first event, gap or epoch change; it must not be used as a production checkpoint.
