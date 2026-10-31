# Builtin Unified profile: integration contract

`BuiltinRuntimeDriver` wraps the existing `ProcessDriver`. It registers only
`unified-system` in-process; other modules retain the subprocess driver's exact
interfaces. It creates no controller, scheduler, fleet journal or child process.

Construction binds the existing journal, public snapshot file, actual loopback
status-server port and release/node/digest. Builtin start requires the supplied
execution authorization and a matching committed supervisor operation ID.
Registration carries a private per-driver generation. Previous-instance handles
cannot be adopted; stopping them never signals the controller or a child.

After each ordinary supervisor tick, the caller performs `view.set(snapshot)`,
`write_snapshot(path, snapshot)`, then `driver.published(snapshot)`. Publication
checks a consistent read-only SQLite transaction and file bytes. Readiness
requires a publication newer than registration, at most two seconds old, plus
fresh journal identity/operation checks and matching actual HTTP/file bytes.
The HTTP probe has an absolute transport deadline and bounded response size.
Readiness never calls supervisor methods while its tick transaction is held,
never depends on global readiness, and never mutates state from the HTTP path.
An unreadable journal or stale/unavailable/mismatched API/file fails closed.
This proves local runtime functionality, not publisher, fleet or physical trust.

Implemented CLI selection:

Config `unified.runtime.config.v1` keeps its existing six-program format.
Config `unified.runtime.config.v2` requires exactly five process programs and
uses this builtin profile for `unified-system`; it rejects a sixth executable.
The six module specs and the public `unified.runtime.v2` status remain unchanged.
V2 requires an explicit nonzero loopback port and a 0.05–0.25 second tick interval.
The CLI binds that port before starting modules, publishes the initial snapshot,
and publishes view/file/driver state after every committed tick and final stop.
Readiness checks the prior committed publication, avoiding transaction recursion.

Process programs can additionally declare `external_file_pins`, an absolute-path
SHA256 map for shared bootstrap/source-policy files outside a module checkout.
These are checked before child creation. Hosted execution also requires every
such file to remain below the disposable runner's temporary root. These hashes
are launch inputs from the trusted release boundary, not self-authorization.

The normal Prepare default and existing ephemeral-host execution restriction
remain in force. This does not implement the physical deployment trust bridge.

All six readiness remains computed by the existing supervisor. Five STOPPED
modules keep it false even when the builtin's journal/API are functional.
Actual five-module functional adapters and the authenticated deployment bridge
remain independent requirements. No physical execution is authorized here.
