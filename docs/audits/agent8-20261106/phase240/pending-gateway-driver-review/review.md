# Independent source review — allocation not accepted

Requirement: A8-GATEWAY-DRIVER-LIFECYCLE. Repository: strattester. Proposed source HEAD0c4f64c897aacd78bbec0e1faa886c7003c353ff/tree064ed4b7661fce976f0fd97b236e85d2ebfff7f0, parent889d787. No new PR/push verified. Environment: source only; no project execution.

Driver SHA2561e6e250ad40a934681ddf80d1f2eac5d389eac3c537f392dfa7be37d36e37a2d independently hashed and full source read.

1. FAIL, proposed-runner correction required: lines129–131 combine poll and kill in one try. A held handle with raising poll skips kill entirely, then timed wait may leave live child. Sticky errors avoid false PASS but do not independently attempt retirement. Required: separate observation, kill on unknown/live, wait and independent sticky errors. Static reproducer is raising poll with otherwise working kill/wait; no owner function executed.
2. FAIL, observed budget correction required: lines122–124 permit successful exit after15s when final poll reports completion. Required: reject recorded elapsed>=15 regardless of final exit. This is an observed-limit check, not a hard OS scheduling guarantee.

Both findings sent to A7 and Integration Owner. No actual process leak, timing violation or application defect inferred. Complete source816/runtime841 maps not independently accepted by this narrow review. Existing root-first helper ordering ACK and prior hosted47 PASS retain their original scopes. Overall NO-GO; physical/Tailscale BLOCKED.

## Source correction readback

Updated driver SHA25653393538619bb59748344a8bca83177d3c66cea916f6b95f98d2e3e6a32f1060; receipt8b8d2df53cb2014baa0635636410aab7ddd6142fdf399b91e8573695d00157ed and exact diff84b865d53a7c98d9bcafa3e4b64bdbbe98c23fc8d480f4ea600361151471412f independently hashed and diff read. Both findings CLOSED SOURCE ONLY: unknown poll preserves needs_retirementTrue and independent kill/wait attempts, each failure sticky; observed elapsed>=15 refusal independent of final exit, with fallback measurement if monitor errors. No negative controls or owner execution performed. Complete driver/source/runtime acceptance and separate execution allocation remain pending. Original findings retained above as historical.
