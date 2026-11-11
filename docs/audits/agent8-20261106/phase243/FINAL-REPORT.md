# MCI186 publication and terminal CI evidence

Exactly ONE push of d6b72b66ff1b85b7e6b956568342ad6bd8bfcfbe and ONE NEW Draft:
https://github.com/YehorBabenko88/bybit-cluster-grid/pull/283
Tree066bbe51900e88dd53541baf29a777037ed10b5b; base unchanged PR281 headfb177d14b1e6e399bd9b66ae7cb35d3838acbd81,
branch feature/agent2-strict-utc-countermodel-20261110. Seven ADD-only files.
Remote Draft body UTF8 SHA matches approved5b50bda8... . No force, retry, extra
push, retarget, merge, manual dispatch, agent cancellation or workflow/security skip.

Fresh pre-mutation gates and API records retained. Remote merge-source commit
71c4d0e4f72d1d09899d251f70c873f1d9906c56 has parentsfb177+d6b72 and the SAME
tree066bbe, independently observed through Git data API. Do not relabel that merge
SHA as head SHA. The actual bundle artifact name correctly references merge SHA.

## Terminal outcomes

All7 PR workflows/all15 matrix cells are terminal, attempt1:
12 success,2 failure,1 cancelled. Windows bundle, both portable SDK cells, both
Mission3 Windows shells, provenance3, history3 and readonly-gateway passed.
Preflight3.11 and Mission3linux full pytest failed at collection; preflight3.12
is CANCELLED and remains visible. No rerun or recovery attempt was made.

| Run | Workflow | Terminal outcome |
| --- | --- | --- |
|43052196836|readonly-gateway|success1|
|43052197019|preflight|failure1/cancelled1|
|43052196793|windows-bundle|success1|
|43052196867|portable SDK|success2|
|43052196579|Mission3|failure Linux1/success Windows2|
|43052196586|provenance|success3|
|43052196664|history|success3|

Additionally automatic push record43052161163 is terminal failure with ZERO jobs
and ZERO check-runs, for unchanged agent2-unqualified-worker-contract.yml. Thus
the0 push JOB CELL forecast is correct, not a0 run-record claim. Original API
responses retained; no original annotation diagnosis returned. Cause remains
UNKNOWN; unquoted YAML scalar source candidate is only a candidate, not an
established platform parser cause. No file was edited to bypass it.

## Original evidence retained

All15 complete job logs are preserved as *-LOG-API.json plus ORIGINAL-UTF8.log,
reconstituting the API's exact decoded UTF8 content without newline normalization.
Failure log hashes match independently retained A8 copies:
preflight3.11 8f92d51c29b0d3caa3d10453889beccce327ee439222e4b160d4f4cfbb120b00;
Mission3linux e11974e36cbcb65cf80e32e7fde4f3074c21b2ebd33e86ad903df008b93a17aa.
Earlier DECODED-ORIGINAL.log text derivatives are retained but are NOT primary
original-byte copies. Complete raw artifact API metadata and digests retained.
All11 original artifact ZIPs physically downloaded and SHA256-matched against
their GitHub API digest, including87.8MB Windows bundle; no artifact code executed
or installed. ARTIFACT-ORIGINAL-BYTES-PROOF.json lists exact file/digest bindings.

## Failure classification and separate correction gate

Full pytest collection reported7 errors: native_snapshot_consul_lab,
test_native_profile_v2, jsonschema and unified_system imports in coordination
tests. Full62 HOSTED execution is NOT qualified by those interrupted suites.
Separate Root actual offline62 PASS remains valid only for its frozen module scope.
No new planner defect is inferred from these collection errors.

Readonly trace proves14 relevant workflow/dependency/helper/test Git blobs are
identical in basefb177 and headd6b72. No actual baseline run was performed; source
identity is not reproduced baseline causality. Concrete SOURCE correction proposal
and newly reachable effects are in COLLECTION-CORRECTION-SOURCE-PROPOSAL.md.
Do not blindly install jsonschema/unified_system or append helper paths: this can
enable actual3-voter Consul/proxy/broker/OS-lock/native fixture effects previously
blocked by collection. Owner exact support pins/locks/entry and Root effects lease
are required before fixes; no skip/deselection/import-catch pass is proposed.

GLOBAL dynamic transitive provider closure remains UNKNOWN, not safety PASS and
not an invented actual send. No Bybit/timeprobe/credential/order/production/office
operation was authorized or performed by Agent3. Source contract ACKs/offline PASS
do not admit actual senders, quotas, authority, runtime or pipeline. No physical
computer/ESET/firewall/Tailscale/route/database changes. PR remains Draft.

P0: no new concrete planner finding. P1: CI collection readiness unresolved, exact
effectful dependency/import repair not authorized. P2: separate zero-job workflow
configuration failure cause remains unconfirmed. No mandatory tests were disabled.
SCOPED OFFLINE62 PASS; HOSTED CI NOT GREEN; MERGE/RUNTIME/PROVIDER NO-GO.
