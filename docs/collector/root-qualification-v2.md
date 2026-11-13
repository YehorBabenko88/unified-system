# Root qualification outer DATA codec

This module joins closed canonical qualification records to supplied source/capsule/profile/copied-runtime/storage bytes. It acquires nothing and cannot issue a source admission, protected approval, grant, phase or C3 PASS. Supporting artifacts, their source/effects interpretation and maximum-case coverage remain NOT_ATTESTED. Missing authentic supporting evidence leaves the genuine factory DENY.

## Canonical API and two layers

`parse_root_qualification(release_raw, software_raw, *, authorization_raw, manifest_raw, profile_raw, copied_runtime_inventory_raw, storage_profile_raw)` returns a fresh detached dictionary with exact keys `release`, `software`, `collector_max_envelope_raw`, `execution_authority` (false), `supporting_facts` (NOT_ATTESTED), `measured_envelope_validation` (REQUIRED_BY_A5_PRIVATE_CONSUMER). Inputs are canonical duplicate-free ASCII compact sorted JSON+LF using existing codecs. Release/software/auth/storage/nested bytes each <=65536; manifest/inventory retain existing lab_release limits. No callback/provider/opener/True override exists. Failures raise generic ValueError without private payload.

Layer1 checks only outer record semantics and byte joins, current existing authorization validity, full existing manifest schema, finite profile, copied Python inventory and existing A4 storage-profile dataclasses. Nested envelope is bounded detached DATA: deliberately malformed empirical fields may survive this layer. It is NEVER sufficient to consume it without layer2.

Layer2 is A5's existing private `_validate_measured_max_envelope(measurement_raw, *, authorization_raw, manifest_raw, profile_raw, copied_runtime_inventory_raw, storage_profile_raw)` in unified_system/collector_service_capacity_v2.py, supplier commit c573dde6900b64e3ae6b9678f030f03e26e64fd3, rawSHA256 f349f13d4c5dede717a3d3351fcaf0fdd866492245a39406725c2775622f98e5. That supplier is absent from base cff; this module neither imports an ambient A5 checkout nor copies its empirical validator. Integration must adopt/verify exact reviewed supplier/source join and call it on returned collector_max_envelope_raw. Both layers still return data: Root's actual supporting-evidence/producer/coverage and A5's genuine protected custody factory remain required. No hash, source pin or status string authenticates evidence by itself.

## Exact outer wire shapes

Pin = exactly {sha256: lowercase64hex, bytes: builtin int1..2^63-1}. UUID canonical lowercase. All objects closed except explicitly unvalidated nested collector_max_envelope DATA. execution_authority is exactly false, never0.

release = {schema:"unified.collector.root-release-qualification.v2",scope:"ORDINARY_SOFTWARE_FOR_C3_ADMISSION",qualification_id:UUID,source:{head:OID40,tree:OID40,source_manifest_sha256:SHA,sources_sha256:SHA,overlays_sha256:SHA,runtime_sha256:SHA,dependencies_sha256:SHA,directories_sha256:SHA},capsule:{manifest:Pin,archive:Pin},profile_sha256:SHA,copied_runtime_inventory:Pin,primary_evidence:Pin,artifact_inventory:Pin,execution_authority:false}.

software = {schema:"unified.collector.root-software-qualification.v2",scope:"ORDINARY_SOFTWARE_FOR_C3_ADMISSION",qualification_id:UUID,release:Pin,test_cohort:Pin,source_effects_review:Pin,measurement_evidence:Pin,collector_max_envelope:object,execution_authority:false}.

IDs equal; software.release hashes exact supplied release bytes. Source joins existing authorization S and actual manifest sections. Profile pins match both record and actual manifest member; profile bounds equal authorization bounds. Copied runtime inventory is exactly every runtime/python/ manifest member and exact independent inventory bytes. Independent storage_profile_raw is decoded with existing RawCaptureProfile/CollectorContextProfile checks and compared to nested workload.storage_profile with numeric-type revalidation; it is not inferred from the envelope alone.

## Acyclic external records and archives

Fixed protected revision refs qualification/release.json and qualification/software.json are EXTERNAL to capsule C (a sibling capsule/ directory may hold C). Reject either fixed name inside manifest files, including case aliases. This syntactic check does not prove physical externality or discover renamed embedded copies; actual transport/custody must establish that. Artifact inventory must not include Q as transitive self-referential inventory; transport binding separately pins Q and the supporting-evidence inventory. Current parser never accepts an artifact inventory's bytes and cannot attest its contents.

Authorization's tagged ARCHIVE pin refers to the actual INNER unchanged capsule archive, not GitHub's outer wrapper. It must equal release.capsule.archive. UNPACKED_MANIFEST_ONLY contains no archive authority: release archive pin is retained only as unverified DATA and cannot authorize transport. No fabricated zero hashes/null future evidence. Future transport must prove actual archive bytes independently.

Source S/capsule C precede external Q; later commit A can carry static R plus fixed qualification-binding DATA. Existing f66 protected provider still requires actual run head/tree==S. Read authorization/binding at A; do not execute A as a substitute source. No workflow changes, dispatch, records or native execution are part of this module.

## Future private acquisition handoff (not implemented here)

The joint transport result has exactly eight fields: materialized_root, capsule_root, release_raw, software_raw, copied_runtime_inventory_raw, storage_profile_raw, artifact_inventory_raw, execution_authority:false. Genuine Admin broker/private factory acquires/verifies it; callers cannot supply it as a grant. LocalService reads protected records only and receives no GitHub token/network. Root-owned later transport must bind actual producer/source/run/job/artifact IDs and exact bounded payload; no arbitrary URL. Existing capsule verifier/stager and worker archive reader remain the mechanisms. This parser neither implements that handoff nor declares any current artifact qualified.

## Validation scope

Inert tests construct labelled fixture DATA only and use actual cff codec/manifest/profile/A4 validators. They exercise wrong source/closure/release/QID/profile/runtime/storage joins, byte/key/number aliases, fixed Q cycles, tagged archive meaning, legacy schemas, no callbacks and forbidden acquisition seams. A positive outer fixture intentionally is NOT an A5-valid measured envelope and NOT a genuine authorization record. Selected91 and tiny902 evidence remain distinct historical software results; neither is full current qualification or maximum workload. No new blanket vendor/all-OS-DLL authenticity gate is introduced. Actual used dependency/native closure is reviewed separately; service/native overhead remains unqualified until actual approved C3.
