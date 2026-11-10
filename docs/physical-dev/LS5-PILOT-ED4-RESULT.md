# LS5 candidate f: localized render failure

Executed source `ed4ac58066c29ba21bbe258c3e303991766baf4c`, tree
`9fa20a242d408976dec84e99e53bdf3d4f7969bb`; Terminan PR79 exact
`47530d81e8b6f297a060a206bea6f783ccd0702e`.
Manifest SHA256 `e551dcf3598a01ca4fd77f75145698762b76c53709adf5452eb3fa6a6103f3c6`;
19,263 files / 1,008,412,748 bytes. Activation plan SHA256
`e871144c7db5f28ac1815dd0582e5a5930f7f7b77c032b5638139a3309bf3b47`.
Original smoke receipt SHA256
`6586624e7b2d2e4fe0a0e6014dea6f930a274f5391b63fc8d43c85395a37343e`.

Full smoke FAIL_OR_UNCONFIRMED. Existing Strattester -> MetaAnalyse again exited
0 and created the expected synthetic 2070-byte artifact f4997d7d... LOCAL_UNATTESTED.
Terminan failed PAGE_NAVIGATE with safe diagnostic ERR_NAME_NOT_RESOLVED at
Node monotonic 12007ms (phase began 11963ms). One page request, zero route denials;
no successful DOM or screenshot. Renderer exited naturally 1; no watchdog kill.
NODE_NATURAL_IDLE was observed at12642ms; actual primary exit is separate evidence.

Work13.3193042s, cleanup0.0019551s, family13.3212593s: within20/10/30.
Own Job active0, retained primaries[0,1], package unchanged. Strict cleanup/result
is still FAILED_OR_UNCONFIRMED because the application exit was nonzero.
Issued context CLOSED, client DISCONNECTED, browser server CLOSED with observed
exit0 and HTTP CLOSED; browser cleanup confirmed51.1251ms/no expiry, guarddenied0.
35 diagnostic events/2198B, no overflow or IO failure. These actual positive
cleanup observations do not qualify every negative deadline case or full runtime.
Outer controller97.969s includes integrity/provenance work outside family timing.

## Confirmed source mismatch; correction still needs runtime proof

The fixed navigation base is numeric127.0.0.1; launch resolver rules use
`MAP * ~NOTFOUND, EXCLUDE localhost`. Exact Chromium141.0.7390.37 primary source
matches the host string against mapping/exclusion patterns before resolution;
invalid remapped URLs return ERR_NAME_NOT_RESOLVED. The numeric target is not
covered by the hostname exception. Sources:
[host mapping](https://github.com/chromium/chromium/blob/141.0.7390.37/net/base/host_mapping_rules.cc)
(blob fec058db4f7c10062355f1f2f9ef5093eb0eeb54) and
[mapped resolver](https://github.com/chromium/chromium/blob/141.0.7390.37/net/dns/mapped_host_resolver.cc)
(blob588fac6bc4f797e2ddf5dcf9d1782b66093b19a8).

This source mismatch corroborates the observed f failure; it is not attestation
of the loaded binary's source or proof of an exclusive runtime cause. The tag's
HostPortPair overload recognizes the canonical `^NOTFOUND` sentinel; the current
`~NOTFOUND` must not be assumed equivalent across resolver overloads. A6 owns a
narrow numeric-loopback exception plus canonical-sentinel correction with
external-denial regressions. No system
DNS/router/firewall/adapter setting is changed. A new GitHub source, qualification,
independent review and new immutable package/state are required before any retest.
This is not proof of the previous office-wide incident's cause, nor retrospective
proof of the earlier e generic error or every retained handle in that run.

## Qualification and limits

Exact ed4 local pure-source qualification106PASS/0skip,1711raw unchanged.
A8 phase154 FILE/SOURCE/INVOCATION_ACK at audit
`bea56d829fd1d6886e8a27ca4dc05f484d7bcb5d`, reportSHA256
`256fbde966ac2c2ac4380a30fd51620880a9112c26b5d1cfb8cf64779659133d`.
This review did not execute the package or issue owner permission. Execution was
Root's serial disposable lane under the retained owner directive961024a6....

Originals/index: `release/physical-dev/ls5-20261109/failed-f/`.
All prior candidates/original REDs retained. Public submit DENY; no native worker,
committed Storage/authenticated READ, provider sends, real orders, network/security
changes, physical multi-node admission, production, main merge or Tailscale removal.
Full CI/F26 and MASTER MISSION remain IN_PROGRESS / NO-GO.
