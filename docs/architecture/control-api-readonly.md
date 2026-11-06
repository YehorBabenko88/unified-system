# Control API P0 denial boundary

`ControlAPIReadOnlyApp()` is a pure, no-argument WSGI application. It creates no
listener, reads no request body, clock, files, environment or network, and has no
provider/backend injection or enable switch. It does not authenticate an operator
or implement distributed consensus. Startup and shared service wiring are excluded.

Approved component base: `2df6f5c2f77f4d883bad1a8623dd8375db529be0`, tree
`f10c13d2dd8a2a88fd7db9a4cf0d0e7a1cd6d0d4`. Ownership revision 3 is pinned at
`57e8f7524912b52ebbb639bd6d5d4fd5e2961622`, ownership SHA256
`22150f804b1b3a0d6e2047887585b1b550d189bb410fbc894ef566c553594ebe`.

This slice implements the immutable P0 profile SHA256
`e4b7f009e6f81cc5baa46be604abde8edd05cc6f48dfb5ac711879343c49d20c`.
Its explicit error shape differs from the earlier proposed Control API spec
`42057e45cc5a2d104fca7d59e39fd3b2ee568d9b08ee21aa6985c074987b60a8`.
Agent 6's scoped profile/version-separation design ACK is not runtime compatibility.

| Route | Method | P0 result |
| --- | --- | --- |
| `/control/v1/capabilities` | GET | 200; constant DENY_ONLY profile, all runtime capabilities false |
| `/control/v1/snapshot`, `/control/v1/events` | GET | 503 AUTHENTICATION_UNAVAILABLE |
| `/control/v1/datasets/{id}/snapshot`, `/control/v1/datasets/{id}/events` | GET | 503 AUTHENTICATION_UNAVAILABLE |
| `/control/v1/commands/{uuid}` | GET | 503 AUTHENTICATION_UNAVAILABLE |
| `/control/v1/commands`, `/control/v1/confirmations` | POST | 503 SAFETY_GATE_CLOSED |
| `/control/v1/sessions`, `/control/v1/reauth` | POST | 503 AUTHENTICATION_UNAVAILABLE |
| `/control/v1/sessions/current` | DELETE | 503 AUTHENTICATION_UNAVAILABLE |

Wrong methods return 405 with `Allow`; unknown paths return 404. Malformed paths,
nonempty queries, transfer encoding and any nonzero/malformed body length return
400 without reading `wsgi.input`. This includes small bodies; no route consumes
JSON or implements cursor/barrier query semantics in P0. Input bodies are never
buffered, so excessive advertised lengths cannot allocate memory. Paths are bounded
to 2048 characters, responses to small constant JSON below 4096 bytes.
HEAD retains denial status and representation headers but never emits a response body.

Errors have exactly `schema`, `code`, `retryable`, `request_id`. Schema is
`unified.control-error.p0.v1`; retryable is false and request_id is null. No UUID,
identity or authority evidence is fabricated to fit a consumer schema. Responses
use no-store/nosniff headers and never echo request secrets, paths or query values.

This profile is intentionally incompatible with frozen Terminan Sync v1 error and
event schemas. No transport adapter is installed. A client may display local
UNAVAILABLE on 503/unsupported schema; it cannot interpret denial as NO_QUORUM,
authenticated session expiry, empty snapshot, receipt or valid cursor. A bare
command UUID cannot select a future wire-v2 receipt without resolving its original
generation/actor/operation/request binding; this implementation performs no lookup.

Both strict-time and closure/eligibility/allocation gates remain closed for every
mutation, including adoption, completion and release. Egress dispatch containment
remains unproven. This app supplies no read barrier, retention, freshness, RBAC,
Windows SSPI provider or endpoint availability evidence. Future read-success
profiles require exact source-owned immutable projections and versioned consumer
ACKs; timestamps, fixture providers and node certificates cannot unlock them.

Run `python -m unittest discover -s tests -p test_control_api_readonly.py -v`.
Tests exercise real WSGI responses and negative inputs without starting a service.
The dedicated Linux/Windows matrix qualifies only this P0 component; it is not
physical HA, Windows identity, real Control API integration or production acceptance.
