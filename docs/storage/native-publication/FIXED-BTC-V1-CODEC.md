# Fixed historical BTC v1 byte consistency

`unified_system.storage.publication_records.decode_fixed_btc_v1(request_bytes,
descriptor_bytes, artifact_bytes)` is a local pure decoder for exactly one
reviewed packet. It performs no IO, computation replay, authority call or storage
publication. This is not a shared native wire ABI or production backend.

All arguments must be exact `bytes` of lengths 1126, 2122 and 2070. All three
length/type checks and SHA256 checks finish before any JSON decoding. The fixed
hash profile closes every accepted field, including duplicate/unknown fields,
numeric aliases, historical source claims and unavailable financial values.
Reencoding is rejected even when JSON meaning appears equivalent. This codec
does not accept arbitrary future packets or claim to be a general JSON validator.

After the hash barrier, explicit joins check request SHA, artifact encoding and
length, dataset identity, request digest, units, replayed rows, echoed source,
experiment, clocks, unavailable revision and financial/authority flags. Meta's
request digest hashes canonical `{payload, decision_ms}`; it differs from the
whole request SHA and the payload SHA. Meta numerical JSON is not Storage C3.

`LocalFixedBtcV1Packet` retains only exact immutable bytes. Its constructor applies
the same checks. It exposes no mutable decoded graph, current capability, receipt,
committed revision or verified replica. Classification is always
`LOCAL_UNATTESTED`; source authenticity and scientific correctness are unproved.
As with other Python records, frozen fields are ordinary API discipline, not a
security sandbox against hostile code manipulating the interpreter.

Fixtures are copied from A7 Git HEAD
`aed8a7c8a952f96803c207d5e90b133969a47f04`, tree
`eed3a87c6e33f0993424f20b49ab5af93bd09b9a`; provenance lists exact raw hashes.
Source revision 6360 and Stratt base 072d remain historical claims. These bytes
are not presented as a new computation, Root runtime adoption or a committed
scientific dataset. Two local paths would not establish independent domains.

Remaining binding gates: actual A2 issuer-owned capture and strict D4 commit-time
expiry enforcement; A2/A5 assignment/reservation/hold atomic CAS; A3 instrument
and historical checkpoint agreement; verified physical replica identities;
immutable committed receipt and current A2/A6 scientific READ/final visibility.
All positive publication APIs remain unavailable. No shared ABI is added.

Target suite: `test_fixed_scientific_packet.FixedScientificPacketTests` (five
methods). Run only this pure suite; no backend/store fixture or native process
is involved. Existing 17-case source qualification is retained unchanged and
must not be relabelled as this successor's full-suite evidence.
