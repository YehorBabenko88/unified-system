# Original visual CI exit31 investigation

**Targeted blocker resolved at current PR69 pin; no new source edit required.**

Original [run41669714074](https://github.com/YehorBabenko88/Terminan/actions/runs/41669714074), attempt1: source `e05004fa366971cbada0d24deed275a9ab583d7d`, tree `35112be1e03fb662d4cd0ab609053eb52b90e694`. Ubuntu job126035459050 and Windows job126035459806 both emit wrapper exit31. All3 DPR projects on each OS fail `visual.spec.cjs:40`:7 expected monitor buttons,0 found. Raw original logs and zipped artifacts13249020303/13247593485 retained; ZIPdigests match GitHub. Original upload omitted hidden `.last-run.json`; available manifest entries match, but original artifact completeness is not asserted.

The original synthetic lifecycle producer emits forbidden legacy node fields and an unknown top-level field. It is rejected by the strict infrastructure adapter, correctly yielding unavailable/empty nodes. Exact original producer reproduced `LEGACY_NODE_INVALID`; current producer produces7 nodes with `AVAILABLE_UNVERIFIED/SOURCE_UNATTESTED`. The actual validator bytes are unchanged. This is an input contract bug, not evidence to relax the validator or change7 to0.

Existing fix `cbf7ce65446561bd1caf10b8d4d17efa223a3dbc` corrects the generator and adds a contract test executing the real generator. It is already an ancestor of approved PR68. Later `0cbef0341df324f65b37de0813cdc619fbafcfa8` fixes retained canvas readiness. PR69 does not modify those producer/runner/validator/spec files; it inherits their fixes. Its own three small sync browser tests were not used as proof for the original full visual suite.

Fresh [hosted run42248777161](https://github.com/YehorBabenko88/Terminan/actions/runs/42248777161), attempt1, verifies HEAD `42686cd8fafcefaed3c5df5adaee5173d27543fd` / tree `81c684c85bda2b64dc9a327d3667f56eeb8defc1`. Windows job127997924142 and Ubuntu job127997924653 succeeded. Both exact-head original visual artifacts were downloaded within bounds:13526868216(15.5MB) and13526087491(19.9MB). Each ZIPdigest, HEAD/tree/invocation, all130 manifest members,3passed/0skipped projects,108matrix cases and114 PNGs validated using the actual producer validators. Local full unfiltered visual runner also exits0 with108/114 at this same HEAD. No green transfer from old166b was used.

No filtering, skips, assertion/count weakening, source-guard changes, product edits or office operations. No edit-scope request is needed because the targeted current defect is not present. More recent de89c9b failures at unittest setup are separate from this original exit31 and are not conflated here.

Evidence: VISUAL-EXIT31-INVESTIGATION.json, visual-exit31-original/ rawlogs/zips/producers, visual-current-hosted42686/ receipts/zips and visual-current42686/ full local evidence.

Status: **HOSTED_SYNTHETIC_VISUAL_QA_PASS_AT_EXACT_CURRENT_HEAD**. This does not establish real Control API/RBAC/HA/six-node or physical acceptance. Overall **NO-GO** remains.
