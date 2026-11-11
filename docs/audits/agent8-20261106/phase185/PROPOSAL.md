# Isolated offline Consul signature verification: before-execution proposal

2026-11-10. Requested SOURCE/TOOL-METADATA-ONLY step. No GPG/gpgv process, version probe, import, signature verification, key creation, network, installation, native fixture or protected computation was performed. Nothing in this proposal authorizes future execution automatically. Root and A8 must approve the exact tool/runtime/runner/input plan first.

## Inputs and preserved failure evidence

Use only the immutable metadata packet sealed by SHA256 `0f184c96564016e1ddd1b6a2c7ef501a5820b707227323e74daa37bc1164cff9`. All six GETs were consumed; no further network requests or retries are authorized. Five HTTP200 files retain original FAILED/partial statuses following the post-EOF script bug; Content-Length equality and offline checksum comparisons do not rewrite them as retrieval SUCCESS. Security page HTTP429 is preserved and is not identity evidence. A8 independently reported packet/raw-byte checks in phase184; A2 has received that owner report, not independently read its report files in this step.

Fixed input paths under `C:/Users/LS-5/Documents/Codex/2026-11-06/codex-agent-2-high-availability-distributed/outputs/A2-CONSUL-METADATA-RETRIEVAL-20261110/`:

| File | Bytes | SHA256 |
|---|---:|---|
| checksums.txt.partial | 1060 | d7c5cc96ddd2bd5f55709bd27495da4d0fb9b2c5e889eed57b4f89402010ab3d |
| signature-keyid.bin.partial | 566 | db6d0a137566690dea45ff0097dbf375d3b5e7e862461a55fec7f48d072311b3 |
| signature-generic.bin.partial | 566 | db6d0a137566690dea45ff0097dbf375d3b5e7e862461a55fec7f48d072311b3 |
| publisher-key.txt.partial | 7717 | c2f5bc1163bd8d15a711616b587bcede212d045a5b8b52df01c74095897cd065 |
| key-update-bulletin.html.partial | 31866 | 0f98f38fb9eb0c55bcfe8d56af2a524d6330db9c000f34f266483faaf88faba4 |

One detached signature is enough for the proposed verification: use exact signature-keyid bytes; generic bytes are identical, NOT a second independent cryptographic attestation. Before execution, Root/A8 must explicitly decide whether the retained HTTP200 bodies with matching recorded lengths/unchanged RED receipt are admissible verification inputs. Do not silently rename, repair or refetch them.

The official bulletin retained over default TLS states primary fingerprint `C874011F0AB405110D02105534365D9472D7468F` and updated expiry March1 2030. Text is an anchor candidate requiring Root/A8 adoption; it is not a computed key fingerprint, valid self-signature or current non-revocation proof. No first-key selection, APT repository key, ambient keyring, keyserver or user-ID/email heuristic is acceptable.

## Existing fixed local tool candidates: not authenticated by their hashes

TOOL-METADATA.json SHA256 `d2ddd1295a1dfeb4ed1d1536f92b360cea8e3b0a939bf5d7a9eb76b2769fefe1` binds PE metadata, file IDs, link counts, attributes, raw hashes and static dependency graph:

| Absolute candidate | Bytes | SHA256 |
|---|---:|---|
| C:/Program Files/Git/usr/bin/gpg.exe | 1129818 | 14953ed8b4549020e185c0f7ab600bb9d0384457ea74da9d574e8d31139aff4f |
| C:/Program Files/Git/usr/bin/gpgv.exe | 513794 | e5b9f232083ac4c7427ad4923e21d26bae0c8b8554db3344ef388088f92919fe |

Both are static x64 PE images (not the small Git launcher), ordinary/single-link/no reparse. Inspected ancestor paths through C:/ have no reparse tags. Windows version resources are empty. Installed etc/package-versions.txt CLAIMS gnupg2.4.9-3, libgcrypt1.12.2-1, msys2-runtime3.6.10-1 and other versions; the file is hashed as reference only, not executable version output or authenticated package origin. No default distributed distsigkey.gpg was read/adopted. No PATH-based GPG candidate was discovered by the read-only shell lookup; this does not attest any machine-wide inventory.

Static recursive PE imports in the same installed directory identify thirteen existing ordinary/single-link/no-reparse DLLs, all hashed in the metadata: msys-assuan-9, msys-bz2-1, msys-gcrypt-20, msys-gpg-error-0, msys-2.0, msys-npth-0, msys-readline8, msys-sqlite3-0, msys-z, msys-iconv-2, msys-intl-8, msys-gcc_s-seh-1, msys-ncursesw6. This inspection did not execute SQLite or adopt it as authority. PE delay-import directories inspected are recorded; static imports do not exhaust runtime LoadLibrary/config/helper behavior. KERNEL32/ntdll/USER32 imports are recorded as SYSTEM_OR_UNRESOLVED, not loader-attested file identities.

