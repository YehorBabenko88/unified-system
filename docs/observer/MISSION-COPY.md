# Journal-copy adapter — follow-up, not admitted

This separate follow-up is not part of the first frozen 51-test Observer
publication. It has not read the office Mission Controller journal. Source
admission, exact-source qualification and independent review remain pending.

The adapter opens the configured source with binary `rb` only. It never makes a
SQLite connection to that source, calls source MissionController APIs, acquires
source locks, quiesces the writer, repairs, checkpoints or creates sidecars.
It rejects links, sources above 2 MiB, WAL format, any journal/WAL/SHM sidecar,
inconsistent page counts/change counters, path or handle identity changes and
unequal consecutive held reads. Failed observations are unavailable; previous
facts expire normally. There is no automatic retry inside the adapter.

The two-second capture deadline is checked after bounded filesystem reads; it
is not a kernel-enforced interrupt of a stuck filesystem. File ID, device, size
and mtime bind the open handle to the path. Path ctime is separately checked
before/after: Windows Python 3.12 `stat` and `fstat` ctime have different legacy
semantics and cannot safely be equated to one another.

Only validated held bytes are copied into a dedicated Observer-owned directory.
The marker and content-addressed filenames are verified on reuse. At most two
2 MiB snapshots are retained; only verified older private copies are removed.
The source and existing project datasets are never pruned. Interrupted or
foreign snapshot contents cause a closed failure requiring operator review.
Snapshots contain private task records and require the eventual least-privilege
state ACL; never publish them or include them in Telegram.

The reader reuses the unchanged existing MissionController, Journal and Contract
modules from engine commit `e869d8365c7e54ed3da3739d9cdf15948f37f022` (byte-identical
at the Observer base). All three exact primary SHA256 pins are required. Held
verified code is loaded in a temporary private module namespace, without a
package search path or replacement of existing Unified modules. Only
`MissionController.open`, `projection` and `continuation_projection` run against
the private copy. Initializers, appends and checkpoints are never invoked.

The existing export reducer emits sequence, bounded state counts and the fixed
Root summary whitelist; full requirements, private paths, receipts and references
are excluded. Evidence identifies the captured database bytes. These are journal
observations, not Authority, native runtime admission or physical acceptance.

Ten developer tests cover real existing-core replay on own copies, source SQL
and mutation traps, source byte/sidecar integrity, source change rejection,
WAL/hot journal rejection, hardlinks, corrupt/incompatible schema, exact engine
pins, restart/deduplication and foreign snapshot refusal. They use temporary
fixtures only, including source containment in the snapshot directory being
rejected without changes. Source-copy observation is still **NOT RUN** on the
live journal.

The test fixture's CRLF checkout fallback reads primary blobs at HEAD and then
requires the same three exact engine pins; no EOL normalization is executed.
A mocked absent-historical-object regression verifies the actual helper without
requiring old Git history in a shallow hosted checkout. Production reader logic
and pins are unchanged. This test is not an actual hosted shallow-clone result.
