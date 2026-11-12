# Collector PostgreSQL boundary v1 — SOURCE ONLY

These SQL files are a proposed metadata projection, not a replacement for the
existing ObjectStore and Journal. No PostgreSQL process, connection, migration,
account, service or permission change has been performed by these files/tests.
SQL syntax, constraint behavior, transaction rollback and readback remain NOT_RUN
on PostgreSQL. Source checks cannot establish database behavior.

`001_collector_metadata_v1.sql` creates one new namespace transactionally and
deliberately fails if it already exists. It creates no database, role, extension,
authority, network configuration or raw byte store. References use restrictive
foreign keys; there is no cascade, delete executor or last-copy deletion path.
Instrument identities are SYNTHETIC or UNKNOWN pending the Agent 3 contract.
The checkpoint is a local pointer to the exact observation and raw journal
digest. It never claims COMMITTED, VERIFIED, provider continuity or publication.

The proposed writer would insert context/observation/checkpoint references in a
single transaction after local readback, with explicit context and manifest
binding. No writer is implemented here. This transaction would not atomically
commit filesystem data or authorize distributed publication. Assignment
supersession/publication linearization remains dependent on the approved Agent 2
and Agent 5 contract. Root-owned local lifecycle ownership is not that authority.

`readback_v1.sql` takes positional parameters, uses a read-only transaction and
requires the exact context/binding pair. Observation limit 17 is an overflow
sentinel for the 16-observation profile; consumers must reject overflow rather
than silently truncate. Holds similarly use 129 as an overflow sentinel for a
proposed 128-hold reader limit. Missing context must fail closed in the consumer.
No consumer or retention executor is implemented. Stopping an instrument never
implies deletion; historical references and local bytes remain retained.

Before any native PostgreSQL test, Root must review a concrete effects packet:
exact binary/runtime hashes, a new isolated root/database, a free new loopback
port (not 55432), exact arguments/environment, custody identity, time/memory/disk
and log bounds, child retirement/shutdown, and retained artifacts. Existing
production clusters, services, accounts (including grid_pg_test), data and ACLs
must not be adopted. Required future native tests include migration rollback,
namespace reuse failure, foreign-key/hash/state rejection, transactional pointer
readback, binding mismatch and cleanup/retention protection. None is PASS here.
