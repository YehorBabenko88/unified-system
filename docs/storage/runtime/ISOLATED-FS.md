# Isolated owned-root filesystem prototype

This additive slice uses actual local temporary files, not an admitted service.
It provides exclusive root creation, exact-byte SHA256 objects, no-overwrite
publication into the local object namespace, bounded reads and corruption checks.
Local object observations never confirm authoritative dataset publication.

`copy_inventory(source, destination, tuple_of_hash_length_pairs)` copies a bounded
caller-supplied inventory between distinct owned roots. Copy alone does not assert
restore success. `verify_restore(backup, isolated_destination, inventory)` actually
copies and re-reads all destination bytes; its observation covers only that local
inventory. It does not authenticate inventory origin, prove dataset/schema/closure
completeness or independent media, or restore authority state. No data deletion,
office database, listener, service, registry, network or deployment is involved.

The immutable inventory digest has a separate domain separator; it is not a
manifest or publication root. Failed copies may retain partial objects; no
success observation is returned and no automatic cleanup/refund is performed.

## Explicit limits

Per-object cap is 64 MiB; inventory cap is 256 objects and 1 GiB total. These are
prototype bounds, not approved fleet storage budgets. Bytes are held one object
at a time. Hash/length rechecks do not grant source completeness or authority.
Roots on the same disk are not independent backup media. File fsync on Windows
does not qualify namespace crash durability; that status remains explicit.
Path/identity checks do not establish hostile concurrent ancestor containment or
Windows ACL admission. Only private disposable test roots are qualified here.
No runtime admission factory or rollback executor exists.

## Verification

Run `python -B tests/storage/runtime/run_isolated.py` from repository root.
It inventories 26 frozen Stage1 cases plus 17 isolated filesystem cases and
hashes owned source/docs/fixtures before and after. The frozen Stage1 runner
expects exactly its original inventory; it is deliberately unchanged. The new
combined runner is used on this additive branch.

Runtime fixtures cover actual three-root restore/re-read, corruption and missing
objects, duplicate/concurrent writes, root identity/hardlink refusal, bounded
inventory, partial/zero write, fsync ENOSPC and link-failure injection. Injected
ENOSPC is not physical disk-full qualification. Thread concurrency is not a
multi-process or distributed publication test. Restore is not pilot rollback.

P0 runtime blockers: actual A2 publication/grant/closure adapter, exact issued
record contracts, admitted root/ACL factory and namespace durability. P1:
independent-media backup, complete dataset closure/schema restore, real crash,
multi-process fault and physical Windows qualification. P2: streaming larger
objects after an explicitly versioned measured bound. Production is NO-GO.
