# One-shot negative integration regression plan

> **For agentic workers:** Use superpowers:executing-plans inline. Existing approved closed-boundary requirements only.

**Goal:** Execute cross-component negative regressions over existing Scheduler preparation, gateway UNKNOWN recovery and worker start denial without implementing an issuer or positive adapter.

**Architecture:** Existing scheduler_components placement/PreparationJournal remain local advisory state; ResearchJobs stays unbound; ClosedAuthorityBoundary and GatewayWorker.start remain closed. Tests join those actual components and exercise restart/pressure/quorum/schedule/forged-grant paths. No production source or shared wire API changes.

**Tech Stack:** Python stdlib unittest/SQLite/tempfile; no dependencies or native helper launches.
**Spec:** Owner attachment b43ebc5e-e2c8-4861-bc3d-52f4aab4a088; sealed HA decisions9af6 and A5 inventorydd816 / design ACK6180.

## Constraints
Base623c1ebe33c14707b99ad526678f5225f553e49a is A5 isolated source, NOT approved HA runtime base. Strict Option1/logical mutations DISABLED; resource/reservation/consume/start APIs NONE. No native Job/Consul/browser/physical or provider operations, no Math/PR52 diagnostics. No second Scheduler/authority or production files edited. Temporary SQLite is only existing local preparation model, not durable native acceptance.

## Tasks
- [ ] Add tests/gateway_jobs/test_one_shot_closed_integration.py: local preparation/recovery through gateway submit/lookup/cancel and worker/boundary denial; capacity pressure, stale incarnation, schedule and no-quorum.
- [ ] Run focused tests under isolated Python; preserve output and source hashes.
- [ ] Run two inert mutation controls: promoting closed GrantAssignment or worker.start must make the relevant tests FAIL. These are counterexamples, not issuer/resource/native evidence. Restore automatically with mock scopes; no production source mutation.
- [ ] Fresh read-only review; commit exact test/doc-only source. Report counts and limitations to ROOT/A2; request A8 source review without executing protected workload.

## Review focus
Local PREPARED/UNKNOWN never becomes native status/Assignment; pending local hold survives reopen and blocks second preparation; new incarnation cannot adopt old attempt; STANDBY does not cancel or refund; advertised quorum/caller metadata never authority; root gate remains closed even with positive advisory placement.

## Verification checkpoint

8 new cross-component local negative tests and 25 selected existing pure tests: 33 PASS, zero skips on Windows CPython3.15.2. Two inert mutation controls produce the expected single AssertionError each; no native/grant evidence is claimed. Fresh source-bound verification follows commit. Hosted CI is configured for CPython3.12.10 on Windows/Ubuntu, not yet accepted. No native Job, worker preparation, broker/Consul RPC, Math or browser test is selected.

Fresh source reviewer found that the competing job in the rejoin regression must use the new incarnation; corrected both replay and competing preparation to Candidate B. Local UNKNOWN debt still blocks that candidate. Production source unchanged. Exact commit, raw guard, logs and CI outcomes belong in the external evidence receipt, not circularly embedded in source.

## Rulings
Managed worktree creation was attempted first but did not return a path. Use separate no-hardlinks own clone, leaving archived evidence checkouts unchanged. No product code added, so RED here is an explicit inert mutation-sensitivity control, not a manufactured missing-function failure. No native acceptance follows green tests.