BLOCKER: trusted origin of the installed Git/GnuPG package and exact runtime/OS loader dependency chain is unqualified. A raw SHA is identity, not authenticity. Root/A8 must adopt an independently authenticated retained installer/package manifest or explicitly review the local tool trust basis; unknown origin cannot produce publisher PASS. No new download/install/copy-of-GPG, DLL replacement, truststore/ACL/link change or version probe is approved. Need exact safe CWD/environment/loader policy and exclusion of unintended helpers; MSYS runtime may have its own configuration/dispatch behavior. Do not infer that a single PE image has no children or that --no-autostart proves containment.

## Proposed future scratch and environment contract

Only after approval: create one NEW empty ordinary directory outside all repositories and outside the user's default GnuPG home, e.g. `C:/Users/LS-5/.codex/ha-signature-verification/<approved-execution-id>/gnupg`. This directory has NOT been created. Freeze its absolute resolved path and parent safety under existing policy first; no alias/reparse/hardlink or reuse, no default ~/.gnupg, no Windows certificate truststore. All public keyring/trustdb/status/log/temp files stay within the approved new execution directory. Root owns the directory/lifecycle and must approve nonprivileged execution; no ACL/UAC/token changes are proposed.

No shell. Direct fixed approved gpg.exe argv only; gpgv is reference/alternative requiring separate exact approval, not fallback. Explicit minimal environment with GNUPGHOME pointing at the new directory and SYSTEMROOT/required already-approved runtime fields only; remove inherited GPG_*, GNUPG_*, GNUPGHOME, GPG_AGENT_INFO, DISPLAY/TTY, proxy, LD_*, MSYS/CYGWIN dispatch and dynamic-loader override variables before setting approved values. Do not rely on inherited PATH. If Windows/MSYS needs a PATH, freeze exactly the approved runtime+system directories with no project/CWD/user search entries, and review actual loader behavior before execution. Current metadata does not qualify that behavior or provide an egress barrier.

All commands share this proposed fixed argv prefix (options require Root/A8 exact-version semantics review before execution; no probe or speculative retry here):

`[GPG_ABSOLUTE, '--no-options', '--homedir', H, '--batch', '--no-tty', '--no-autostart', '--no-auto-key-retrieve', '--no-auto-key-import', '--auto-key-locate', 'clear', '--no-default-keyring', '--keyring', R, '--no-auto-check-trustdb', '--status-fd', '1']`

H is the NEW empty approved home; R is its single explicit `publisher-public.gpg` keyring path. No config-file, default keyring/trustdb import, ownertrust operation, personal/private key creation, key generation, agent/dirmngr/other helper start, online key discovery, trust override, ignore-expiry, fake-time or skip-selfsig verification. GPG may create its own empty local public keyring/trust bookkeeping during public import; those are confined execution artifacts, never personal ownertrust or global trust changes. If the exact tool requires an unreviewed helper/config/trust override, stop rather than add flags or permissions.

## Proposed minimal bounded offline command sequence (NOT RUN)

1. Prefix + `['--with-colons', '--fixed-list-mode', '--with-fingerprint', '--with-subkey-fingerprint', '--show-keys', KEY_FILE]`. Inspect ONLY the pinned public-key bytes. Machine output must show exactly the adopted primary fingerprint, with explicitly enumerated subkeys; no first-key choice or unapproved additional primary. This inspection does not alone verify selfsig/revocation. Reject secret-key material/import requests; do not print personal/default keyring contents.
2. Prefix + `['--import', KEY_FILE]`. Import only the exact public file into R/H. Require bounded expected IMPORT_OK/IMPORT_RES and exact primary fingerprint accounting; reject secret key counts and any unexpected primary. Do not import ownertrust. No keyserver, signing, certification or private key command.
3. Prefix + `['--with-colons', '--fixed-list-mode', '--with-fingerprint', '--with-subkey-fingerprint', '--check-sigs', 'C874011F0AB405110D02105534365D9472D7468F']`. Review actual key metadata and cryptographically checked applicable self-certifications/subkey bindings/revocations; Root/A8 must freeze the precise colon/status parser against the qualified GnuPG version before running. A timestamp or pub expiry field alone is not a verified current self-signature. Require valid adopted primary and signing-subkey chain, intended usages, nonexpired/nonrevoked state at recorded verification UTC, and the current valid self-signature establishing expected primary expiry date2030-03-01. Missing issuer/selfsig/binding/revocation interpretation or an unverified parser is a BLOCKER, not a best-effort PASS. No extra signatures or users trusted by email.
4. Prefix + `['--verify', SIGNATURE_KEYID_FILE, CHECKSUM_FILE]`. Signature verification ONLY over the exact retained checksum bytes, not decoded/normalized/regenerated text. Require exit0 and machine `[GNUPG:] VALIDSIG` (actual status name, no underscore). Full signing fingerprint must be the adopted primary or an explicitly verified current bound signing subkey; VALIDSIG primary-fingerprint field, where present, must exactly match the adopted primary. Check signature time/type/hash/public-key algorithms under the explicitly reviewed crypto policy; no silent acceptance of obsolete algorithms. GOODSIG/UID/exit0 by themselves are insufficient. No BADSIG, ERRSIG, NO_PUBKEY, EXPKEYSIG, EXPSIG, REVKEYSIG, KEYEXPIRED, SIGEXPIRED, KEYREVOKED, FAILURE, NODATA or unknown blocking status. Undefined personal ownertrust is not repaired: publisher identity comes from separately adopted official full fingerprint and valid key chain, never newly assigned ownertrust.

