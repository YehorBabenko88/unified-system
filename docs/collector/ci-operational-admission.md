# Hosted stopped-service operational admission

Status: **PENDING / C3 BLOCKED**. No authorization record is supplied by this change.

The owner directive requires separate operational admission before service creation
or ACL changes. The legacy hosted Windows stopped-service workflow previously ran
those effects on ordinary source events. Historical fixture results do not establish
Collector C3 acceptance or authorize office-host operations.

Push and pull-request events now run pure guard regressions on Ubuntu and fail with
`C3_OPERATIONAL_ADMISSION_BLOCKED`. The native matrix is skipped and remains
**BLOCKED, never PASS**. Existing stopped-service native commands, pins, matrix,
timeouts and artifact ownership checks are retained behind the admission boundary.
The admission job is FAILED on ordinary events; the native job is SKIPPED, not
reported as a failed native execution. Branch-protection required-check names are
UNKNOWN: they have not been queried or modified. This change grants no merge
permission. A skipped native job cannot count as C3 PASS in our acceptance matrix.

Only a manual `workflow_dispatch`, attempt 1, can request admission. Inputs are
`source_sha` (the exact dispatch source SHA), `authorization_commit` (40 lowercase
hex characters), and `authorization_sha256` (64 lowercase hex characters). The
record is fetched at that immutable commit from the fixed repository
`YehorBabenko88/unified-system`, fixed path
`docs/collector/ci-operational-authorization.json`. A SHA verifies integrity;
it does not establish human authority. No approved record is generated here.

The exact record keys are `status` (`APPROVED`), `SourceKind`
(`explicit_operator_record`), `repository`, `source_sha`, `workflow`
(`.github/workflows/lab-stopped-service.yml`), `environment`
(`collector-c3-stopped-service`), `matrix` (`windows-2022`, `windows-2025` in
that order), `permissions` (in order: `hosted-disposable-service-register-stopped`,
`hosted-disposable-acl`, `hosted-disposable-app-only-removal`), `attempt` (integer 1),
`approved_by` (configured required User reviewer login), and `expires_at` (UTC
`YYYY-MM-DDTHH:MM:SSZ`, strictly future and at most 24 hours away). Unknown or
missing keys fail closed. This scopes only the existing disposable hosted legacy
fixture; it grants no provider, real Collector installation, service start, office
ACL, training or protected-runtime permission.
Duplicate JSON keys are rejected in the record, remote configuration and review
history, including nested objects; ambiguous status or scope values cannot admit.

The read-only preflight must observe an already configured GitHub environment with
required explicit User reviewers before the native job can declare that environment.
Team-only/ambiguous configurations fail closed. This code never creates environments,
changes settings or weakens `prevent_self_review`. GitHub enforces the existing
environment review policy. Operator identity or a committed APPROVED string alone
does not prove a human approved anything.

After GitHub releases the protected environment job, a second guard revalidates the
record, expiry and configuration and reads approval history for this exact run ID.
It requires one unambiguous matching environment ID/name review, actually approved
by the record's configured User reviewer. Missing, rejected, duplicate, malformed,
unreadable or paginated histories deny before helper downloads or native commands.
Reruns deny; there is no atomic single-use claim. Every new run requires fresh actual
human environment approval. Root must not approve on the user's behalf.

Both network reads are GET-only, fixed-host/path, redirect-rejecting, size-bounded
and timed out. HTTP failures, missing configuration and API permission failures deny.
Only read permissions (`contents`, `actions`) are requested. A future operator must
configure protected admission and supply an actual reviewed record separately; this
source change performs neither action and does not dispatch the workflow.

Pure verification: `python -B -m unittest tests.test_ci_service_operational_admission
tests.test_ci_stopped_service_acceptance -v`. No native acceptance is executed by
these fixtures. The mandatory C3 test is retained and acceptance remains BLOCKED
until separately admitted execution produces a reviewed actual result.

API references: [environment configuration](https://docs.github.com/en/rest/deployments/environments#get-an-environment),
[run-specific review history](https://docs.github.com/en/rest/actions/workflow-runs#get-the-review-history-for-a-workflow-run).
