# Root-owned authority source extraction

Base Root136fa5983f3496f0d873098d9044ad981ebc8c43. Source Grid295 c9ffdaa2af52c4d55871a48655a77a0c669da80f.

| Original source | RawSHA256 | Canonical Root owner |
| --- | --- | --- |
| grid/coordination.py | 3dd73d3eb3dfb576f7174a94fab05a0f87fe248ffcacccfa19786ccc74f0776b | unified_system/consul_authority.py:Config/Lease/SessionAuthority/errors and numeric control codec |
| grid/authority_runtime_v1.py | cfb32db73f1859d9d78b03d886372cc08584c81abd64930b5409a91edc417b64 | authority_codec.py:strict native canonical metadata and NativePlanMeasure/measure_native_plan |
| grid/authority_assignment_v1.py | 5b972b6d81eeaf6f2283584c5b0482552fa9bf0717a4379838900a72da791491 | research_authority.py:negative result/authority, captured records, bounded consistent snapshot and transaction subset |

No Grid import, facade, worker, market collector, PG leadership factory, environment factory, general Assignment issuance or registration custody is copied into this runtime closure. The original Grid sources remain retained evidence, not imported aliases. Root broker and native-negative fixed-type consumers use actual Root classes. Five raw source pins are recalculated from the corresponding real Python files; original hardlink/symlink/source guards remain.

Ownership-only changes: session display name grid-control becomes unified-control; AssignmentUnavailable becomes Root ResearchAuthorityUnavailable and CURRENT_GRID_LEADER_REQUIRED becomes CURRENT_AUTHORITY_LEASE_REQUIRED. Broker removes its retired missing-Grid import fallback and imports actual Root types directly. Every other broker constructor guard remains. ResearchLabAuthority uses a private Root snapshot helper with no positive execute/reconcile operations. No job/worker/resource effect permission is added.

Control canonical JSON permits numeric fencing indexes. Native metadata canonical JSON intentionally rejects numbers and enforces ASCII/depth/member/array/16KiB limits. Native plan measurement separately permits native Consul indexes and enforces64operations/32KiB encoded size; it is not a domain authorization or a CPU/RSS containment proof. These codecs are not interchangeable.

Preserved guards include lease session/index/deadline, current generation, exact same authority/client, consistent unfiltered native reads, bounded record inventory, peer/certificate/session/expiry and request/scope binding, clock poison, local invalidation before audit, native retirement best effort despite audit refusal, UNKNOWN/no-not-found/no-reexecution/no-job-permission semantics. The provenance fixture hashes38original method ASTs plus declared ownership transforms. Empty Python3.12type_params fields are the only AST-version normalization.

Reproduce only reviewed inert scope: Python -B tests/gateway_research_identity/run_root_authority_inert.py from this checkout.27tests PASS on available WindowsPython3.11 and3.12. The3.11 run reads existing pure httpx dependencies from work/release-control/.venv/Lib/site-packages through explicitPYTHONPATH; no install or shared environment mutation. Strict audit denies socket/process/ctypes events, including synthetic denial calibration. Coroutines use immediate fakes and a test-only inline wait; this tests control flow, not real deadlines or quorum.

Local cryptography is unavailable. The explicit test harness supplies import-shape stubs whose every crypto operation raises; no fake certificate validation succeeds. Source hashes and method AST preservation do not qualify certificates, ACLs, TLS, Consul quorum, native transaction/index/lock behavior or revocation at actual commit time. Existing actual Consul/mTLS/native tests are retained with canonical imports, compiled only, NOT_RUN. Native qualification remains NOT_RUN/NO_GO.

Not changed: Root collector/profile/lab_release; target adapter/target bindings still point at the historical Meta/Stratt stand and require separately versioned canonical Terminan contracts/pins/goldens. collector_offline and lab_paper_pipeline retain other legacy imports pending their own ownership migrations. This is not a full release pass.
