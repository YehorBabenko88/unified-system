# Windows CPU hard-cap policy v1: arithmetic only

Version: `windows-hard-cap-logical-mcpu.v1`. This is local pure policy, not an Assignment/API freeze, resource hold or admission capability. `admitted_fields` stays empty.

## Source and derivation

Microsoft documents CpuRate in 1/10000 cycle units, with ENABLE plus HARD_CAP flags (`5`). Zero is invalid. Without a CPU-controlled ancestor the denominator is the whole system; otherwise it is parent-relative. DFSS can make this facility unavailable. See [CPU rate control](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_cpu_rate_control_information).

Policy inference: define one logical CPU as 1000 nominal millicores and let N be the complete active logical CPU count. Then `r = floor(10*m/N)`. The represented nominal bound is exactly `r*N/10 <= m`; rounding loss is less than `N/10` millicores. Reject `r=0` instead of rounding up. Example: m=1000, N=16 gives r=625, not 1000. No claim about benchmark-normalized throughput, wall-clock utilization, heterogeneous cores or performance guarantees follows.

V1 conservatively accepts only one group, identical nonzero process/system masks with at most 64 bits and popcount N. N comes from [GetActiveProcessorCount](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-getactiveprocessorcount); [GetProcessAffinityMask](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-getprocessaffinitymask) supplies group-sensitive masks. Restricted affinity, multiple groups, count mismatch, unknown/CPU-controlled parent and unknown/enabled DFSS are unsupported. This restriction avoids inventing a partial-affinity denominator.

Require `m > 0`, nonnegative already-reserved millicores and `m + reserved <= 1000*N`; reject excess, never clamp. All numeric inputs must be exact integers, excluding bool. This prevents oversubscription in the supplied arithmetic snapshot only. Actual admission still needs A2 atomic current holds, verified identity/session, topology custody and freshness. Caller-provided totals/flags cannot prove these facts. Affinity equality before/after observation does not prevent later topology changes.

## Executable qualification matrix

`tests/gateway_jobs/test_cpu_policy.py` exercises integer floor bounds across N=1,2,3,8,16,32,64, below-quantum rejection, exact capacity/excess, invalid/coercible types, topology restrictions and parent/DFSS unknowns. Every result keeps `admission_supported=False` and `behaviorally_qualified=False`.

| Gate | Executable evidence | Current qualification |
| --- | --- | --- |
| Integer conversion and supplied aggregate bound | Pure regression matrix | Arithmetic only |
| Actual child topology | Retained-handle group/count/affinity reads before/after local observation | Snapshot only, not pinned |
| Actual Job CPU rate | Query existing suspended Job, verify flags=5/rate=1000 unchanged | Set/query only; derived rate not applied |
| Parent CPU denominator / DFSS | UNKNOWN in actual local observation | Unsupported; no guessed attestation |
| Behavioral CPU cap | No workload executed or resumed | Not qualified |
| Distributed reservations / sessions / UTC | Actual A2 API pending | Not qualified |
| RSS hard bound | Working-set snapshot; no RSS enforcement | Unsupported |
| Committed-memory cap | Existing native set/query, PR51 peak discrepancy open | Not qualified; never substituted for RSS |

Native tests create/inspect/abort only an owned suspended child. No ResumeThread, CPU load probe or PR52 execution. Passing the test matrix does not change any qualification status. Root must separately authorize any behavioral probe; exact topology, parent/DFSS provenance and source custody must be qualified before permit wiring.
