# Internal experimental ControlV3 executable read boundary

This is source/isolated fixture software, not the final ControlV3/multiplex ABI or
an admitted operator service. Namespace is ONLY `/control/experimental/v3/` and
profile ONLY `unified.control-read-boundary.experimental.v3`. Frozen V1/P0 schemas,
startup, native providers, Terminan and Grid mutators are unchanged.

## What runs

`ControlV3App()` is a real WSGI application with no provider/env/boolean/testing
activation arguments. It starts no listener. `GET capabilities` returns constant
false availability/native_admission and no real node/LIVE information. Missing
native bridge on protected reads returns503 AUTHENTICATION_UNAVAILABLE. No header,
REMOTE_USER, JSON principal or dictionary enables a provider. POST/DELETE parse
bounded admission identity but always503 ADMISSION_UNAVAILABLE; no slots/effects.

The reusable parser/dispatcher and `ControlReadAdapter` execute actual selector,
context, scope/view/root/counter and event framing checks. Test composition ONLY
under `tests/control_v3/fixture_server.py` runs those same functions with synthetic
providers through an actual owned127.0.0.1 ephemeral-port plain HTTP server. Positive
fixture responses carry UNTRUSTED_PROVIDER_CLAIM/native_admission=false and fixture
header; they are never native identity, real cluster data, proof or consumer
admission. Fixture server is closed/joined at test exit and no service/config is
modified. There is no listener factory or fixture selector in production app.

## Exact internal routes, framing and limits

GET `snapshot` uses canonical four-field query in exact order:
`scope=CONTROL&dataset_id=~&source_id=~&partition_id=~` or DATASET plus lowercase
UUIDv4 and bounded source/partition IDs. `~` is null; literal `null` is a non-null
ID. Dataset aggregate is source=null/partition=null; source aggregate has source;
exact partition requires source. No omitted/empty/reordered/duplicate/percent/plus
aliases; query<=512bytes. These selectors do not grant domain access.

GET `events?cursor=<base64url>` requires X-Expected-Connection-Epoch and
X-Expected-Sequence canonical positiveu63 strings plus UUIDv4 X-Stream-Attempt-ID.
This finite experimental batch is NOT a multiplex socket, durable cursor issuer,
replay registry or heartbeat authority. Every frame must match requested epoch,
current view and contiguous sequence. Whole batch validates and current identity
rechecks BEFORE response; any inner failure gives JSON503 with no partial SSE.
LIVENESS contains a bounded connection identifier only and grants no freshness.
Exact event framing is `data: `+canonicalJSON+two LF bytes; no event/id/comments.

POST `connections` accepts canonical ASCII JSON with exact schema
unified.control-open.experimental.v3, request_id, role, app_instance_id,
enrollment_revision; UUID request_id equals X-Request-ID and Idempotency-Key is
required. DELETE `connections/<uuid>` or `subscriptions/<uuid>` requires request
ID/key and positive X-Expected-Connection-Epoch, plus subscription epoch for the
latter. Parse digest binds method/path/target/expectedepochs/request/key/bodyhash.
It is NOT final authenticated idempotency identity: actual actor/session/quota owner
binding and durable registry do not exist here. No replay/admission/send is enabled.

GET/DELETE bodies are forbidden. Reject transfer encoding, terminated/ambiguous
streams, noncanonical/oversize Content-Length before reading. POST reads at most
declared16384bytes and normalizes missing/short/failed input to400. Strict
canonical JSON rejects duplicates/extra keys/version aliases/nonfinite values.
WSGI environ may already have collapsed duplicate raw headers or decoded paths;
where RAW_URI/REQUEST_URI exists it must equal exact request target. Absence does
not prove raw safety. Future production front MUST enforce raw HTTP framing,
mTLS/native identity and request deadlines; WSGI alone cannot certify them.

Snapshot response<=65536bytes, finite batch<=131072bytes, eventJSON<=32768bytes,
<=32events,<=100resources, depth<=8, members<=48, string<=16384 and aggregate
validation<=4096nodes with encoded-size budget before serialization. Repeated-
reference provider objects cannot cause exponential unbounded traversal. Integer
resource data is bounded; revisions/epochs remain checked decimal strings.
These are INTERNAL test bounds, not adopted final mux2MiB/128KiB limits or measured
RSS/native containment guarantees. Responses are no-store/nosniff, bounded errors
have no traceback, and HEAD carries metadata with no body.

## Typed future dependency, still unqualified

`identity.resolve(parsed_request)->ReadContext|None` must eventually be supplied
by ROOT's admitted local-Windows-account bridge. Context has actor_id, opaque
session_id, view_id and authorization_revision. None/malformed denies401;
unavailable/throwing bridge503. No external IdP is required or implemented.

`authority.snapshot(context,selector)` and `authority.events(context,request)`
must eventually bind real Grid consistent reads, authorized projection/root/view,
schema and cursor provenance. Current adapter checks detached bounded claims,
then resolves current identity AGAIN and requires exact same context before any
disclosure. Missing/throwing/malformed read provider503 AUTHORITY_UNAVAILABLE.
No unqualified timeout becomes global NO_QUORUM. A dataclass/callback/boolean
does not prove native authority. A returned root hash is syntax, not cryptographic
verification of domain data or actual read barrier; all positives remain untrusted.
Actual native factory/provider/shared wiring requires separate allocation/review.

## Verification and exclusions

Run standard-library tests (no added dependencies):

`python -m unittest tests.test_control_v3_boundary tests.test_control_api_readonly -v`

After commit, run source-bound runner from a clean LF checkout:

`python tests/control_v3/source_runner.py --expected <HEAD> --output <outside-source-dir>`

`python tests/control_v3/source_runner.py --expected <HEAD> --probe-scratch <new-outside-dir>`

Runner requires exact46IDs (30experimental+16unchangedP0), no failures/errors/skips,
raw primary HEAD/tree inputs before/after and explicit git --no-replace-objects
for every Git subprocess. Negative hidden-assume-unchanged, blob/tree replace and
rawCRLF controls use ONLY an independent owned .git clone, restore bytes/index and
remove replacement refs. They never create refs/replace in linked/source repos.
Hosted Linux/Windows jobs are evidence only after actual success; local source/
loopback PASS is not TLS/native/Consul/Windows physical HA/real LAN/publication/
provider quota/send/slot admission. Experimental responses must not be fed to
frozen A6 consumers or labelled final endpoints/mission acceptance.
