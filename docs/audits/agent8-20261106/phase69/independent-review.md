# Phase69 — independent financial v2 DTO proposal review

Requirement IDs A8-HEAD, A8-DATA-INTEGRITY, A8-CONTRACT-NEGATIVE, A8-SOURCE-GUARDS, A8-WINDOWS-CI. Repository strattester, Draft https://github.com/YehorBabenko88/strattester/pull/74.
Exact executed HEAD8e1e0459a849f67eafd283080f27cb2da70ef985/tree0d9a698a5240699652166c38ae10ab831f68c3b2, basea56c24a0f25a0c5ea9222fcd953a49536c91dfc9. Four new owned proposal files plus new dedicated workflow. Schema SHA256b3d8e9f81aa19bf844c29d3c491ab4adbf3566f4e9e9d8624e5767ec87753de9. c865 is historical only.
Environment own detached no-hardlinks raw-LF clone, local Windows/Python3.12.10; committed workflow -I-S-B. Separate own previously pinned jsonschema4.25.1 environment for actual Draft202012 checks, not newly qualified native dependencies. Synthetic profiles/trades only; no real provider profile, order/network/storage/ledger mutation.

| Test | Expected | Actual | Evidence | Status | Severity / correction |
|---|---|---|---|---|---|
| Exact workflow and source |20mandatory/0skip, raw prepost equal |20PASS/0skip/779raw |workflow20.original.json; workflow20.stderr.log |PASS |synthetic component only |
| Independent high-precision Decimal oracle |gross/net explicit, signed funding once, scale0/2/18, unchanged inputs |384cases PASS at precision200; produced outputs schema-valid |extra.stdout.json; extra-executed.py |PASS |no binary64 ledger conversion or profitability claim |
| Strict code IDs and versions |ASCII codes reject LF, no v1 replay |20tests and own actual schema code-LF negatives PASS |workflow20.stderr.log; extra.stdout.json |PASS |IDs do not grant URL/path authority; profile membership caller-supplied not authenticated |
| Canonical monetary and pin schema |reject trailing LF |all9fields with dollar-end regex accepted by actual Draft202012 validator |extra.stdout.json; extra-executed.py |FAIL |P2 A8-F18: strict-end remaining5money/4pins and actual-validator negatives |
| Pure adapter LF refusal |reject malformed money and pins |adapter rejects; schema issue is not runtime bypass |extra.stdout.json |PASS |no endpoint/full-mapping ACK |
| Four own source negatives |refuse cache/shadow/tracked/replace before tests |4rejected before0tests |guard-controls.json; guard-*.stderr.log |PASS |no globalF16/F17/environment authenticity closure |
| Hosted Windows/Ubuntu |terminal mandatory jobs/artifacts |42368971093/42368968128 attempt1queued/null |ci.original.json |BLOCKED |P1 acceptance gate, obtain terminal CI |
| Actual profile/endpoint/C3 mapping/native |explicit independent admission |absent, proposal only |PROTOCOL at exact source |BLOCKED |owners must supply references/admission, not infer from schema |

A8-F18 reproducible issue handed to A7 and Root before publication; A8 did not edit production implementation. Full canonical schema ACK withheld. Open6P1/4P2 after this new issue. Overall NO-GO; physical and Tailscale removal BLOCKED.
