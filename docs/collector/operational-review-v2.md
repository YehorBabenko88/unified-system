# Collector V2 operational review facts

Source implementation only. No owner approval record, protected setting,
workflow bridge, dispatch, phase file or execution is created here. C3 remains
**NOT AUTHORIZED**. A valid record, matching digest or provider result alone is
never a host/runtime permission or C3 PASS.

## Canonical public ABI

Pure module `unified_system.collector_operational_review` exports:

- `parse_authorization(raw: bytes, *, now=None) -> dict`
- `parse_review(raw: bytes, authorization_raw: bytes, *, now=None) -> dict`
- `derived_service_name(auth) -> str`
- `dispatch_title(authorization_sha256, authorization_commit) -> str`
- `phase_id(review) -> str`, `capture_attempt_id(review) -> str`

The two parsers return detached data, not capabilities. `now` is explicit for
deterministic tests; production callers use their actual admitted clock and must
repeat freshness/revocation checks under A5's owner boundary. Records must be exact
canonical LF JSON, duplicate-free, finite, builtin typed and at most 65536 bytes.
Unknown/missing fields and numeric bool/float/string aliases are rejected. Runtime
codec has no HTTP, token, issuer, file writer or native action.

The broker-only API is
`scripts.ci_collector_operational_admission.GitHubCollectorReviewProvider(token).acquire(ctx) -> bytes`.
There is no public opener, resolver callback, allow method or caller-True result.
Only acquisition is replaced in tests, through the existing legacy
`build_opener` seam; actual HTTP/context/JSON/review validation runs. Failures
close with `COLLECTOR_OPERATIONAL_REVIEW_REJECTED`, without private response data.

## Exact static authorization shape

Schema: `unified.collector.operational-authorization.v2`. Exact top-level keys:

```text
schema, scope, authorization_id, cohort_id, source, capsule, target,
graph_profile, evidence_requirements, bounds, issued_at, expires_at, approved_by
```

`scope` is `ADMISSION_FOR_C3_QUALIFICATION`; authorization/cohort/installation IDs
are canonical lowercase UUIDs. No actual computer name, absolute path, plan SHA,
run ID, approval digest, status-APPROVED or C3-PASS field belongs in this record.

- `source`: exactly `head`, `tree` (40 lowercase hex each),
  `source_manifest_sha256` (64 lowercase hex).
- `capsule`: exactly `manifest_sha256`, positive integer `manifest_bytes`,
  `archive`. Archive is exactly `{kind: UNPACKED_MANIFEST_ONLY}` or exactly
  `{kind: ARCHIVE, sha256: <64 hex>, bytes: <positive integer>}`.
- `target`: exactly `runner_label` (one of `windows-2022`/`windows-2025`),
  `job_name` (`collector-c3`), `installation_id`, `service_name_policy`
  (`UNIFIED_COLLECTOR_V2_INSTALLATION_UUID_SHA256_24`),
  `root_relative_runner_temp` (`unified-collector-c3/` plus installation UUID).
- `graph_profile`: `COLLECTOR_C3_FINITE_SYNTHETIC_V2` only.
- `evidence_requirements`: exactly `source_schema`, `capacity_schema`,
  `resource_schema`, `scope`, with values `unified.collector.source-admission.v2`,
  `unified.collector.capacity-admission.v2`, `unified.collector.resource-outcome.v2`,
  `ADMISSION_FOR_C3_QUALIFICATION`. These name required real evidence; strings are
  not evidence of source/software qualification, capacity or a resource outcome.
- `bounds`: exactly `workers` and `capture_attempts` (integer 1 each), `frames`
  (1..4), `frame_bytes` (1..1048576), `raw_bytes` (1..4194304 and at least
  frame_bytes), `duration_seconds` (1..120), positive `capacity_max_age_seconds`
  no greater than authorization lifetime, and `stop_policy`.
- `stop_policy`: exactly seven keys: builtin string `transport` equal to
  `NSSM_CONSOLE_CTRL_C_V1`; exact integers `console=0`, `skip_methods=6`,
  `kill_process_tree=0`, positive `console_grace_ms`, `owner_retire_seconds=5`,
  `actuation_timeout_seconds` in 1..60. Strict inequality:
  `console_grace_ms + 5000 < actuation_timeout_seconds * 1000 <= 60000`.
  No `margin_ms`, profile nesting, unit conversion or performance default exists.
- `issued_at`, `expires_at`: UTC `YYYY-MM-DDTHH:MM:SSZ`, valid now, with lifetime
  at most 24 hours. `approved_by` names the intended required User reviewer.

This shape does not expand v1 registration-only admission into START/STOP or
activation. The legacy validator still uses its original fixed v1 constants,
schema, transport and preflight behavior. Its extracted
`verify_protected_review(ctx, environment, history, *, environment_name, approved_by)`
is the same review-check body. Legacy `history=None` means preflight only; V2
explicitly rejects null/missing history before calling it.

## Actual GitHub review join

