# Office network safety

Scope: LS5 controls PC1, PC2, PC3, PC4 and LS7. ADMINIT is excluded.
This extends MASTER MISSION; it does not authorize physical installation.

## Boundaries

Ordinary application code must run without administrator or Network
Configuration Operators membership, privileged impersonation, or an elevated
broker command channel. Current protected service code uses LocalService plus
an exact service SID; this is not yet the requested separate account for every
component. Migration to dedicated virtual service identities requires changes
to the token verifier, SCM identity and ACL admission together, and hosted
native tests before any office change. Merely removing Backup/Restore
privileges does not prove absence of network administration rights.

The installer/update broker receives only closed, owned installation actions.
No network reconfiguration action is admitted. DNS, DHCP, gateway, routes,
adapter configuration, Tailscale, firewall, ESET and router changes require a
separate owner-authorized maintenance workflow outside ordinary deployment.
Do not add an unrestricted shell or arbitrary privileged command parameter.

## Observation and deployment gate

A separate read-only PowerShell probe collects timestamps, actual computer
identity, adapters, IP/DHCP, DNS, routes, firewall state and selected service
state. Fixed public DNS/TCP443/HTTPS/Bybit time GET probes have bounded waits,
normal TLS verification, no credentials, redirects or exchange order calls.
The LS5 transport uses existing strict SSH host keys, bounded process output
and an independent process deadline. Evidence uses immutable files and SHA256.

Before a deployment phase, record a successful baseline on that host. Before
each next owned effect and after the phase, compare configuration and fresh
reachability. Missing/old/wrong-host evidence, configuration change or
connectivity degradation stops that deployment operation. Do not attempt
network repair, restart network services, kill unrelated processes, or roll
back host networking. Network observations can change independently of Unified;
the guard detects change and never attributes its cause by itself.

## Evidence and negative tests

Pure tests must reject administrator/operator tokens, elevated/impersonating
contexts, forbidden broker actions and stale/mismatched observations. These are
policy tests, not native proof. Disposable Windows hosted negative tests must
read actual token membership and attempt only denied handle acquisition on
network resources, never apply a configuration mutation. Office negative tests
must remain read-only until an explicit safe per-host plan is approved.

The prior outage investigation correlates available Codex command transcripts,
Unified logs and Windows network/service events around a user-supplied time
window. Preserve missing evidence and clock uncertainty. No root cause is
established without corroborating logs.

References:
- https://learn.microsoft.com/windows-server/identity/ad-ds/manage/understand-service-accounts
- https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/manage/understand-security-groups
- https://learn.microsoft.com/en-us/windows/client-management/mdm/policy-csp-admx-networkconnections
