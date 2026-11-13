# Collector protected service source gates v1

Engineering base902a1704a16841d15d817ce17b48da1d3de19fda, tree
132e85fc08ca447c1bfedbb4cdaa4db24505be7d. Five new source files only.
This is an implemented read-only plan/revision boundary, not a working service.
No production API, V1 argv, V1 activation descriptor or V1 service kind changes.

## Implemented API

`collector_service_plan(capsule_root, manifest_sha256, root, installation_id,
node_id, boundary)` constructs a closed `unified.owned-collector-stopped-service.v1`
plan after actual existing capsule verification and fixed reviewed source checks.
The explicitly supplied boundary supplies readonly SID/host/native-tool metadata;
no native boundary is constructed by default. Source pins are checked before SID
lookup. The existing PSM1 is pinned as the declared executor but rejects this new
kind today. A plan does not imply that registration is available or authorized.

`check_collector_service_plan(plan)` verifies the original source capsule and
returns its manifest. It checks exact fields/types, canonical plan digest,
Collector-only kind/role, isolated argv, source/runtime/helper pins, fixed layout,
domain-separated service name, SID and native tool metadata. `_check_manifest`
performs the same policy join on an already verified installed manifest; it is
internal, does not authenticate a caller's dict and does not grant authority.

The plan uses the V1 field names plus `collector_profile_sha256`,
`source_manifest_sha256`, `collector_bootstrap_sha256`, `security_helper_sha256`
and `job_helper_sha256`; role is COLLECTOR and activation is BLOCKED. Python/NSSM
paths remain runtime/python/python.exe and runtime/nssm/nssm.exe. The raw entry
is sources/unified-system/unified_system/collector_service_entry.py. Bootstrap
is the sibling collector_service_bootstrap.py, not owned_python.py. Parameters
are exactly `-I -S -B "<absolute entry>"`. Service namespace is
UnifiedCollector_<24 lowercase hex>; LocalService/dedicated SID/demand-start and
AppExit=Exit expectations reuse existing semantics. No automatic restart.

`expected_collector_service(plan)` returns readonly live-SCM/NSSM expectations
with execution_authority=false; it does not inspect native state or prove parity.
Grid Job bytes have a capsule pin only: no independent primary-source approval,
neutral process adapter or Job execution is provided by that field.

## Genuine revision evidence, unavailable protected grant

Raw collector_service_entry.py accepts only [] or [--collector-worker], requires
effective -I/-S/-B, fixed local Windows drive and ordinary single-link stable
bootstrap bytes matching its compiled-in digest, then executes those held bytes.
It has no relative package/developer CLI fallback or arbitrary path argument.

The bootstrap loads the exact pinned existing stdlib service_bootstrap helper
bytes, reusing WindowsActivationKernel, read_file, local, parse and existing
admitted-byte capsule verifier/loader. It does not modify V1 code or manufacture
a V1 ProtectedActivation. The loader's existing ambient-namespace denial remains.
No candidate .pyc, site processing or ambient application import is substituted.

`read_collector_revision(service_root, *, kernel=None)` returns a
CollectorRevisionEvidence after actual checks. The default source implementation
reads current process Session0 with GetCurrentProcessId/ProcessIdToSessionId in
addition to existing LocalService/exact enabled dedicated SID/host admission.
Injected unit kernels exercise policy, not actual Windows token/API behavior.

Pointer schema is unified.collector-activation-pointer.v1 with exact schema,
revision_id, descriptor_sha256. Descriptor schema is unified.collector-activation.v1
with exact schema, revision_id, activation_plan_sha256, service_plan,
resource_receipt_sha256, collector_profile_sha256, source_manifest_sha256,
qualification_refs. The refs contain phase_id, source_evidence_sha256,
capacity_evidence_sha256, operational_admission_sha256. These are syntactically
checked references only, never proof of independent approval or receipt validity.
There are no invented full-runtime credentials or database fields.

Reader checks protected owner/DACL/stable held pointer/descriptor/profile/source
ledger bytes, plan/host/root/SID/hash joins, actual whole-capsule integrity and
full existing Collector profile policy. Every inventory path gets existing ACL
checks. `require_current()` repeats identity/Session0, protected document
identities/hashes, ACL checks and the existing streaming whole-capsule verifier.
Empty files remain supported. Evidence is not globally atomic against an admin,
publisher attestation, native acceptance, operational approval or execution grant.
The receipt/qualification digests have no independent resolver in this scope.

`read_protected_collector_activation(service_root)` performs the reader checks
then always raises OPERATIONAL_ADAPTER_NOT_AVAILABLE. It accepts no injected
approval callback. `run_protected_collector(grant, *, stop_event=None)` always
raises COLLECTOR_RUNTIME_UNIMPLEMENTED for every argument. Both raw entry forms
remain blocked with exit78; neither can execute capture. This is intentional
closed behavior while the real adapters are unavailable, not a mock worker pass.

## Missing shared parity and operational work

NOT IMPLEMENTED / NOT ALLOCATED:
- PSM1 additive exact Collector schema/argv/member validation, registration and
  live inspection. Existing V1 factory/checker still reject the Collector kind.
- Protected revision publication, actual receipt/provenance/capacity/operational
  qualification resolution and revocation adapters. A digest is not an ACK.
- Collector actuation/registry-proof parity over the same opened SCM handle and
  receipt/phase-bound owner authorization. Existing actuator accepts V1 only.
- Owner-approved neutral suspended-create/assign/resume Job adapter. Existing
  OwnedJobProcess is PG-plan coupled; ProcessDriver mandates health/listener
  policy. Neither is called through a fake plan or unapproved extraction here.
