# Phase67 — independent installer archive namespace review

Requirement IDs: A8-HEAD, A8-ARCHIVE-NEGATIVE, A8-EVIDENCE, A8-WINDOWS-CI.
Repository unified-system; Draft PR https://github.com/YehorBabenko88/unified-system/pull/26.
Executed source HEAD fe0f5234a1c5eeeca02b2dad3ddfa948ef6c51cf, tree e48e42630f3c709292d6832a40ad8fe0a41f30fa.
Current observed PR HEAD2590cdad71a777029a616c36c0449624d498ea66; builder, test and workflow raw bytes identical, later changes documentary. No full current-HEAD matrix execution is inferred.

Environment: isolated own detached no-hardlinks raw-LF source clone on local Windows, Python3.12.10; new temporary output per inert archive. No installer invocation, ACL modification, service, office probe, provider or host network change.

| Test | Expected | Actual | Evidence | Status | Severity / correction |
|---|---|---|---|---|---|
| Source/tree/raw closure | pinned source and unchanged files |1292 raw files before/after exact |local-review.json; workflow10.original.json |PASS | bounded component only |
| Actual committed workflow |4 mandatory tests/0skip |4PASS/0skip |workflow10.stderr.log |PASS | log basename historical harness naming, actual4 |
| Independent archive negatives |reject all before output creation |5cases: parent case/nested case/file-parent/reversed/explicit-dir alias |extra.stdout.json; extra-executed.py |PASS | none for checked cases |
| Primary-parent regression |reproduce original implicit-parent alias acceptance |two inert files accepted under case-aliased parent |extra.stdout.json |PASS | corrected at source pin |
| Current PR pin preservation |same source/test/workflow bytes |3components raw identical at2590 |current-head-component-preservation.json |PASS | full current HEAD execution NOT_RUN |
| Original owner evidence index |all6selected bytes/hash retrievable |6verified at49290143; original logs retained |owner-evidence-index.original.json; owner-* |PASS | owner33 includes1skip; not A8 execution or waiver |
| Hosted Windows/Ubuntu |terminal mandatory jobs/artifacts |source-pin workflow API returned zero runs |ci.original.json |BLOCKED |P1 gate, obtain exact-head hosted evidence |
| Broader33/native/install/rollback |separate execution/admission |not independently run here |local-review.json |NOT_RUN |existing native/ACL/manifest/rollback gates remain |

Workflow receipt guards do not establish universal environment authenticity: this workflow uses site-enabled -I-B, inherits Git environment and does not independently recompute each Git object OID or validate all hardlinks. No global F16/F17 closure is claimed. Scoped primary raw equality and inert tests are the actual evidence.

Overall NO-GO; Tailscale removal BLOCKED/NO-GO. Existing6P1/3P2 unchanged; archive correction adds no install authority. Root LAN MUX causal race notice is retained as owner-reported pending independent exact fix review, not yet A8 reproduced. A7 Strattester74 financial DTO proposal is queued for separate review and receives no runtime ACK here.
