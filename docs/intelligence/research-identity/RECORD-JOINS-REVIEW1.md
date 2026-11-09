# Exact broker record/registry joins

API549abfe7 record fields are now closed machine schemas in this directory.
Same L/profile-registry/<profileSHA> selector as research-lab review2: no duplicate
principal/profile authority or role map in local memory. Broker constructor takes
ONLY the server-selected immutable profile SHA; actual role/policy data comes
from Consul. L/native session lock and principal/policy keys are those in API1.

Profile raw canonical KV Value SHA256 must equal its key selector; profile body
contains NO own SHA. It binds cluster/realm, actual peer fingerprint -> actor UUID,
fixed input/producer and TRIAL demands. This actor profile does NOT qualify worker
limits/headroom or publication. Job issuer's global approved schema/profile
registration remains an additional target-side check; broker session is not it.

Actual cert URI service UUID and peer DER SHA must match same actual principal
row and profile registry mapping. Principal row policy ID/actor/profile/quota and
policy row ID/actor/profile must agree; ACTIVE/current native row indices and
sorted unique scope subset are mandatory. Context stores original peer, native
session and principal/policy/quota; changing those joins denies, not adoption.
Source returns current actual raw/index/session observations; mutation owner
MUST independently include all relevant profile/principal/policy/session/gen/leader
native checks in target transaction. Capture is NOT permission or a boolean proof.

Native Consul session identifier is a DISTINCT canonical lowercase UUID string,
not necessarily UUIDv4; exact real RPC/lock/session equality required. Client/job/
actor UUIDv4 rules remain strict. See separate native-session correction packet;
the old lab lease schema is not silently rewritten or treated as approved.

Machine schema is structural only. Runtime additionally enforces exact C3 bytes,
actual server CA/EKU/SAN/DER, issuer/source membership, profile raw hash, complete
cross-record identity joins, real UTC date parsing, positive revision <=u63 and
scope ordering. Regex date syntax or JSON record state is not standalone authority.
Source/identity/native session class qualification is separate from worker/job
admission. Strict UTC-at-Raft-commit remains P0. Root public submit stays DENY.
