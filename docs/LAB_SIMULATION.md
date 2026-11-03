# Personal lab deployment

The owner selects LAB_SIMULATION as the primary mode. It admits verified unsigned
own components without public Authenticode trust. TRUSTED_RELEASE is separate
and remains BLOCKED_NO_TRUSTED_PUBLISHER; no automatic fallback, fake publisher
pin, generated release certificate or security-policy bypass is supported.

## Admission and execution

1. Prepare a fresh immutable capsule on the control machine. Its canonical
   `lab-release.json` uses `unified.lab-release.v1` and binds six exact repository
   commits/trees, module versions/dependencies, versioned dependency lock files,
   runtime configuration, ten unique USDT symbols, every file SHA256/size and every
   directory (including intentionally empty Git metadata directories). Runtime
   DLLs, standard library, installed dependencies and native tools belong to
   this complete file inventory, not merely their launch executables.
2. Independently admit the manifest SHA256 over the existing authenticated
   management channel. Computing a digest from a received manifest cannot admit
   that same manifest. No certificate field or placeholder publisher is used.
3. Use `unified_system.lab_release` with explicit `--mode LAB_SIMULATION --root
   ABSOLUTE_ROOT --manifest-sha256 ADMITTED_DIGEST` to verify, or add `--stage-to
   NEW_ABSOLUTE_DIRECTORY` to copy into a new inactive directory. Never overwrite
   or delete an existing release. Unknown files/directories, active `.env`, path
   aliases through links, hardlinks, changed bytes and ambiguous JSON reject.
4. The deployment bootstrap and its entire interpreter closure must already be
   independently pinned. Run `package_preflight.py` using absolute admitted
   Python with `-I -S -B`, plus existing `--source-root`, `--source-head`,
   `--source-tree`, `--source-guard-sha256`, `--git-executable`, `--git-sha256` and
   an external mutable `--cache-root`. Add `--operation lab --lab-root CAPSULE
   --lab-manifest-sha256 ADMITTED_DIGEST`. The raw script itself must be checked
   against its external hash before invoking it, as for the other preflight modes.
   It verifies bootstrap source bytes before importing lab code. A default run
   prepares only; explicit `--execute-lab` starts the lab supervisor.
5. Source fences check all six repository origins, raw tracked bytes and exact
   HEAD/tree before launch and each restart. The admitted runtime configuration
   must bind this actual hostname and use the builtin Unified profile plus five
   reviewed component entrypoints. Python uses isolated `owned_python.py`;
   Node uses Math's fixed source entrypoint. No arbitrary shell/eval/loader path.
6. Mutable journals, databases, caches and snapshots stay in a dedicated external
   lab state directory. Grid's DSN must address a loopback `unified_lab_*` user and
   database in a separately provisioned test cluster, never an existing database.
   Capsule admission alone does not prove ownership of a database server.
7. Children receive a minimal OS environment, contained component paths, public
   Bybit endpoints and `PAPER_ONLY`/trading-disabled flags. Exchange credentials,
   startup injection settings, private Bybit endpoints and inherited production
   ProgramData/ProgramFiles are not admitted. A fresh private Grid authentication
   token is generated in memory; it is not an exchange credential or manifest field.

Hash admission authorizes reviewed own lab bytes; it is not hostile-code
containment or host attestation. Existing TLS, SSH host keys, ESET, Firewall,
WDAC and ExecutionPolicy remain enabled. Grid retains scheduling/lease/fencing
ownership. Successful module health does not qualify ten-instrument paper/HA.

## Management and acceptance

Owner's latest ruling removes ADMINIT entirely. Route: LS5 -> PC1, PC2, PC3,
PC4, LS7. No office-to-ADMINIT connection or ADMINIT runtime is required.
Foreground lab execution requires no service installation. Persistent Windows
services still need a real elevated owner session on LS5; do not bypass UAC or
Restricted/AllSigned script policies. Existing services and data are preserved.

The runtime admission code does not itself install services, provision databases,
implement a fleet rollout or qualify backup/failover/update/rollback. Those must
be executed against isolated lab state with retained evidence. Full acceptance
remains NO-GO until exact-head CI, six actual office nodes, historical research
with complete costs, ten-instrument live/paper, Terminan and recovery gates pass.
