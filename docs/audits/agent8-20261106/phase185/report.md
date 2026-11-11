# Offline signature tool: independent preexecution review

| Requirement ID | Repository | PR | Exact HEAD | Test name | Environment | Expected result | Actual result | Evidence link | Status | Severity | Required correction |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A8-SIGNATURE-PROPOSAL | Grid / Unified support | — | Proposal cd8b5ac148f5f18a09a588211621050d95ebdd3053f73fc2458ccd00037ebc4b | Sealed proposal source review | A8 offline data only | Preserve restrictive boundaries | Scope separates retained inputs, tool identity, signer policy, family lifecycle and actual crypto result | [proposal](PROPOSAL.md),[verification](verification.json) | PASS scoped design boundaries | — | No execution approval inferred |
| A8-GPG-LOCAL-IDENTITY | Same | — | Metadata d2ddd1295a1dfeb4ed1d1536f92b360cea8e3b0a939bf5d7a9eb76b2769fefe1 | Rehash existing gpg/gpgv+13 DLL files | Read-only local files | Exact ordinary singlelink bytes | All15 match recorded SHA256/size, ordinary singlelink/no reparse; ancestors no reparse | verification /TOOL-METADATA.json | PASS raw identity only | — | Package authenticity and loader closure remain unqualified |
| A8-GPG-EXECUTION | Same | — | No approved runner/parser implementation | Four conditional commands | NOT_RUN | Qualified tool origin/loader, nonprivileged family custody, bounded parser and adopted input/anchor/freshness policy | No execution approval; no actual GPG process or keyring creation | proposal /verification | BLOCKED | Acceptance blocker | Qualify exact implementation and preconditions before any process |

The proposal correctly preserves original partial/FAILED and429 metadata, uses one signature rather than claiming two independent attestations, and does not treat key text, exit0 or GOODSIG as publisher proof. Existing local executable/DLL hashes establish identity only. A8 did not independently qualify PE import graph, runtime LoadLibrary dispatch, package authenticity, current signer expiry or absence of newer revocation.

No approval of the exact four commands is issued. Their option semantics and closed status/colon parser remain unqualified for the actual tool version. Before any execution, freeze how status records are distinguished from colon records (the draft puts both on stdout), reject ambiguous/duplicate/unknown blocking output, and demonstrate verified applicable primary self-signature, subkey binding, revocation/expiry and adopted algorithm/time policy. `--check-sigs` output alone is not an implemented selection algorithm. Retained-key-relative validity and current global non-revocation are separate claims.

Windows family containment remains a blocker; direct-child kill, no-autostart flags and an empty home do not prove custody or network exclusion. Scratch/file budget enforcement, actual safe nonprivileged context, input admissibility and independently adopted full-fingerprint anchor require exact review. No new Job/API/key import/tool copy/install/security policy changes or execution were performed by A8. Source proposal ACK does not amend Grid Windows0spawn or authorize a GPG lane.

RELEASE_MANIFEST_STATUS: not release approval.
NODE_INVENTORY_STATUS: no new observation.
CONTRACT_STATUS: data-only /public DENY /no execution authority.
OFFLINE_TESTS: sealed source and local raw identity verification PASS scoped.
WINDOWS_CI: NOT_RUN for this proposal.
PHYSICAL_TESTS: BLOCKED.
P0_P1_P2: no new implementation defect classified; existing acceptance blockers remain.
EVIDENCE: retained proposal, metadata, seal and independent verification.json.
NEXT_ACTIONS: exact qualified tool/runner/parser/policy design; no GPG launch pending review.
GO_NO_GO: NO-GO.
TAILSCALE_REMOVAL_ACCEPTANCE: BLOCKED /NO-GO.
