# Capacity observation source prerequisite v1: local DATA only

Independent branch from PR62 `6f3085c0b4c2e07f11958c64a39603a1f74c2049`. PR60/62 remain immutable. Only A5 gateway_worker.py, its new tests and this design are changed.

Existing host diagnostics timestamp only after K32GetPerformanceInfo. A long query can therefore appear younger than its oldest input. Capture monotonic start and completion, module-owned observation incarnation and elapsed query duration. Keep existing UTC label as diagnostic only; never use it for authority expiry. Preserve `qualified_for_native_admission=False` and all six unsupported resource dimensions.

Retain the old monotonic_ns field as query-completion diagnostic for compatibility, with an explicit semantics label. Freshness evaluation uses the new start/end fields only; never silently reinterpret the legacy field. This is an interval around the OS read, not proof of the OS data's true measurement age or authenticated remote freshness.

Implement frozen pure `CapacityFreshnessV1` result and `capacity_freshness_v1(...)`: exact nonnegative integer timestamps, start<=end<=now, exact matching UUIDv4 observation/expected incarnation. Cross-incarnation samples are unusable; monotonic values are not portable across nodes/boots. This equality check is local DATA validation, not authenticated origin/enrollment proof. Age is now-start, conservatively including query duration. Positive, exact integer max_age_ns must be explicitly supplied; none/invalid means UNSUPPORTED. Reject age>=max_age_ns, including exact boundary. No built-in operational max age: ROOT/A2 policy coACK and load/failure measurements are still required.

Every result keeps admission_supported=False and resources_reserved=False. A fresh snapshot neither reserves free memory nor proves CPU/RSS/disk/network capacity. No actual Assignment/permit/source-qualification capsule is minted. Remote capacity needs an actual qualified issuer protocol; this local helper cannot establish remote freshness.

TDD: malformed/foreign/rollback/query-span/boundary/absent-policy tests RED, implement, verify deterministic query barriers with an inert K32 stub (not native capacity evidence). Run current local suite, read-only review, commit and fresh primary source guard. Two existing explicitly selected actual suspended preparation/inspect/abort cases may verify emitted observation fields; no supervisor crash rerun, Resume, CPU load, qualifier or PR52. Keep actual resource enforcement and native effect gates closed. Separate Draft/evidence and A8 handoff.
