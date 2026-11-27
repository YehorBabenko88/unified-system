# Provenance v1.1 integration acceptance (source pins, not runtime authority)

## Frozen reviewed upstreams

- Strattester Draft PR43: `943095d00d5d56276f3832c42b36b290bea77a84`; tree `5b9d99f3beb55ba31ea551ef9c1c82488c6f457a`.
- Grid Draft PR249: `bf9f108b6777085d6725675eac778d61ec55f42b`; tree `c8e8131e353956436b981b6b9857a4c5250460a4`.
- A uses immutable declared input windows, qualified terminal receipts and independently admitted source pins; B uses atomic candle/footprint revisions, bounded repeatable-read snapshots and independently pinned historical handoff.
- A->B research uses inner `api_version={major:1,minor:1}`, `completion_receipt`, `dataset.fingerprint`, `producer_epoch`, `producer_identity`, `source_revision`, `execution_authority=false`, `mode=HISTORICAL`.
- The public /internal/v1 HTTP envelope may remain 1.0 while the qualified inner record is 1.1. Do not collapse these versions.
- Git source revisions are 40 hex; content hashes and receipts are 64 hex. Neither hash is automatically trusted.
- Grid source snapshots have dataset fingerprint, producer epoch, UTC watermarks and PARTIAL/STALE/GAP conditions, but exchange completeness attestation remains unavailable.
- Supervisor contract is control-plane observation only, not proof that a historical research bundle is admitted by Grid.

## Required downstream integration

1. Use separately provisioned owner-pinned source and receipt identities. Never trust a request's self-reported SHA/identity.
2. Validate the complete canonical historical record before handing it to Grid; empty trust policy -> UNAVAILABLE.
3. Do not convert a Grid PARTIAL/STALE/GAP snapshot to AVAILABLE based on a successful hash comparison or a connection's HTTP 200.
4. Terminan must continue to display results as unverified until independently qualified. Never label footprint as true live L2.
5. Add independent pinned actual-source CI after exact current upstream HEAD and workflows settle; no source-owned test may be silently replaced by synthetic mirror fixtures.
6. Keep all PRs Draft, no merge, service/ACL/PG changes, physical host actions, G1, orders or trading.

## Evidence boundaries

Strattester run 40496043425 attempt 1 succeeded for 4 hosted Windows/Linux jobs, but real source receipt pins and physical execution are absent. Grid run 40496225645 was queued at review; no hosted acceptance is inferred. Codex external combined evidence manifest digest `30c9bcff767c6fd6ac6fd2822ef078190ca0e738648a475b50fc871a90b5925a` is recorded as a reported digest, not downloaded or independently verified bytes.
