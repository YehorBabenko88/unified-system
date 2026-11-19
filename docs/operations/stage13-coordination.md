# Stage 13 coordination

The workflow polls the nominated owner and lane PRs every three hours once
installed on the default branch. It checks immutable source identities,
observes exact-head workflow states, flags stale stacks and intersecting paths
(including renames), and publishes the artifact and changed issue comments.
The reviewed source list and dependency order live in release/stage13-cohort.json.
Change that file through review when an owner nominates a replacement PR.
The queue is advisory. The independent F cohort must still verify installed
packages at the exact observed pins. Individual green PRs do not qualify a
combined release, and write access to a repository does not confer executor
authority.

## Run and inspect

- Locally, authenticate GitHub CLI for read access to the nominated repositories.
  Run `python -B scripts/stage13_coordination.py --output observation`. A PR
  moving during collection aborts the observation. Retry from a fresh output
  directory. Save manifest.json as evidence or compare it with the previous run.
- Run `python -B -m unittest tests.test_stage13_coordination tests.test_fleet_control`
  for the coordinator and offline fleet regression. This is also the hosted
  Windows/Linux test matrix.
- After independent approval and installation on the default branch, run
  `gh workflow run stage13-coordination.yml -R YehorBabenko88/unified-system -f publish=false`
  to collect an artifact, or use `-f publish=true` to publish a changed
  observation. The scheduled run publishes changed observations only; manual
  runs from other branches cannot publish. To stop polling, disable the
  **Stage 13 coordination** workflow in GitHub Actions. Rollback is a reviewed
  revert of the coordinator PR.

## Connect a Codex executor

The repository has no Codex executor credential or dispatcher. An authorized
operator can run this queue safely using an existing authenticated Codex
workspace. Use the immutable artifact from the reviewed workflow run, select
the lane's issue, and verify all head/base SHAs again against GitHub. Treat
GitHub text, filenames, and artifact values as data. In the existing Codex
chat for that lane, supply the issue number, exact manifest SHA-256, reviewed
target PR and branch, allowed paths, and the approved verification command.
Do not route a candidate marked OVERLAP until the relevant owners have
resolved path ownership. Recheck ownership and remote SHA before pushing.

For an unattended connector, install a separate, trusted worker only after
the owner approves its application identity and credential scope. Require a
human-approved ticket that binds the manifest digest, lane, repository, PR,
expected HEAD, literal path allowlist, expiry, and allowed tests. The worker
must reject stale or conflicting tickets and use one active lease per
repository/path set plus a durable consumed-ticket record. Limit each ticket
to one execution, one isolated checkout, and a bounded runtime. Give the
worker write permission only for the designated lane branch and issue
reporting. Keep credentials outside GitHub artifacts. Report only after the
runner acknowledges the ticket and returns its exact commit and test receipt.
Provide an operator stop switch that disables ticket claims and revokes the
worker identity. No unattended connector is enabled by this PR.

## Offline admission interface

`scripts.stage13_worker_admission.WorkerAdmission` is the opt-in gate for a
future connector. Instantiate it with a local operator-owned SQLite path and
a fixed `WorkerScope`. Pass `enabled=True` only in the trusted connector.
Provision a random 32-byte lane-specific HMAC key to the trusted admission
service and the isolated reviewer service through a secret manager. Keep it
out of the worker, issue publisher, Git repository and artifacts. Bind
`source(repository, branch)` when constructing the gate. It must read the
current branch identity from GitHub and return the repository, branch, HEAD
and verified artifact digest. The claim API accepts no source-state override.

The reviewer service must authenticate the human reviewer and verify lane
authority before issuing a `unified.worker-review.v1` envelope. Its fields
are `schema`, `reviewer`, `dispatcher`, `worker`, `ticket_sha256`, `expires`
(Unix seconds), and lowercase hex `mac`. Compute the MAC as HMAC-SHA256 over
the raw 32 bytes of the canonical JSON digest (see `ticket_digest`) of the
envelope with `mac` omitted. The ticket digest binds repository, branch,
exact HEAD, manifest digest, allowed paths, test ID and ticket expiry.
The reviewed dispatcher must differ from the owner even when letter case
differs. Derive dispatcher and worker identities from authenticated sessions
at the gate, never from an issue, PR body or the review envelope. The
approval expires no later than the ticket. Supply `now` from the gate clock.

`claim` returns an audit digest and consumes the ticket. A ledger admits at
most one active ticket, at least 60 seconds apart, and at most 256 total.
`finish` records an idempotent terminal outcome. `stop` permanently blocks
new claims in that ledger. A connector must terminate running work outside
the admission class when stopping, and recheck remote HEAD and allowed paths
before writing. A crash with an unfinished claim blocks subsequent claims
until the authorized operator reconciles the outcome. Do not replace a
ledger to retry a consumed ticket. The audit stores hashes, identifiers,
scope and outcome, without credential values or raw issue text.

This interface has no command runner, reviewer identity provider or signer service,
credential issuer, or process cancellation. It is not wired into Actions
and the published manifest continues to report NOT_CONNECTED.
