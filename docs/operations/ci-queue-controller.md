# Bounded CI Queue Controller

Scope: offline development observations, permanently non-authorizing. No physical,
provider, production, runner, or GitHub mutation operations are implemented.

Reuse: `unified_system.journal.Journal` supplies SQLite transactions, hash-chain
integrity and expected-sequence writes. `OBSERVING` receipts carry the version
marker `unified.ci-queue.v1`; this is not a second journal or consensus service.
Scheduler/Consul authority is unchanged and no clock value grants authority.

Construct an exact `Pin(repository, workflow_id, run_id, attempt, source_sha,
job_id)` from separately verified metadata. `Controller.create(path, pin)` creates
a dedicated single-writer journal using atomic exclusive file reservation;
`Controller.open(path, pin)` explicitly resumes
it. Existing, foreign, corrupt, oversized or mismatched journals fail closed.
Initialization failure retains the partial owned reservation; it is not deleted or
silently adopted. Constructor calls require exactly the immutable `Pin` type.
Never remove a journal to bypass its observation limit. Missing journals must not
be recreated during restart: use `open`, not `create`.

`observe(captured_bytes, now=integer_epoch_seconds)` accepts at most 256 KiB of
JSON with exactly `run`, `job`, and `artifacts` keys. These are captured GitHub
run/job API objects and an artifact object list, not arbitrary command strings or
URLs. Every job/run identity must match the pin. There is no collector, executor,
network client, polling loop, shell, token parameter, dispatch, rerun, cancellation,
merge, or authorization renewal method. One call consumes one bounded observation,
including duplicates; a duplicate cannot reset the schedule or count.

The initial interval defaults to 30 seconds and doubles to a 900 second cap,
with reproducible nonnegative jitter derived from the persisted seed. Limit defaults
to 16 observations (maximum 256). Calls before the persisted next timestamp,
including reversed-clock calls, fail without consuming or resetting the schedule.
An external caller may schedule another invocation; this module never sleeps.
Timestamps are scheduling and evidence fields only. Terminal conflicts stay UNKNOWN.

States: QUEUED means waiting, RUNNING means reported in progress, SUCCESS/FAILURE/
CANCELLED require matching completed run and job conclusions. Missing/null or
unrecognized conclusions and inconsistent terminal reports produce UNKNOWN.
INFRA_BLOCKED is reserved for a separately verified infrastructure evidence adapter;
the captured status ingestion never infers infrastructure cause from queue age,
timeout, missing runner or missing steps. A queued job is not a code defect.

The protected original's authorization receipts are CONSUMED and can never
authorize a retry. Its full immutable identity is repository
`YehorBabenko88/math`, workflow `409676563`, run `42352374979`, attempt `1`, source
`2446d04624469e34aa96ed766be7a4887d6d654c`, job `128343065197`. A pin using that
protected run ID with any changed field is rejected. Ordinary CI runs are
NOT_APPLICABLE: the module does not invent an authorization or a consumption event
for them. Both classifications are immutable local configuration facts; neither
grants permission. Observation payloads cannot change them.

GitHub's queued-job `runner_id: 0` is preserved as the raw scalar fact `0`, with
`runner_assignment_state: UNASSIGNED`. Missing/null assignment is also unassigned;
only a positive integer yields a reported ASSIGNED observation. This does not
authenticate the capture. A queued job's API `started_at` may be populated while
its runner remains unassigned; this does not make it RUNNING or SUCCESS.

The real queued regression derives its scalar fields from the archived Math115
`math115-observation-240m/run.json` and `jobs.json` snapshots, without CI filesystem
or network dependency on that archive. Exact original-byte SHA256 provenance:

- run.json: `24670c428528cea08c791fe31e3a7561bff78dd058006f20bdab8c2da09e03ec`
- jobs.json: `a9447f5db6237d4811da9275202963c4dc043728188f35175787adf2f026fa6f`

The checked-in fixture is deliberately reduced; these are hashes of the original
archived inputs, not hashes of the reduced fixture. Actual full captured bytes
were also replayed once locally; source hash and sanitized receipt are separate
evidence. No new GitHub request is needed for this regression.

Only allowlisted scalar metadata, integer artifact IDs, raw SHA256/reference, and
sanitized timestamps are persisted. Names, arbitrary payload fields, credentials,
logs, runner names and artifact URLs are omitted. Raw bytes stay with the caller.
`UNVERIFIED_CAPTURE` records data origin independently of the reported CI state;
matching pins and a raw hash do not authenticate GitHub, establish queue root cause,
prove hosted CI PASS, or qualify Windows Home/Pro/native operations. Local Journal
hash chains detect corruption, not a hostile writer recomputing the entire chain.

CI uses CPython 3.12.10 on Windows and Ubuntu, stdlib only, fixed test IDs, primary
repository raw Git-blob comparison before/after, isolated interpreter flags, pinned
actions and no dependency cache. Tests never contact GitHub. Current local execution
includes CPython 3.12.10 and 3.15.2; hosted and native qualification remain separate
evidence.
