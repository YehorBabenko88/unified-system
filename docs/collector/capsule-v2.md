# Collector kind in the existing LAB capsule verifier

Implementation allocation: base408cfabe8787ace1808db2ec4b9f436a502336c1.
Proposed Collector schema `unified.lab-release.collector.v1` is a separate kind
in lab_release, not a replacement installer or trusted-publisher format. This
wire fields below were ACKed by Root for its existing builder. The kind does
not grant execution or installation.

Public parse_manifest/verify_capsule/stage_capsule signatures remain unchanged.
Existing unified.lab-release.v1 parsing/reporting and six-source LAB_SIMULATION
semantics remain unchanged. Collector capsules must be rejected by the existing
V1 service_plan before SID lookup or any native boundary call. The same guard
also covers direct _check_plan/ServiceResource callers before V1 member handling.

## Proposed closed fields

Top-level exact keys: schema, mode, release_id, sequence, permissions, sources,
files, directories, dependencies, collector_profile, source_manifest, git,
runtime, overlays (14 keys).
Mode SYNTHETIC_OFFLINE. Permission keys provider_rest, provider_websocket,
trading, training, math, public_submit, authority_mutation, service_creation,
acl_changes are all literal false; numeric zero is rejected.

Sources are exactly unified-system and grid. Each retains existing repository,
root, commit, tree, version, dependencies fields and adds file_pins. Source roots
remain sources/<id>; repositories remain existing canonical identities. A
file_pins entry maps source-relative path to sha256, bytes and canonical Git
blob_oid. The SHA1 preimage is `blob <byte length> NUL <exact bytes>`; SHA256 and
byte length are also mandatory. This checks byte identity, not publisher trust
or the authenticity of supplied Git commit/tree metadata.

Overlays are an ordered list (proposed maximum16), each exact source, commit,
tree, files. Files uses the same source-relative pin map. No delete/rename or
implicit EOL transformation. Apply base source map then overlays in given order;
last explicit overlay wins. Final source inventory must exactly match the staged
source files and their pins. Reordering conflicting overlays changes expected
bytes and must reject. Unlisted, escaping, foreign-source or case aliases reject.

Files/directories reuse existing exact path/case-collision/ancestor inventory,
individual/aggregate byte limits, ordinary single-link no-symlink/reparse checks,
stable held reads, capsule hash and no-extra-file/no-extra-directory walk. The
same verifier/staging code performs integrity checks and copies; no application,
interpreter, Git binary, archive or source code from the capsule is executed.

dependencies retain name/version/lock_path and add lock_sha256, equal to the
corresponding file pin. runtime is exact python {path,version,sha256} and lock
{path,sha256}; paths must be in files and hashes agree. These are declared pinned
runtime/version/lock bytes, not an observed executable version or runtime grant.
collector_profile, source_manifest and git likewise name pinned relative files;
profile and source_manifest must be distinct. The profile is bounded to32768B,
canonical JSON and checked as DATA after stable capsule inventory. Its schema
is unified.data-only-collector.profile.v1, mode SYNTHETIC_OFFLINE, grid profile
grid.data-only-collector.v1 and instrument identity synthetic-btcusdt-v1. Its
source_manifest_sha256 must equal the actual pinned source_manifest file SHA256.
Network rest/websocket and feature trading/training/math/public_submit/
authority_mutation must all be literal false. No candidate profile code imports.
All other policy remains Root's existing trusted runtime Collector validator;
report profile_policy=RUNTIME_VALIDATION_REQUIRED. No fake runtime_config/
research credentials/instruments field is added. Source ledger and manifest
must not introduce a self-hash or invented merged Git HEAD.

Python version is exactly3.12.10 and a dependency named python must match its
declared version and runtime lock path/SHA. Source commits/trees and source
semantic versions remain metadata requiring separate primary-source admission.

## Reports and scope

Collector reports mode SYNTHETIC_OFFLINE, execution DATA_ONLY,
execution_authority=false and service_admission=false. Immutable bytes do not
authorize provider sends, native Authority, SCM, ACL, process launch or C3.
Unknown schema or extra manifest fields reject. Successful stage is inactive local
copy/integrity only; existing target and source/target overlap reject.

Tests use inert private files and actual verifier/parser/staging functions;
one early V1 kind guard uses a verifier-result double only to isolate whether
SID lookup occurs; another passes an actual fully verified Collector capsule.
No SID/native object is issued or called. Existing V1
test_lab_release suite remains an independent unchanged compatibility check.
The local suite contains18 Collector cases plus the unchanged11-case V1 suite.
Original REDs and final source pins/results are recorded outside the source
tree; passing byte checks do not establish the actual declared Python version.
No tests or docs here claim C1/C2/C3/service/publisher/primary-source attestation.
