# Follow-up review scope

The first Draft PR snapshot `8d7c3c321b8b0bd7704a92721c9549b778d053f6`
remains preserved. Its exact 51-test scoped local pass is not a claim that the
independent A8 review had no findings or that hosted/physical acceptance passed.

## A8 source-availability episode defect

The original runtime queued SOURCE_UNAVAILABLE with the same source, status and
version on every failure. Persistent deduplication therefore correctly retained
that identity, but wrongly suppressed a new outage after recovery. Original
engine-path regressions failed with one queued event instead of two and zero
after delivered-event compaction/restart instead of one.

The follow-up makes source availability, its monotonic local episode number,
event identity and outbox enqueue one Observer-owned SQLite transaction. Repeated
FAIL within an outage does not enqueue; PASS closes the episode; the next FAIL
increments a durable counter. This counter is notification identity only, not
Authority, fencing or Scheduler state. Existing FAIL rows without episode data
are not re-alerted on adoption; recovery then a new failure creates a new event.
No live journal or production database schema changes occur.

## Evidence hyperlinks

Only allowlisted public repository names and validated numeric IDs can produce
PR/run links. Arbitrary input URLs, private addresses, paths and schemes are
never adopted. Immutable Observer code links require an explicitly supplied
40-hex reviewed commit (`--source-head`); the display argument is not source
verification or a security grant. Private Mission Controller evidence retains
digest/sequence without an invented public URL. Statuses and source freshness
remain independent of link availability.

## Journal copy

See MISSION-COPY.md. Exact qualification includes the three unchanged primary
MissionController engine blobs. Checkout EOL aliases are not executed. Existing
source files are not rewritten. All copy tests use newly created temporary
fixtures, not the live journal. Live source-copy admission remains separate.

## Current limits

Actual GitHub observation at the first milestone performed two unauthenticated
GETs with persistent reservations. Its raw response bodies were not retained;
body digests, sizes and sanitized facts are observations, not independent wire
proof. No reconstruction or repeat was performed. A future admitted capture may
retain original bounded public responses privately after its effects are reviewed.

LS5 listener, Windows Service, node APIs, PostgreSQL/ingestion probes, real Telegram
delivery, live journal polling and all physical acceptance remain unadmitted.
No new hosted cohort is authorized by this local follow-up commit or local tests.