Each step is conditional on prior exact evidence; any failure stops the sequence, with no retries/fallback/version/network commands. Do not claim the generic and keyid signatures were separately verified merely because the bytes match. gpgv can check an explicitly supplied reviewed keyring offline, but does not by itself close full current selfsig/expiry/revocation/trust-anchor requirements; it is not a shortcut around steps1-3 or unqualified tool origin.

## Bounds, custody and receipts before any process

Propose at most4 sequential GPG invocations,15s per command,90s whole lane including setup/cleanup, aggregate stdout2MiB/stderr1MiB, scratch16MiB and at most64 ordinary output files. Inputs are pinned small metadata only; no archive/Consul/binary opens by GPG. Stream-enforce output/deadlines/file budget; record raw separate stdout/stderr and status boundaries without trusting text messages. Bound parsers before allocation and fail on unknown/ambiguous/multiple primary output. Preserve all failures/partial output. Recheck input/tool/DLL metadata before/after, and original archive digest/member/size evidence separately; no source edits.

BLOCKER: no qualified Windows family lifecycle/containment runner was established here. The Grid source verifier correctly remains0spawn on Windows; its restriction is not bypassed by this proposal. Before GPG launch, Root/A8 must explicitly qualify existing authorized family custody, deadline/output enforcement, no-network/helper boundary and cancellation/cleanup receipts, or approve a separately scoped design. Retain original handles from launch; clean/reap all owned descendants without PID/name scans or killing reused PIDs. Direct-child-only kill and inherited pipe hangs are inadequate. Do not introduce a Job hook, new OS API or copy another agent's privileged/private helper without separate ownership review. If custody or nonprivileged context is unsupported, reject BEFORE any GPG process.

Empty external home can be left intact as a sealed evidence artifact by Root; any cleanup must stay within verified exact approved scratch and never touch default/personal keys or installed tools. Record which files were created (public-only), that no secret key or ownertrust command was used, and actual process/handle closure. No native fixture cleanup or physical node action belongs to this lane.

## Required decision and evidence boundaries

Proposed cryptographic chain if separately approved and actually successful: adopted bulletin full fingerprint -> verified current public primary/selfsig/signing subkey -> actual VALIDSIG over exact SHA256SUMS -> unique exact Windows/Linux archive checksum entries -> separately rehashed existing archives -> streamed exact member/size/leaf matches. Current state closes only byte comparisons and metadata retention. Five RED retrieval statuses, HTTP429 and missing authenticated tool/runtime origins remain explicit.

Offline retained key/signature can establish validity relative to reviewed retained key material and recorded verification time; it cannot prove no newer revocation exists elsewhere. Root/A8 must explicitly adopt a freshness/non-revocation evidence policy or retain that axis NOT_QUALIFIED. Do not invent global current revocation proof, a trusted host clock, independently authenticated Git installer or publisher approval. D4 strict UTC at commit is a different unresolved capability and is neither tested nor weakened here.

Before execution Root/A8 must approve: RED input admissibility; exact tool+DLL origin/loader basis; full-fingerprint anchor and current-selfsig/expiry/revocation parser/policy; safe nonprivileged runtime/env/custody; exact4 commands and limits; exact new external home. No such execution approval is claimed by this document. Decision now: TOOL_METADATA_REVIEW_ONLY / SIGNATURE_NOT_VERIFIED / PUBLISHER_NOT_QUALIFIED / NATIVE_READ_FULL_FIXTURE_D4_PHYSICAL_NO_GO.
