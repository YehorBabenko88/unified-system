# Rollback plan — preparation only

No deployment is authorized by this package. Before any future phase, bind exact old/new source, artifact and dependency hashes, owned paths/services/accounts, current generation/fences, data/checkpoint/backup roots, phase ID and owner confirmation. Missing bindings block the phase.

On failure stop only the current owned Unified operation, preserve original logs and UNKNOWN outcomes, and prevent a second effect until reconciliation. Restore only an explicitly admitted prior code version; do not roll back current authority generations or reactivate old leases. Preserve existing data and compatibility metadata. Database/Consul restore and promotion are separate fenced operations, never a directory copy or old-primary restart. Do not delete an unrecognized file/service or the last verified copy.

No rollback script may reset DNS, DHCP, gateway, routes, firewall, ESET, Tailscale, Ethernet, WLAN or router settings. Existing third-party applications and Reolink remain untouched. If normal office access degrades, halt testing and hand diagnostics to the operator; do not attempt automatic repair. Each physical recovery action needs the corresponding separately approved plan.
