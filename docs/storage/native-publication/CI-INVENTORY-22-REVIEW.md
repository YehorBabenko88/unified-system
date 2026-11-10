# Source-only inventory correction for review

Parent cc78e5b0db8fe7f25cec5b99e7ac8804dfcf5493 produced original hosted
EXACT_CASES failures before fixture execution (PR run42877585984 and push
run42877577568, attempt1, Windows/Ubuntu). Original RED logs remain preserved
outside the checkout; this correction does not relabel those runs.

Only qualify.py, new inventory_controls.py and this report change. Workflow,
matrix, action pins, runtime, physical/raw-Git pre/post checks, clean worktree,
origin checks, no-skip requirements and qualification flags remain unchanged.

ORIGINAL_REQUIRED contains the exact original 17 ID strings in their original
order. SHA256 of ASCII newline-joined IDs with final newline:
33b577e317ec44aa66ab2b0251831cef884808025dc180b98e4d8323b6017960.
FIXED_PACKET_REQUIRED contains the exact five fixed-packet IDs, hash under the
same rule 234b647d1f74dbbd9e8ed04f4be2d06142b7c7b020d949d2c85067701060a507.

The actual validator checks both group pins, group lengths and uniqueness, then
rejects duplicate actual IDs and requires exact sorted union equality. Returned
validated union length drives result count, existing report and printed count.
No new report schema/field or shared publication ABI is introduced.

The stdlib-only helper supplies six pure controls to the actual validator.
It has a non-test_ filename, so mandatory fixture discovery remains 22 cases.
Inside the qualifier these controls run after full pre-import Git/physical and
clean-source guards, but before fixture discovery/import. Controls write a
separate inventory-controls.log; their six results are not fixture counts.

Pure local TDD: missing validate_inventory RED is one setup KeyError, not six
test failures. Successor GREEN is six controls, zero failures/errors/skips on
CPython3.12.10 -I -S -B. No project/fixture imports or fixture executions were
performed for this review. In particular old17/new5, actual ObjectStore/SQLite
and os._exit child remain NOT_RUN on this successor pending Root separate lane.
Hosted qualification and publication await Root/A8 exact-source review.

No native/backend/runtime admission or retries of original hosted runs.
LOCAL_UNATTESTED, strict D4/logical DISABLED, public DENY remain unchanged.
