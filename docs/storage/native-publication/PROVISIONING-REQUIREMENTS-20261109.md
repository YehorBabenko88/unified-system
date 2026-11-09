# Concrete disposable two-domain provisioning requirements

Status: NOT_PROVISIONED / NOT_COMMISSIONED. This file authorizes no physical,
office, deployment, service or network-security changes.

ROOT must supply or explicitly commission two independent admitted storage hosts
with independently backed media and unique node/volume/storage incarnation IDs.
For a virtual laboratory, evidence must identify the backing physical hosts/media
and shared failure dependencies. If only same-host isolation is available, report
exactly that logical process/container model; it does not meet independent
physical two-copy policy. Do not weaken policy to make a test pass.

Per host provide: isolated disposable owned root; authenticated transfer/verifier
endpoint bound to actual admitted source and identity; actual capacity/free-space
and measured repair/safety headroom; versioned budget/reservation/usage records;
failure-domain evidence and policy decision; current corruption/loss eligibility;
retention/hold protection; cleanup responsibility restricted to disposable roots.
Caller UUIDs, path names or declared domain labels are not commissioning evidence.

A2 supplies the existing disposable Consul authority namespace/generation and
actual current issuer/leader/session/ACL/transaction interfaces. Three local
Consul voter processes may exercise logical quorum behavior but do not establish
physical fault-domain resilience of storage hosts or Consul itself. No second
consensus, permanent service, office ACL/firewall/VPN configuration or fake issued
records are introduced by Storage.

A2/A4 jointly freeze exact authority replica/inventory/protection/reservation/
accounting/access records and full record-to-CAS ledger; ROOT/A5 approve assignment/
attempt/cancel/source/ownership semantics. A7 approves receipt projection/reading.
Actual transactions include all relevant captured native indices and session
checks, checked absence where needed, dataset expected revision and original
intent/idempotency. Every actual encoded plan must fit native64op/32768byte limits;
oversize denies, never split/omit checks or use an unchecked hash-only root.

Qualification run must transfer actual full closure to both hosts; independently
re-read/hash/schema-check both copies; establish protection against retention;
commit through actual A2 transaction; capture raw receipt/ModifyIndex and access
scope; interrupt before/after transaction/response; consistently reconcile the
same original and read actual bytes with current authorized access. Inject actual
destination corruption/loss, stale writer, current hold change and no quorum.
Protect the last confirmed copy; lost data is explicit, never an empty success.

Evidence must name exact sources/HEAD/tree/module hashes, actual runtime/dependency
capsule, domain identities/backing/failure model, native request/response/receipt
bytes and indices, pre/post roots/revisions, byte inventory/hash/length, original
request/job/attempt/access joins, failure points and unresolved outcomes. Physical
acceptance, native-human trust and production remain independent gates.
