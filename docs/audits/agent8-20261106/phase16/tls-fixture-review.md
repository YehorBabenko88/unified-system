# Bounded TLS fixture hygiene triage

Requirement: classify four named private-key fixtures, references/trust/package use, avoid false production-secret findings.
Repository: meta_analyse; Draft PR77; exact HEAD88b45c328bfdc8131ff0c6d139fddd8b27a4050c; tree83304074f9cc3f90c09615c7f6920e1a07eab0c6.
Environment: static Git-object and source inspection on independent Windows clone. No TLS script executed, keys generated/exported, system trust modified or external connection made.

Actual: four tracked docs/commissioning_evidence_v3/tls-loopback/{ca,good,self,wrong}.key are explicitly documented disposable loopback fixtures. Their SHA256 matches historical EVIDENCE_HASHES and exact Git/local bytes. Only hashes/paths/Git identifiers are recorded, no key bytes. audit.py generates two-day CA/localhost/wrong.invalid/self-signed fixtures, binds127.0.0.1 and trusts the CA only via an explicitly constructed SSLContext(cafile=...), retaining required certificate/hostname checks. Fixture notice prohibits OS trust installation. No system trust installation call identified in this script.

No named fixture/test-CA path references were found in inspected src/commissioning runtime files; scripts/s1_source_reference.json contains historical source hashes. This bounded static result is not a proof about external deployment or all dynamically supplied trust/configuration. No production credential use, compromise or actual misuse established. Severity INFORMATIONAL hygiene recommendation; no new confirmed P0/P1/P2 defect from the filename heuristic alone.

Package boundary: all four are included in the tracked Git source snapshot. Setuptools package discovery is src-only; main CI uploads named public-platform/public-evidence/public-benchmark projections rather than directly selecting the historical fixture directory. Final built wheel/installer/release payload was NOT inspected, so artifact exclusion and operational admission remain NOT_QUALIFIED.

Recommended narrow admission rule: exclude the exact historical tls-loopback fixture prefix from deployable payloads and fail final artifact inventory if present; never accept these public fixture keys/test CA as operational identity or trust roots. Distinguish labeled source/evidence archives from installable runtime payloads. Preserve historical files, original evidence hashes and source-proof references; no rotation/history deletion warranted by this evidence alone. ROOT and component owner receive recommendation; no production edits by A8.

Evidence: tls-fixture-review.json; reproducible static checker ../review_tls_fixture_hygiene.py. Expected result met for fixture classification/evidence integrity only; runtime/package admission NOT_RUN. Overall NO-GO remains6P1/1P2; physical and Tailscale removal BLOCKED.
