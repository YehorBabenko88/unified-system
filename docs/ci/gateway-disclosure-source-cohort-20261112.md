# Gateway disclosure source cohort repair — SOURCE ONLY

Base: PR100 HEAD36344c18411c2ae6ff0a2928fd0ed9940d6d5c7a,
treebbd315ad7f51b0666b95a3ab424df41253e74997.
Root original run43318984089 selected147 tests on both OS;16 errors reached
support_owner.py OWNER_SOURCE_NOT_PROVISIONED. This repair changes only its
test-fixture provisioning SHA, adds pure source checks outside Gateway discovery,
and this note. No selected147 execution is performed by this repair.

| Source | Canonical LF SHA256 | Git blob OID |
| --- | --- | --- |
| unified_system/gateway_identity.py, unchanged15283B | 84093865e8477ef6562100d41137922785446c9cb4e024c9ba7105593a2b36c1 | f81ede7ddd6973a544968922c1db20c7b056a286 |
| tests/test_gateway_identity.py, current20851B | 75caec14f84e0f388d0aaff92d9617223346a8cc895e28830b32e6e1237e2f14 | 3e45a107ff924122cfdf20678b1d4a3b20afd255 |
| tests/test_gateway_identity.py, old18653B | b26fe114c778a8b8a95bc3de822dd7c7a4f57dd12277e9fdcbc96cfb5bc4199f | 72b1a05acd21f31e68616ada59cb9d03d7c3e37d |

The old pin matches the exact parent fixture before
610224abcece37d9dbdb625a73ab1be061d566be (cherry-picked71989562...).
That commit changes only tests/test_gateway_identity.py and
docs/ci/gateway-strict-pki-20261110.md. The fixture adds proper KeyUsage/SKI/AKI
certificate extensions, explicit STRICT options/diagnostics, and the25th strict
fixture regression. This is more than merely adding a test method; the complete
fixture diff was inspected. Production identity has the same blob before/after.
The existing strict-PKI note documents its earlier independently scoped RED/GREEN;
this repair does not rerun or extend that TLS evidence.

No normalization or alternate accepted pin is introduced. The loader still
requires exact raw bytes, single links, non-symlink files, the canonical imported
owner module/path and the same fixture path. Exact function source SHA256
(excluding module-level pins) is unchanged:
3d9b5fd577164a8190b5e5cb81a2996a65aff34e5733f46a99e1dccb04bd1de0.
Production authentication/authority and strict TLS guards are unchanged; this
test-provisioning change supplies no new A2 contract or runtime admission.

Pure source test command (explicit canonical-LF checkout required):
`python -I -S -B tests/ci/test_gateway_disclosure_source_cohort.py`.
The test reads bytes/AST only; it never imports owner/fixture modules or creates
PKI/TLS/listeners. It verifies the primary SHA/OIDs and unchanged loader function.
AST locates the function; its exact source bytes are hashed to avoid coupling
the guard check to Python-version-specific ast.dump formatting.
Original RED:2PASS/1FAIL, solely current fixture75ca vs stale pinb26fe. After
one-pin repair:3PASS. Logs retained in Agent4 task outputs/
gateway-source-cohort-{red,green}-20261112-r1.
Final exact-function-source digest check also passed3/3 in
gateway-source-cohort-green-20261112-r2 (0.009s).
Hosted147 runtime rerun remains
Root/A8 forecast/admission work; no PASS transfer from these source tests.

No workflow/current Root99/PR100 edits, push, SQL/native/provider/service/ACL
operations or dependency changes are included. Publication remains held pending
Root scope review and A8 forecast.
