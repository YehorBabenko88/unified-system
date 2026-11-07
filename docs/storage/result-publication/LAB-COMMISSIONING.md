# Two-domain laboratory commissioning proposal

Status: NOT_COMMISSIONED. No office/physical/network actions are proposed to run
without separate authorization. Two temporary directories or two ObjectStores on
one volume are one failure domain, regardless of their UUIDs.

ROOT must first allocate an isolated laboratory with two independent storage
failure domains and an independently hosted existing Grid authority fixture.
Candidate topology: two disposable VMs on independently backed hosts/volumes,
each running an admitted copy/verifier process, plus the existing A2-owned
disposable Consul quorum. Provider/shared-host outages and shared media must be
described; two VMs on one host cannot qualify independent host-loss resilience.
No actual infrastructure IDs, capacities or admission are asserted here.

Commissioning evidence must bind host/volume/storage incarnations to measured
failure domains, actual process/source HEAD/tree/hash, authenticated peer/issuer,
policy revision, budget/reservation basis, capacity/free-space/headroom, verifier
identity and authority namespace/generation. ROOT and A2 own issuer/provider and
Consul admission. A4 owns byte transfer/readback and replica observations. A5
owns worker assignment. No caller-provided topology label establishes independence.

Before the first distributed positive, A2/A4 jointly freeze exact replica,
inventory, protection/pin/hold, eligibility, reservation/accounting schemas and
key-to-native-CAS mapping. The real authority transaction checks all dependencies
and both eligible replicas. It must fit measured64operations/32768encodedbytes;
an oversized plan denies. A parsed local-copy observation is never an input proof
to that transaction. Native capture/commit remain unavailable in this slice.

Run actual authenticated copy and independent re-read/hash/schema checks on both
domains. Inject destination corruption, loss of one host, stale incarnation,
concurrent hold/eligibility changes, lease supersession, no quorum, ENOSPC and
crash before/after the actual commit. Preserve complete source-bound evidence;
measure repairs and restore readback. Never delete the last confirmed copy.
Native publication positives require both policy-qualified copies throughout the
transaction; unavailable topology keeps them BLOCKED.

Local Slice A tests only create owned disposable roots, copy exact bytes, verify
declared graph shape, and test failures. They do not commission domains, validate
semantic dependencies or establish physical namespace durability on Windows.
Retain all caller-owned staged/partial copies after uncertain failure; this module
has no cleanup executor, quota reservation, deployment or network configuration.
