# PR64 independent negative composition acceptance

Exact Unified HEAD `0342413b76e5574e7e303bfdd8a4ea2417ae8d93`, tree `438a6309214a90133d3cce4e4d1a7009a50c32c7`; explicit Grid dependency `539239e3c11ec9e86aa24365d74a68301fdf1185`. Source/safety review preceded execution. All 11 paths are additions relative to 3af; prior production files are unchanged. This is a separate source pair, not advancement of Grid40e release pins.

| Requirement ID | Repository / PR / exact HEAD | Test | Environment | Expected | Actual / status | Evidence | Severity / correction |
|---|---|---|---|---|---|---|---|
| A8-NEGATIVE-COMPOSITION | Unified PR64 / 0342413 above, Grid539 | 11 actual fixture cases plus 5 DATA/boundary cases | Own Windows CPython 3.12.10, pinned offline dependency environment, loopback TLS and ACL-default-deny three-voter Consul | Current authentication; denied submit/unknown lookup; invalid identity/policy/leader reject; cancellation and cleanup fail closed | 16 unique PASS / 0 skip | [Original log](actual16/tests.log), [qualification and primary maps](actual16/qualification.json), [original process lifecycle stdout](stdout.log) | Scoped PASS; no positive admission inferred |
| A8-NEGATIVE-GUARD | Same exact sources | Wrong HEAD; Git environment override | Separate isolated interpreter invocations | Reject before native fixture | Both rejected before fixture entry; not extra application PASS cases | [Controls](guard-calibrations.json), [wrong HEAD](wrong-head.stderr.log), [Git override](git-env-override.stderr.log) | Scoped guard calibration only |

Actual accepted mTLS, fixed broker open_session and native ResearchLabAuthority submit/lookup were exercised against own Consul. Revoked/expired policy, destroyed leader, malformed inputs and closed TLS remained errors. Same original twice remained denied without a job; absence lookup remained UNKNOWN. Concurrent second call rejected rather than queueing. Async task cancellation was observed, not cancellation of an issued research job. The final case killed only two retained own Consul processes during cleanup, preserving the original error and local context invalidation. Healthy session retirement was separately queried; successful invalidate_context alone is not a strong native-retirement receipt.

1635 Unified and 800 Grid files were checked before/after, with exact module origins, no extra files and all three retained own Consul process handles waited (PIDs 93312, 137848, 139456). The initial startup confirmed three voters and one leader. No office node or foreign process was touched. Full scientific E2E, public HTTP endpoint, worker/job grants, quota/resource admission and publication remain unqualified. Owner original16/RED and five reported calibration artifacts were not independently authenticated in this phase and are not included in A8 counts.

RELEASE_MANIFEST_STATUS: component manifest only, not approved release.
NODE_INVENTORY_STATUS: not requalified.
CONTRACT_STATUS: negative internal scope reviewed, no positive API acceptance.
OFFLINE_TESTS: isolated integration 16 PASS; two separate guard rejections.
WINDOWS_CI: NOT_RUN here; no hosted transfer.
PHYSICAL_TESTS: BLOCKED.
P0_P1_P2: 7 open P1 / 3 P2 unchanged; absence of P0 not proven.
EVIDENCE: original logs and exact source maps linked above.
NEXT_ACTIONS: hosted exact-head qualification and separately authorized positive APIs remain required.
GO_NO_GO: NO-GO; TAILSCALE_REMOVAL BLOCKED.
