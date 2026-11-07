# Phase71 — financial proposal schema F18 correction independently verified

Requirement IDs A8-F18, A8-HEAD, A8-CONTRACT-NEGATIVE, A8-DATA-INTEGRITY, A8-WINDOWS-CI. Repository strattester, Draft https://github.com/YehorBabenko88/strattester/pull/74.
Exact HEAD072d22214136148b47e82d21fec9e269bd7468ac/treeffaff34af5375b23235491d92a250ccb66eb03df. Delta from8e1 modifies only owned schema, regression target and protocol notes; adapter arithmetic and shared implementation unchanged. No v2 version transfer from old candidate is inferred.
Environment own fresh detached no-hardlinks raw-LF clone, local Windows/Python3.12.10; stdlib workflow -I-S-B. Separate actual Draft202012 validator jsonschema4.25.1 from own previously pinned environment (owner used4.26; not represented as same environment). Synthetic fixture profile only.

| Test | Expected | Actual | Evidence | Status | Severity / correction |
|---|---|---|---|---|---|
| Exact source/workflow |20mandatory/0skip, source unchanged |20PASS/0skip/779fullrawGit inventory |workflow20.original.json; workflow20.stderr.log |PASS |local synthetic component only |
| Own original9trailingLF regressions |all5money+4pins refuse |9independently verified actual-validator rejections |extra.stdout.json; extra-executed.py |PASS |A8-F18 FIX_VERIFIED_OFFLINE_AT_072d |
| Committed separate actual-validator target |46checks, no skip |46PASS/0skip |actual-validator46.stdout.json; actual-validator46.stderr.log |PASS |NOT in hosted stdlib20 workflow |
| Independent arithmetic oracle rerun |gross/net/signedfunding/scales0/2/18 unchanged |384Decimal cases PASS, no input mutation, produced schema-valid outputs |extra.stdout.json |PASS |no ledger/profitability/provider claims |
| Post-validator source qualification |clean full receipt after all checks without cleanup |actual guarded20 PASS, full raw/inventory preserved |post-schema-workflow20.stderr.log |PASS |repeat20 not additive |
| Hosted Windows/Ubuntu |terminal mandatory evidence/artifacts |primary snapshot saved, no terminal PASS asserted |ci.original.json |BLOCKED |P1 acceptance gate |
| Profile/endpoint/native/physical |separate owner admission/actual references |not provided/exercised |current-acceptance-status.json |BLOCKED |full mapping/provider/native ACK withheld |

F18 was independently reproduced at8e1, reported to A7/Root and corrected by owner; original nine failures remain historical phase69 evidence. Only this proposal-schema defect is closed. Open6P1/3P2 restored. Overall NO-GO; Tailscale removal BLOCKED/NO-GO. No production edits by A8, no install/service/network settings or real order actions.