`ctx` has exactly string fields `event`, `repository`, `sha`, `source_sha`,
`attempt`, `run_id`, `actor`, `authorization_commit`, `authorization_sha256`,
`job_name`, `runner_name`. It is collected by the trusted broker from its actual
job context, not accepted as an operator runtime permission.

The provider reuses the existing fixed-repository GET helper, TLS defaults,
redirect rejection, timeout, body bounds, duplicate-key decoder, context guard
and extracted protected-review checks. It performs only six GETs:

1. Exact authorization commit, fixed path
   `docs/collector/ci-collector-operational-intent-v2.json`.
2. Actual `/actions/runs/<run_id>`.
3. Actual `/git/commits/<source_head>` for its tree.
4. Actual `/actions/runs/<run_id>/attempts/1/jobs`.
5. Already configured `/environments/collector-c3-operational-v2`.
6. Actual `/actions/runs/<run_id>/approvals`.

All URLs stay in `YehorBabenko88/unified-system`. Missing/403/redirect/pagination,
incomplete jobs, unconfigured protection, ambiguous/rejected reviews, stale scope,
wrong source/tree/job/runner or reviewer ID deny. The actual current run must be
manual, attempt 1, in progress with no conclusion, on
`.github/workflows/lab-stopped-service.yml`. Its API `display_title` must be exactly
`collector-c3-operational-v2 <authorization_sha256> <authorization_commit>`.
This binds the scope to the reviewed run, since run API does not expose dispatch
inputs. A title is not approval: the source/tree, actual assigned job, existing
required User reviewer, exact environment ID and actual approval history must all
join too. Existing self-review protection is preserved.

Exactly one current `collector-c3` job must match actual run/head/attempt and
runner name, approved label, and API hosted-runner group (`0`, `GitHub Actions`).
These API facts are correlation, not Windows computer-name or host/token/ACL
attestation; A5 must independently observe the actual assigned host.
Jobs API does not provide a job-environment field. The future reviewed bridge
must declare the protected environment on the fixed job after preflight; A5's
source admission must check that bridge. The returned run/environment review
facts do not independently attest that workflow declaration.
Missing qualified bridge/source admission therefore DENIES A5 phase issuance;
provider facts alone are insufficient. This remains an integration gate, not an
implemented workflow or a native qualification claim.

## Output and A5 ownership boundary

Output schema `unified.collector.verified-github-review.v2` has exactly:

```text
schema, scope, authorization_id, authorization_sha256, authorization_commit,
cohort_id, source, run, job, environment, reviewer, expires_at, response_bodies
run: id, attempt, event, workflow, head, tree, actor, created_at,
     display_title, status, conclusion
job: id, name, runner_id, runner_name, runner_label
environment: id, name, required_reviewer_id
reviewer: id, login
response_bodies: authorization, run, commit, jobs, environment, history
each body receipt: sha256, bytes
```

Only needed typed facts plus original response hash/size are retained. No comments,
private errors, raw headers, credential, private key or token is emitted. A matching
hash identifies bytes; it is not authentication. Parsing a fabricated facts record
does not prove HTTP acquisition: the trusted Admin broker/protected issuance path
must actually call this provider and A5 must verify actual file owner/DACL/stable
identity and current source/capacity/artifact closure. LocalService receives only
protected records and pure codec, never the provider, token or network path.

Service name is `UnifiedCollector_` plus first 24 lowercase SHA256 hex of canonical
LF `{domain: unified.owned-collector-stopped-service.v2, installation_id: UUID}`.
Activation revision is the authorization UUID; resolved local node ID is the
installation UUID. Phase UUID is UUID5(namespace=authorization UUID,
name=`phase:<actual run ID>:<actual job ID>`); capture UUID is UUID5(namespace=phase
UUID, name=`capture:1`). These are deterministic identities, not capabilities.

A5's actual elevated owner factory alone resolves
`unified.collector.resolved-operation-intent.v2` after real review and actual
host/source/artifact/fresh-capacity checks. It computes the initial service plan
under existing locks and proves `ABSENT_NEW_NAMESPACE`. Future fixed
`SAME_PHASE_OUTPUT` references must resolve actual REGISTER/PUBLISH receipts and
reconstruct plans under those locks. No fake unknown hashes or arbitrary graph
callbacks are provided here. The only graph is REGISTER_STOPPED ->
PUBLISH_ACTIVATION -> START -> STOP -> INSPECT_STOPPED -> REVOKE_ACTIVATION, with
one finite worker/capture; no REMOVE, restart, retry or second START.

Read-only repeated validation is not a new effect. Attempt 1 and current review
do not claim globally atomic single use; A5's durable phase journal must consume
unknown/attempted effects and prevent replay, and must recheck expiry/revocation
under the phase lock. No source code test grants this permission. A future manual
V2 bridge through the already registered workflow is still required and must keep
all ordinary/default paths denied. No workflow or protected environment is created
or modified by this change, and native C3 still needs exact owner permission.
