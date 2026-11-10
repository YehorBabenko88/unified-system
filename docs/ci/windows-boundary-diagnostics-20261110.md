# Windows boundary timeout diagnostics

This test-only change prepares finer observations of original hosted failures at
`01630597fb418d5a76a93c8b09750683dfe49b94`. It is instrumentation, not a timeout
fix or a hosted/native qualification. The original 15-second PowerShell and Node
limits and 30-second declaration-test limit remain unchanged. There are no retries,
new skips, extra module imports, command-resolution probes, cache warming, SCM
operations, or changes to the sanitized environment or poison-autoload assertions.

The fake NSSM-member test now separates object construction (`OBJECT_BEGIN/END`)
from the first existing `Add-Member` call (`FIRST_MEMBER_BEGIN/END`). The enclosing
`MEMBER_BEGIN/END` markers remain. Neither member markers nor `COMPILE_BEGIN`
prove that a native API or compiler has started: PowerShell still resolves the
original unqualified commands in the original environment.

The existing 30-second declaration test now reports parser, import, Add-Type,
Unicode-child, and output-cap-child intervals. `COMPILE_BEGIN/END` surrounds the
existing Add-Type expression, including command resolution and module autoload.
It cannot discriminate resolution from compilation. The original Unicode/output
assertions and child commands remain. Timeout failures expose only a fixed phase
allowlist and bounded numeric timestamp/elapsed facts; malformed or private stderr
is represented as `PHASE_DATA_REJECTED`.

The Node harness emits seven fixed stderr markers: `ENTRY`, `STDIN_END`, `PARSED`,
`VM_RETURN`, `FIRST_SETTLED`, `SECOND_SETTLED`, `DONE`. They report reached JS
statements, not kernel-level process startup or pipe ownership. The parser accepts
at most eight lines and 1024 ASCII bytes. The existing VM script, assertions,
stdin payload, and async scheduling remain; no real browser is introduced.
Timeout failures do not print argv, harness, input, paths, or raw child output.
No missing-output or inherited-pipe explanation follows from a timeout alone.

Original evidence is private under
`C:/Users/LS-5/.codex/ci-queue-evidence-20261107/pr69-01630597-original-red-20261110`.
Representative run `42732724684`, job `129554474213` contains the 15-second Node
timeout and 30-second declaration timeout. The original phase control lookup
completed in 235ms in that job before the safe lookup timed out. Later local
Add-Member/safe-lookup discriminators reportedly passed; those are not a hosted
reproduction or proof of command-discovery root cause.

Validation at preparation time: pure mocked parser/privacy/bounds tests only.
The original three pure tests plus six new tests run without subprocesses or
fixtures: the new tests first failed against the old helper, then all nine passed.
PowerShell, Node, sockets, SCM, and native child fixtures have not been executed
for this change. Root must review the exact source and assign a serial fixture
lane before qualification or publication. Keep the original RED even if a later
fixture completes; diagnose the first missing marker without increasing limits.
