# Independent Root F16 review

Overall NO-GO, 6 P1 / 2 P2 open. Global F16 remains OPEN; this is one exact-source component correction only.

- Requirement ID: A8-F16 / Root final-integration raw Git object binding.
- Repository / PR: unified-system / Draft PR26.
- Exact reviewed HEAD: 18085568df01bdbc4df74404e3c650ec30bb7d6b.
- Tree: ebdd08b00d78c0c130d78747fed717bc636793bf.
- Published descendant: 18a6bfad356446552f7dadb345880513c35ee86d. Descendant ancestry verified; no automatic qualification of that later candidate.
- Environment: local isolated Windows clones, Python 3.12 audit venv and previously hash-pinned tzdata. Original embedded workflow Python executed with local metadata explicitly marked NOT_HOSTED.
- Test name / expected: clean exact75/no skip succeeds; changed raw source hidden via blob/tree replacement must fail before tests; post-test source mutation, wrong ID and skip must not yield acceptance.
- Actual: see original per-case logs/receipts and machine report. Old c9f3735 blob/tree controls accept75 with false binding; fixed clean accepts75/0skip; fixed blob/tree controls reject before tests without receipt. Post-test hidden mutation, wrong ID and skip reject. Skip emits source-binding receipt but exits failure; that receipt is not acceptance PASS.
- Status: PASS for independently tested offline correction; hosted CI NOT_QUALIFIED; physical and Tailscale removal BLOCKED.
- Severity: P2 component correction verified, global F16 pending other applicable guards.
- Required correction: complete independent review of A3 and remaining applicable guards; separately qualify mandatory hosted/platform/runtime/physical gates.
- Evidence: [machine report](root-f16-review.json), original stdout/stderr/test logs and receipts in this directory; [primary PR snapshot](primary-pr-snapshot.json); harness ../review_root_f16.py.

The fix commit changes exactly workflow plus one document relative to its parent dd8b4ff9ace0a75dd81d0ab654e97a1e2319259a. All Python and PowerShell sources, tests and75-ID inventory match earlier c9f3735. Both subprocess Git call sites (initial ls-tree and shared wrapper) force --no-replace-objects. Clean protected inputs were independently rehashed against primary Git blob OIDs and receipt raw SHA256s. Existing raw EOL/regular-file checks, before/after source equality, exact75/prior59 IDs and zero-skip assertions remain.

Every mutation ran only in a new --no-hardlinks clone with its own .git/common directory and no alternates; no developer/shared worktree refs were changed. No actual hosted tampering is alleged. No full-suite, native source-authenticity, runtime authentication, LAN transport, production or physical acceptance is inferred. No real orders, production deployment, host/network change or Tailscale removal performed.
