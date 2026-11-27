# Synthetic profile review1 — bounded output and capability accounting

Additive clarification; original PROTOCOL.md raw97bc538785bc696826348928c3c26b5757fd52622d7cdbe5a74a4e62ca3bd566
and all canonical object bytes/inventory remain unchanged.

Maximum complete encoded query result is1048576 bytes, independently of total
input read budget1048576. Serialize/measure bounded local output before final
capability check; excess refuses all output, no truncation or partial row response.
Actual provider coverage/gaps remain UNKNOWN even if explicitly generated fixture
cells are locally checked; separate labels must not promote synthetic evidence.

Positive path uses exactly six ObjectStore.read calls, no verify reread or
read_manifest_object duplicate. Use decode_manifest(already_read_root_bytes).
Lineage is embedded in that root, not a seventh store object. A2 server-owned
QUERY tool budget must allow seven current checks: one before each read plus one
immediately before returning bounded output. First read check is also the entry
authorization check; no redundant check consuming an eighth use. Exact type/source/
issuer handshake is still required before accessing supplied store attributes.
Early refusal is not permission to skip checks on any later attempted read.

Each query has its own actual issued capability for its exact request/store/grant.
No caller-configurable check budget, automatic remint/retry, generic callback or
fallback to a manifest-tool capability. A4 GETmanifest retains its separate two-
check grant. Exact actual A2 source/type and A4/Root composition ACK pending.
