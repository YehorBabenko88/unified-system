# LAB_SIMULATION and TRUSTED_RELEASE

The owner explicitly authorizes verified unsigned local lab deployment and paper
execution. Public Code Signing is optional for this personal lab, mandatory only
for TRUSTED_RELEASE. No implicit fallback between the two modes is permitted.

LAB_SIMULATION uses a separate canonical manifest and an independently supplied
SHA256 transported over the existing authenticated management channel. The
manifest binds all six repository commits/trees, dependency versions/locks,
every capsule file and the runtime configuration. Hashes establish admitted byte
identity, not public publisher trust or hostile-host containment. The deployment
bootstrap and its interpreter closure must themselves be pinned before use.

An immutable capsule is separate from mutable journals, databases and evidence.
Unknown files, aliases, symlinks/reparse points, hardlinks, ambiguous JSON, source
drift, missing dependencies or credentials fail closed. Before process launch,
the existing source fences verify repository bytes against the admitted commits
and trees; ProcessDriver retains its executable/file pins and authenticated health.
Only the new explicit lab entrypoint may authorize lab starts; hosted-only entry
points retain their original guards. No fabricated GITHUB_ACTIONS environment.

Lab children inherit a minimal OS environment plus pinned component settings;
exchange keys/secrets, external credentials and order-enabled configurations are
rejected. Market access is public/read-only and execution paper-only. This is
defence in depth for reviewed own components, not a sandbox for arbitrary code.
Grid remains task/lease/fencing owner. No security policy or firewall changes.

TRUSTED_RELEASE retains CMS/Authenticode, publisher SHA256, Code Signing EKU,
system trust/revocation and timestamp requirements. Without an admitted publisher
its state is BLOCKED_NO_TRUSTED_PUBLISHER, independently of lab readiness.

Owner's subsequent ruling removes ADMINIT entirely from processing, deployment
and acceptance. Deployment route is LS5 -> PC1, PC2, PC3, PC4, LS7; no ADMINIT
connection or runtime is required or attempted. Persistent LS5 services require a genuinely elevated owner session,
never an automatic elevation/policy bypass.

Acceptance remains NO-GO until exact-head required CI, real six-office-node
execution, ten-instrument history/research/live-paper, UI and
recovery/update/rollback all have retained, machine-verifiable evidence. Unit
tests, synthetic integration and short source probes do not replace those gates.
