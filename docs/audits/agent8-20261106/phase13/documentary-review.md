# Documentary checkpoint review

Requirement: exact candidate/ownership/evidence binding; no acceptance or ACK transfer.
Repository: unified-system; Draft PR26; HEADca9e390203305c8662ddf98fb771ac0bd268ec49; treedfcf0331e25da56c76a07d59bf6b84126534dff7; base80c25306a7b0230a39cf1150172844ec94452529.
Environment: independent Windows Git-object inspection; no runtime tests or physical calls.

Expected: documentary-only delta from56f4215, correct source metadata, preserved original evidence and safety gates.
Actual: app/test/workflow blobs unchanged;25documentary paths changed. revision4 SHA2415c81fb4099bad670312df1132cf398e70a11368eebf3c31d435626b349f38 matches manifest. A7platform-coverage/A2Gridfixture allocation matches reviewed scope. A8 ACK only its own audit prefix; no global/contracts/endpoint/previous-revision ACK transfer. Explicit full-feature human-design approvals remain pending A1/A3/A4.

PASS for evidence integrity only: five original stdout/stderr pairs match receipt hashes;164archived original metadata members match sizes/SHA256 and archive digest;7CIguard evidence members match index;14skips appear in original log and have null waivers. Broader composition receipt remains exit1 and is not turned into PASS by focused18case run. These are reviewed original owner evidence, not independently reexecuted tests. Current immutable HEAD has no inherited hosted acceptance.

FAIL A8-F12, P2: allocation A8 base_head6f89abed disagrees with fresh PR21 base and actual merge-base b9b03a1ce9f887dbe113fd22d0bda8932f46ef80; manifest pairs current integration branch with PR13 rather than PR26. Required correction: identify historical component pins separately, reconcile actual allocation base and bind current candidate PR/HEAD/tree; publish new documentary SHA. Repro: inspect corresponding two JSON fields and gh pr view21/26 --json baseRefOid,headRefOid. Original observations are in documentary-review.json. Passed checks do not close this metadata finding.

Six declared redacted node summaries retain NOT_VERIFIED/BLOCKED admission. Underlying owner-local raw node inventories, script/SSH identity evidence and physical observations have not been independently reacquired by A8; PC3firewall-off is a declared observation requiring owner/security review, not an independently confirmed defect or authorization to change policy. Egress snapshot explicitly does not prove Bybit routing/quota activation. PHYSICAL and TAILSCALE_REMOVAL remain BLOCKED; overall NO-GO,6P1/2P2open.

Evidence: documentary-review.json; reproducer ../review_documentary_checkpoint.py; immutable source objects in PR26 HEAD above. Report delivered to Integration Owner with reproducible corrections; no production edits.

Later bounded correction: F12 independently resolved at084ef2ec3b42131b12af44103f2d21845bf1c0f7, revision5 SHA0ef0dde1f6b238e87b60e2e21eeb13466f6b5e39c3815d91b39890134c982bdd. A8base and PR26 linkage corrected, historical pins separately labeled; all allocation paths unchanged. Fresh ACK only A8 own prefix, no global or prior ACK transfer. No tests rerun for three documentary-only paths. F13 remains OPEN pending exact fix. Current total7P1/1P2; overall NO-GO.
