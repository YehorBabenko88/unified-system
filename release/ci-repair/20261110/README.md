# CI boundary repair and retained acceptance limits

This package preserves the original RED inventory at Unified source
`01630597fb418d5a76a93c8b09750683dfe49b94`: 32 completed runs,
21 SUCCESS, 11 FAILURE, 22 failed jobs. Category counts overlap. Original
logs/artifacts remain retained; no manual retry replaces them.

The Gateway fix is Draft [PR76](https://github.com/YehorBabenko88/unified-system/pull/76),
source `71989562c51a008201babb222391211757eaf402`, tree
`91306124644e6c3f304fe7e7971a012f3298680a`. The original synthetic
certificate failed explicit STRICT with verification code85 (missing AKI).
Only test certificates/regression changed. Exact-source Windows CPython3.12.10
module qualification: 25 PASS, zero skips, 4.019s, no remaining fixture threads.
Root independently matched all1839 receipt source digests to Git blobs and
reviewed the exact diff. A8 issued a source/security-preserving fixture ACK;
A8 did not rerun TLS. Hosted CPython3.13 qualification remains pending.
The dedicated identity entrypoint retains its pinned24 tests; full unittest
discovery includes the new25th strict regression. No coverage is transferred.

Test-only Windows/Node phase instrumentation comes from source
`36e4955c0d10da0eed2184a4f626cf4c64198b37`. It preserves existing15/30s
deadlines, mandatory assertions, sanitized environment and security controls.
Nine pure diagnostic tests passed after test-first failure. It introduces no
module/command warmup. COMPILE_BEGIN still includes command resolution; it is
not evidence that the compiler started. Actual hosted timeout causes remain
UNKNOWN. These markers collect evidence; they are not a timeout repair claim.

| Required report field | Status at preparation |
| --- | --- |
| LS5_SCOPED_PILOT | Retained scoped synthetic PASS; not repeated |
| D4_TIME | Strict Option1; current-component explanation reviewed; logical mutations DISABLED |
| EXACT_SOURCE | Component pins above; no approved full native runtime assembly |
| CI_SUCCESS | Original016:21 completed SUCCESS |
| CI_FAILURE | Original016:11 completed FAILURE; originals retained |
| F26_STATUS | OPEN; no full hosted qualification |
| LAN_ROOT_CAUSE | UNKNOWN; owner's bounded serial discriminator authorized |
| WINDOWS_NATIVE_ROOT_CAUSE | UNKNOWN; original-style local member/lookup probes did not reproduce |
| AUTHORITY_ADMISSION | Logical mutation disabled; no strict positive admission |
| SCHEDULER_POSITIVE_JOB | NOT_IMPLEMENTED/NOT_RUN; PR75 is negative preparation only |
| STORAGE_COMMITTED_RECEIPT | NOT_AVAILABLE; LOCAL_UNATTESTED retained |
| TERMINAN_AUTHENTICATED_READ | NOT_IMPLEMENTED; PR81 pure preparation is not actual authorization |
| MATH_NATIVE | BLOCKED; original single-use authorization consumed, no repeat |
| A8_REVIEW | Gateway scoped source/evidence ACK; no full-system acceptance |
| PHYSICAL_CLUSTER_READINESS | Read-only preparation only; no distributed installation |
| NEXT_ACTION | Qualify exact integrated source, inspect original hosted results, diagnose remaining REDs |
| GO_NO_GO | IN_PROGRESS / NO-GO |

No production orders, provider sends, protected merge, office fault injection,
service installation, security policy or network configuration change is
performed by this package. ADMINIT remains excluded. The previous LS5 pilot
PASS is not native Scheduler/Storage/Math or six-node acceptance.
