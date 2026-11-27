# Six-profile synthetic cloud runtime proof

`integration/verify_runtime_stack.py` exercises one actual `RuntimeSupervisor`
through the existing config-v2 `run_runtime` loop: five owned module processes
and Unified's in-process journal/snapshot/API profile. It is a Linux managed
cloud integration proof, not an installer or production launcher. It rejects
execution unless explicitly requested in the managed cloud environment, and
rejects office hostnames before creating output, databases or processes.

It uses independently pinned clean local Git capsules for all six modules,
externally pinned Python/Node/Git executables, the existing isolated Python
bootstrap (`-I -S -B`), and an explicit installed fixture dependency root. No
source HEAD is inferred from a dirty checkout. Local sources may advance after
review: the exact externally supplied committed objects remain the inputs.
Neither source consistency nor a matching checksum establishes authenticity.

## External inputs

Supply a reviewed JSON file outside the repositories using this exact shape:

```json
{
  "git": {"path": "/absolute/local/git", "sha256": "<64 lowercase hex>"},
  "python": {"path": "/absolute/local/python3.12", "sha256": "<64 lowercase hex>"},
  "node": {"path": "/absolute/local/node", "sha256": "<64 lowercase hex>"},
  "dependencies": {
    "path": "/absolute/local/fixture/site-packages",
    "sha256": "<64 lowercase hex inventory digest>"
  },
  "sources": {
    "unified-system": {"path": "/workspace/unified-system", "commit": "<40 lowercase hex>"},
    "grid": {"path": "/workspace/bybit-cluster-grid", "commit": "<40 lowercase hex>"},
    "math": {"path": "/workspace/math", "commit": "<40 lowercase hex>"},
    "meta_analyse": {"path": "/workspace/meta_analyse", "commit": "<40 lowercase hex>"},
    "strattester": {"path": "/workspace/strattester", "commit": "<40 lowercase hex>"},
    "terminan": {"path": "/workspace/Terminan", "commit": "<40 lowercase hex>"}
  }
}
```

Placeholders above are documentation, not accepted pin values. Supply immutable
full commit IDs and independently reviewed executable/dependency hashes; do not
learn an expected value from the candidate immediately before treating it as
trusted. The script does not fetch remote sources or infer a trusted publisher.
Executable paths must refer to actual files, not final-component symlinks, and
the invoking interpreter must match the pinned Python executable.

The dependency digest is SHA256 of compact, sorted-key JSON mapping each
POSIX-relative `.py`, `.so`, `.pyd` or `.dll` file below the dependency root to
its SHA256. Ignore paths containing `__pycache__`. JSON uses
`sort_keys=True, separators=(',', ':'), allow_nan=False` and UTF-8 encoding.
The inventory is bounded to 20,000 files and checked before and after execution.
This describes installed cloud fixture bytes, not an authenticated production
package closure. Site initialization and `.pth` execution remain disabled.

## Fixture requirements and execution

Use the existing authorized, disposable PostgreSQL18 regression fixture on
loopback port 55438, database/role `grid_test`. Connection credentials remain
local in the fixture-specific script; do not publish connection strings or
private process nonces in evidence or documentation. The role must be able to
create/drop a uniquely named test database. The proof verifies PostgreSQL major
18 and the expected fixture database, creates its own random database, and drops
only that database in cleanup. It does not accept arbitrary database endpoints.
Do not run it against office, user-owned or production databases.

The explicit dependency root needs the already provisioned Grid runtime and
fixture-test dependencies (including `asyncpg`, `uvicorn` and the existing test
fixtures' `pytest` import). This proof adds no production dependencies or lockfile
changes. A reproducible signed dependency installer is a separate requirement.

After the script is committed and its bytes reviewed, invoke the externally
pinned interpreter, for example:

```sh
/absolute/local/python3.12 -I -S -B integration/verify_runtime_stack.py \
  --pins /workspace/.onboarding/mission4/reviewed-six-runtime-pins.json \
  --output /workspace/.onboarding/mission4/six-runtime-unique-attempt \
  --execute-isolated-cloud-test
```

The output directory must be new and under `/workspace/.onboarding/mission4`.
Execution needs the managed cloud loopback/socket permission. Keep failed
attempts. Do not edit expected pins, remove assertions or reuse output paths to
conceal a failed result. A later source change requires a fresh reviewed input
file and attempt; it does not rewrite earlier evidence.

## Evidence and limits

The report records its own script SHA256, exact six source commit/tree identities,
source/dependency postchecks, owned process/database cleanup, and the closed
failure stage if blocked. Outputs include startup states, the real supervisor
and Terminan snapshots, STOPPED state, and actual numerical/history/results API
responses. Private nonce/process records are removed only after owned stop is
proved. Capsules and failure evidence remain outside the source repositories.

Assertions cover dependency-ordered startup, five actual private nonce health
responses and missing/forged authentication rejection, the real read-only public
API and Terminan UI, Math's numerical/scientific endpoints, actual Grid synthetic
history export through Meta's causal analysis HTTP API, and a real synthetic
ResearchRunner receipt through Strattester's read-only results API. Grid stays
`INFRA_ONLY`; all configured exchange endpoints are unavailable loopback targets.
Research receipt admission is local synthetic fixture policy, not production
owner trust. Final administrative STOP must persist for all six profiles and
all owned subprocesses must exit.

`PASS_CLOUD_FUNCTIONAL_ONLY` proves this bounded cloud scenario. It does not
qualify publisher signatures, enrollment/rollout permits, production dependency
closure, immutable release transport, native installation, real market history,
live public feeds, paper execution, training, multi-node HA or physical
acceptance. Physical, trading and training authority remains false and production
remains `NO_GO`. No ADMINIT/office activity is permitted. No workflow automatically
runs this proof until its PostgreSQL fixture and dependency closure are explicitly
provisioned and reviewed.
