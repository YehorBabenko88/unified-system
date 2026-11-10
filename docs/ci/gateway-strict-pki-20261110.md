# CPython 3.13 Gateway identity fixture investigation

Exact baseline: `01630597fb418d5a76a93c8b09750683dfe49b94`.
Branch: `feature/gateway-strict-pki-fixture-20261110`.
Ownership: test fixture/regression only. `unified_system/gateway_identity.py`
remains unchanged. No verification flags are removed and no guard is bypassed.

## Original evidence

Root's original failure matrix identifies eight CPython3.13 jobs across Ubuntu
and Windows, each with sixteen GatewayIdentity authentication denials. Example:
run42732716713 / job129554444542 / attempt1, artifact13748216340.
Original artifact SHA256:
`ea498fc5eeda0d5cf9bdd579f2c4bd84f335b1a76415ace36110dd818be99abb`.
Its `_temp/actual-six-source-suite/unittest.log` SHA256:
`711dbea1ad0fda9ff0ff8412fd90927a3b238521c2059c850dc9fda2cf90dd01`.

The original traceback reaches test line140 -> permit line130 -> production
authenticate_connection line221, ending in GATEWAY_READ_DENIED. It does not
expose the inner TLS validation reason. Originals remain at Root's
`pr69-01630597-original-red-20261110` evidence directory; an unchanged selected
unittest log and matrix subset are retained in the separate investigation
evidence directory. No original run is retried or replaced.

## Confirmed fixture strict-verification defect

The fixture CA currently has critical BasicConstraints but no KeyUsage/SKI.
Leaves have SAN/EKU but no AKI. TLSFixture catches a client SSLError and stores
an exception as the server outcome; authenticate_connection correctly rejects
anything other than a verified live server SSLSocket.

Python documents that create_default_context adds VERIFY_X509_STRICT and
VERIFY_X509_PARTIAL_CHAIN starting in3.13:
[Python3.13 SSL documentation](https://docs.python.org/3.13/library/ssl.html#create-default-context).
OpenSSL3.0 documents strict requirements including explicit CA KeyUsage, CA SKI
and non-self-signed v3 certificate AKI:
[OpenSSL verification options](https://docs.openssl.org/3.0/man1/openssl-verification-options/).
The assigned actual loopback regression confirmed the old fixture fails STRICT
on CPython3.12.10/OpenSSL3.0.16 with SSLCertVerificationError verify_code85,
Missing Authority Key Identifier. The non-strict existing positive case passed
in that same selected process. Original hosted logs mask their inner SSL error;
the fixture defect reproduces the documented3.13 default change, while an actual
CPython3.13 rerun remains unperformed.

## Prepared serial-lane regression

`StrictTLSFixtureTests.test_generated_chain_handshakes_with_explicit_strict_verification`
enables STRICT by OR on both existing fixture contexts, preserving every other
flag, CERT_REQUIRED and hostname checking. Its failure diagnostic reports only
exception type, verify_code and verify_message. Synthetic private keys are not
printed. This should reproduce strict behavior on existing CPython3.12, without
installing3.13 or changing production policy.

After Root assigns the TLS lane and supplies an approved cryptography environment:

```text
<approved-python> -I -B -c "import sys,unittest;sys.path.insert(0,'.');sys.path.insert(0,'tests');s=unittest.defaultTestLoader.loadTestsFromName('test_gateway_identity.StrictTLSFixtureTests');r=unittest.TextTestRunner(verbosity=2).run(s);sys.exit(not r.wasSuccessful())"
```

Run from the isolated worktree. Capture original RED output before changing any
certificate extensions. If confirmed, add proper RFC5280 fixture extensions;
never disable STRICT, PARTIAL_CHAIN, certificate validation or hostname checks.
Then retain GREEN for the strict case and all existing positive/negative gateway
cases. Runtime source changes require separate Root approval and actual RCA.

## Qualified serial-lane results and dependency origin

Root supplied the existing read-only site directory:
`C:/Users/LS-5/Documents/Codex/2026-11-06/codex-agent-8-independent-security-ci/work/identity-a8-env/Lib/site-packages`.
The actual base interpreter was
`C:/Users/LS-5/AppData/Local/Python/pythoncore-3.12-64/python.exe -I -S -B`,
with only that qualified dependency directory, this worktree and its tests
explicitly added to sys.path. Cryptography46.0.3 matches the original CI lock;
OpenSSL is3.0.16. No installation, site mutation or venv redirector was used.
There is no installed3.13; local3.14/3.15 were not used for fixture qualification.

Actual RED: old certificate generation, existing non-strict positive control PASS,
explicit STRICT case FAIL with verify_code85/Missing Authority Key Identifier;
2cases/0.198s. Ephemeral fixture fix then adds critical KeyUsage, noncritical SKI
and issuer-derived AKI to the CA/leaves. It does not alter runtime source, trust
mode, hostname checks, certificate requirements, default flags, CA scope or EKU.

Actual GREEN: all25 unique Gateway module tests PASS, zero skips,3.734s. Negative
untrusted CA, missing client certificate, wrong EKU/SAN, revoked/closed session,
forged/foreign capabilities and bounds remain covered. A55-second own-process
watchdog bounded both selected runs; all accept threads joined and the process
returned. Source raw SHA256 before/after each run matched. Lane RETIRED after the
full module; no further socket/TLS/native fixture may run without a new Root lane.

Initial native checkout used CRLF for the unchanged runtime module. Its raw
working-tree SHA differs from the Git LF blob, but LF-normalized content and
Git diff establish no production edit. The exact tested raw identities are
retained in receipts. Final commit/fresh LF primary-byte verification is separate
and must not be inferred from that initial checkout. A further serial-lane run
on the exact committed LF clone requires Root assignment.

Evidence directory: `C:/Users/LS-5/.codex/gateway-strict-pki-evidence-20261110`.
Original RED, source/dependency metadata and all selected receipts remain there.
No office/provider, truststore/policy, installation, protected Math or native
Windows service operation was performed. These synthetic loopback tests do not
grant runtime/physical deployment admission.