- SCM STOP/NSSM delivery/settings, cooperative actual Worker retirement,
  checkpoint-before-close ordering and complete descendant quiescence evidence.
  Synchronous local I/O is not made interruptible by an async callback or timeout
  check. No graceful checkpoint promise after forced termination.

Future C3 packet must pin sources/runtime/closure and independently authorize
actual LocalService/SID/Session0, ACL sealing/readmission/revocation, source and
resource approval, SCM STOP delivery, bounded owned-process retirement and
restart recovery. Uncertain retirement retains state as UNKNOWN without cleanup
or retry. Existing source-bound operational gate/protected review is mandatory.
Hosted unit PASS cannot satisfy this packet. Authority-dependent work is BLOCKED;
no A2 ACK is claimed. No provider, SQL, service creation, ACL or token provisioning.

## Local test boundary

Run tests/collector/test_protected_service_contract.py under CPython3.12.10 with
-I -S -B. Tests execute actual new validators/readers, old verifier and private
file operations. Kernel/initial helper load/verifier import-admission boundary
are injected; actual existing verifier and full profile decoder still run.
The fixture explicitly builds canonical primary LF helper source and substitutes
an inert NSSM pin; it is neither an executable capsule nor vendor qualification.
No native helper is executed, and no dynamic helper exec branch is exercised.
The Session0 Win32 source path is not invoked. V1/native tests are separate.

## Additive PSM1 Collector source parity allocation

This section supersedes only the earlier missing PSM1 **validation/dispatch**
item. It does not implement registration, activation, actuation or runtime.
UnifiedOwnedService.psm1 now has a separate closed Collector data validator and
expected-proof formatter. An explicit schema branch precedes V1 admin/SID/native
handling. All BEGIN/SEAL/REGISTER/INSPECT requests for this new kind still throw
COLLECTOR_OPERATIONAL_ADAPTER_NOT_AVAILABLE before effects. Unknown kinds never
fall through to a Collector acceptance path. No approval hash/extra request key
can unlock an action; a real phase/action/plan-bound Python boundary and actual
independent operational provider remain unavailable and mandatory for future work.

The validator checks exactly the Python plan field set, string/nested-key types,
kind/role/activation, root separation and fixed entry/bootstrap/python/NSSM argv,
reviewed entry/bootstrap/security/NSSM pins, hash syntax, native-tool metadata,
domain-separated name/SID and exact canonical plan seal. The canonical serializer
handles Python ensure_ascii escaping and UTF-16 surrogate pairs, with LF for this
Collector schema. It does not change the existing V1 seal or argv conventions.
Manifest/profile/source/Job digests are metadata joins supplied by the genuine
Python capsule reader, not independently qualified data or authority in PSM1.

Get-OwnedCollectorExecutorPin hashes the imported module file; the future Python
boundary must independently bind the exact primary executor bytes before loading
it. This read is not authentication of source provenance or of already executed
bytes. No hash is embedded into its own source. Only the NEW Python Collector
EXECUTOR_PIN is updated to the final primary LF script hash; no normalized CRLF
alias, alternate hash allowlist or V1 constant is introduced.

V1 helper source prefix/action tail are preserved, except the explicit new-kind
dispatch. Actual V1 factory/checker tests also cover executor cohort pairing:
an old saved plan is accepted with its retained exact old executor bytes and
rejected against the new script. A fresh V1 plan receives the new executor hash
with unchanged V1 shape/argv. This is not a claim that historical saved plans
work with substituted new executor bytes. Keep old tool/executor pairs together;
do not silently migrate an old plan, mutate its receipt or weaken a pin check.

test_service_powershell_contract.py launches a fixed PowerShell interpreter only
to parse source and evaluate selected pure function ASTs with effect-function
traps. It does NOT Import-Module, compile the native C# declarations, execute a
native command or call admin/SID/ACL/SCM/Job APIs. The executor-file hash getter is
injected with a Python hash of the exact source; its production module-loader
path is not exercised. New-kind tests assert zero effect calls and operational
DENY for every action through the actual extracted dispatch. Other tests check
closed fields/drift/Unicode seals, proof formatting and actual V1 pure pairing.
These results qualify source/inert contracts only, not Windows service behavior,
the complete module helper pipeline, independent approval or C3 readiness.

Historical test-boundary correction: the earlier reader runs at9166/dde3 injected
identity/Session0/ACL but still traversed service_bootstrap.local()'s actual
read-only GetDriveTypeW query on Windows. Their prior blanket zero-Win32 wording
was inaccurate; original logs/proofs are retained with a separate correction.
They did not exercise actual token, Session0, SCM, ACL or Job admission. The
current reader fixture additionally intercepts ctypes.WinDLL with a drive-only
inert double and denies every other DLL/function path. The new PSM1 test's Python
side denies ctypes.WinDLL entirely. Fresh logs after this isolation change are
separate from those historical results; parser subprocesses remain explicitly
source-only and are not protected/helper/native pipeline qualification.

Executor getter custody correction: stream/hash acquisition now occurs within
try/finally, both disposals are independently attempted, and a primary error plus
all cleanup errors is retained as COLLECTOR_EXECUTOR_CUSTODY_UNCERTAIN aggregate.
No hash is returned until cleanup succeeds. Inert factory/open/hash/dispose fault
controls execute the extracted getter's actual custody logic with only module
metadata, stream acquisition and hash acquisition expressions substituted.
The real module-loader/file-open/hash-provider path remains NOT_RUN. Seven cases
cover success, open failure, hash-factory failure, each disposal failure, factory
plus stream-dispose failure and computation plus both disposal failures.
Original failing controls are retained separately from the successor results.
