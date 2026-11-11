# F26 pre-reentry review1 / V2 compact contract proposal

SOURCE_PREP_ONLY / IMPLEMENTATION_HELD / NOT_EXECUTED / NO_PUSH.
BASE_SHA bfa3b24d8f209d5e91acfa64819d3ebed4967af7
BASE_TREE 0145968d0492f0a87d3e1a7e1eecc0b34a0c4a98
Branch agent1/f26-pre-reentry-source-review1-20261110.
Only this document and NEW tests/test_lan_pre_reentry_diagnostics.py prepared.
Existing helper/test and all production files untouched. No project imports,
compile, discovery, tests, fixtures, native calls or source publication performed.
Standalone stdlib JSON arithmetic only; not execution of helper/test source.

## Scope and exact packed schema proposal

Keep existing LAN_FAIL_DIAG_V1 prefix,1960-byte ASCII cap and existing fields.
Proposed additional top-level key pre contains exactly TWO fixed ten-integer rows:
[slot,bits,idle,current_site,current_code,current_family,current_order,
 close_code,close_family,close_order]. Slots1,2 only. Unknown slots cannot allocate.
Default rows [1,0,0,0,0,0,0,0,0,0] and [2,0,0,0,0,0,0,0,0,0].
No third connection, strings, times, arbitrary keys, payload or event trace.

bits0..31: READY1, CONTROL_RETURN2, CONTROL_REENTRY4, DATA_WAIT_EXPIRED8,
IDLE_CALLED16. idle:0NONE,1TRUE,2FALSE,3UNAVAILABLE; exact bool only.
current_site:0NONE,1READER,2PONG,3OTHER.
Family:0NONE,1TRANSPORT,2BUDGET,3SSL,4TIMEOUT,5OS,6OTHER,7UNAVAILABLE.
Code table:0NONE,1OTHER,2ASSERTION,3BUSY,4UNAVAILABLE,
5DIAGNOSTIC_UNAVAILABLE,6DEADLINE,7DISCONNECTED,8DELIVERY_UNKNOWN,
9POLICY_REVOKED,10CANCELLED,11BUDGET_STORE_UNAVAILABLE,
12BUDGET_CLOCK_UNCERTAIN,13OVERLOADED,14CLOSED,15AUTH_REJECTED,
16PROTOCOL_REJECTED. These are fixed local enums, not network/API contracts.
Order: one shared saturating counter0..255; each accepted observation advances
it to min(255,n+1), no rollover. First current failure/first close entry stored
once per slot; later observations cannot overwrite. Equal255 means ordering
unknown after saturation, never strict happens-before proof. Separate fields
order only those first entries; readiness bits carry no history/timestamps.

close_order denotes FIRST OBSERVED CLOSE ENTRY, not proof of first actual
closed=False->True transition. Without holding/changing production cv around
original close, observer cannot make that stronger claim under a race. Retain
this explicit semantic limit; do not infer initiating cause from final error.
Observer lock is nonblocking; BUSY/UNAVAILABLE stays explicit. Internal references
and thread-context tags never serialized, and all calls delegate exactly once.

## Proposed actual-helper API (not implemented / not frozen)

Private tests.lan_failure_diagnostics._PreReentryState:
readiness(slot,event), idle_result(slot,value),
current_failure(slot,site,code,family), close_entry(slot,code,family), packed(),
call_current(slot,site,original_callable).
The call_current pure wrapper returns original result or rethrows same exception
object. Recording exceptions cannot replace result/error. Hook attachment to
actual fixture is IMPLEMENTATION_HELD; no production source change proposed.

PONG context must come from exact own observed_emit invocation, privately scoped
to that thread. READER means own control-reader thread outside nested emit. Any
uncertain attribution OTHER. Guard is local registry admission, not HA fencing.
Original read/emit/current/close/body limits/security/timers remain unchanged.
No exception str/repr, stack, callback args, thread IDs, socket IDs, peer/registry
records, keys/certs, request bodies or absolute wall timestamps may enter wire.

## Exact worst-case ASCII arithmetic and concrete conflict

Arithmetic uses json.dumps(sort_keys=True,separators=(',',':'),ensure_ascii=True,
allow_nan=False),17-byte prefix and1-byte newline. Maximum old code is24 ASCII
characters BUDGET_STORE_UNAVAILABLE, not22 BUDGET_CLOCK_UNCERTAIN. Old allowed
maximum state:2connections,2streams+2jobs each,5false alive flags,2stores,4IO;
7-digit scalar maxima, negative8-character remaining times,19-digit grants.
JSON value sizes by old top-level member: v1,stage15,code26,observer13,
connections795,stores317,io729,truncated5. Key/separator/braces79. Therefore
old JSON1980 +prefix17 +newline1 =1998 bytes. This already uses the OLD formatter's
existing fallback (2IO,1job/1stream per connection,truncatedtrue):1393 bytes.
The packed pre addition is EXACTLY66 bytes: key/separators plus two10-int rows
(max row [2,31,3,3,31,7,255,31,7,255], whose two-digit code width bounds all enums).
Full old+new2064; old fallback+new1459. Existing cap itself is NOT changed.

Concrete additional-loss counterexample: take that same valid full old state and
set each store entry_ms,hold_ms,max_ms,n,budget_ms to0 (ten7-digit->1-digit values).
Old line1938 bytes, all4IO/2jobs/2streams retained, truncatedfalse. New line2004
bytes exceeds1960 by44. Existing fallback would discard2IO and onejob/onestream
per connection that the original1938-byte line retained. Thus adding66 bytes
causes EARLIER information loss, despite fitting the old already-truncated path.
No formatter can keep this exact textual old representation AND proposed66-byte
schema within1960 for that state. No cap increase/extra drop silently accepted.

CONFLICTS: strict preservation of every previously retainable field conflicts
with proposed addition at1960. Need Root decision on a versioned compact legacy
encoding or explicitly revised retention semantics BEFORE implementation. Neither
is authorized here. The new test release gate deliberately demands no earlier
truncation; no expectedFailure/skip/limit relaxation may bypass it.

## Initial pure regression scope (superseded by V2 extension below)

Ten eventual actual-helper tests: fixed2slots, exactFalse/bitmask, sticky first
current site/code/family/order, sticky first close-entry, ordinal saturation,
private str/repr tripwires, original call once/return identity, same exception
identity despite observer failure, actual formatter private-data rejection,
and1938-byte no-earlier-truncation release gate. They import eventual ACTUAL
helper in setUp and contain no helper clone/model implementation. Base lacks
proposed API: source is intentionally unexecuted/unintegratable pending review.
Do not discover/import/compile/run this module or alter shared mandatory inventory.
No project fixture/native/process call is needed by the proposed pure cases.

Root review required for conflict resolution/exact API before implementation;
then separate pure-test allocation. F26 OPEN/NO-GO. Historical96 cause UNKNOWN;
current bfa no-heartbeat-error observation does not establish root cause.


## V2 revision: resolves wire-size conflict by reversible aliases only

SOURCE-DESIGN revision2, NOT_IMPLEMENTED / NOT_EXECUTED. Earlier V1 size conflict
is retained above as provenance. V2 supersedes the proposed V1 pre addition and
its blocked release gate; V1 prefix, encoder, historical bytes and semantics are
UNCHANGED. No opaque binary encoding, code-value remapping or legacy field loss.

Wire prefix LAN_FAIL_DIAG_V2 (same17 bytes including trailing space), wire v=2.
Decode returns (legacy_v1_body,pre_rows), where legacy_v1_body is EXACTLY the
JSON object the existing V1 formatter selected, including v=1, every retained
field, arrays, values, BUSY/UNAVAILABLE and truncated flag. New rows remain a
separate result, never silently inserted into historical V1 semantics. V1 decode
returns (original_body,None). No historical line is re-labelled V2.

Retention algorithm, exact order:
1. Call original V1 format_failure(state,code) once, unchanged, ignoring additions.
2. Parse its bounded ASCII line with duplicate-key rejection. That already chose
   old full/fallback/unavailable semantics. Do not choose retention from V2 size.
3. Reversibly alias ONLY dictionary keys, recursively; string values untouched.
   Replace root v=1 with v=2, add reserved root P for the two packed rows.
4. Encode ASCII compact sorted JSON, same1960 cap. Never run another lossy
   retention fallback due to additions. Under the closed schema bound below this
   fits. Internal/shape/encoding failure emits explicit unavailable V2
   {"k":"DIAGNOSTIC_UNAVAILABLE","t":true,"v":2}, no P, no invented legacy state.
   Decoder restores that sentinel exactly to V1 {code,truncated,v=1} and pre=None.
   This sentinel is UNAVAILABLE, never a claimed complete diagnostic or PASS.

Closed global dictionary-key alias registry (case-sensitive,34 injective keys):
active:A, age_ms:a, alive:f, budget_ms:B, budget_waiters:W, channel:C,
closed:d, code:k, connections:c, elapsed_ms:E, entry_ms:e, error:x,
held:h, hold_ms:H, io:i, jobs:j, max_ms:m, n:n, observer:o, phase:p,
q:q, qb:b, read:R, remaining_ms:u, slot:l, stage:g, state:z, stores:s,
streams:r, truncated:t, v:v, waiters:w, why:y, write:T.
P reserved exclusively for root pre array; NOT an alias or allowed nested key.
No dictionary-key aliasing applies to list scalar values. Registry is not learned
from input and must be immutable. Decoder inverses only this table, then checks
allowed keys/types/bounds for each original root/connection/store/IO context;
reject unknown/duplicate aliases, misplaced P, extra fields, wrong version,
non-ASCII/over1960 input BEFORE JSON parsing, duplicate decoded keys, malformed
rows, invalid enums/integers/bools, bad slot order/count. Never str/repr hostile
objects. Decoder failure is fixed ValueError with no input echo. No tolerant
unknown-key dropping. JSON max depth fixed for this schema; no arbitrary recursion.

Proposed eventual actual-helper additions (still not implemented):
V2_KEY_ALIASES immutable registry, format_failure_v2(state,code='OTHER',*,pre=None),
decode_failure(line)->(legacy_v1_body,pre_rows_or_None). Old format_failure stays
V1. Internal _PreReentryState API/semantics above retained. Normal V2 formatter
always provides two default rows when pre absent/invalid; malformed private data
never enters output. Explicit unavailable sentinel alone may omit P.

## V2 ASCII bound for ALL bounded collection shapes

Same exact maximal scalar values, key retention and booleans as earlier proof.
Alias replacement saves380 bytes from the old1998 full state: compact full1618.
Reserved P addition adds64 bytes (rather than66 for long key pre). Hence
hypothetical unretained full V2=1682 <=1960, margin278. This is an upper bound
EVEN BEFORE using V1's required fallback. Selected maximal old fallback1393
encodes V2=1167. Old1938 witness retains ALL original fields and V2=1622.
No earlier fallback/drop occurs. Prefix/version-number/newline lengths identical.

Why all bounded shapes are covered: each full connection row upper-bounds the
shorter state-only BUSY/UNAVAILABLE row. Every optional stream/job/alive element
and connection/store/IO row adds positive bytes; choose all2/2/5/2/2/4 maxima.
Seven-digit/negative8-character scalars,19-digit grants,false bool and longest
allowlisted string upper-bound all legal value alternatives. Root full schema
upper-bounds sparse sentinel. Fixed2 ten-int P rows are already maximized.
Deletion of any collection element/key or shortening a bounded scalar cannot
increase compact JSON length. Thus1682 dominates every valid bounded pre-retention
shape. Old V1 retention only removes/shortens fields (true is shorter than false),
so cannot exceed this bound. Malformed/unbounded inputs are rejected/unavailable,
not covered by a fabricated full-state bound.

## Revised source-test card and approval gate

Prepared17 eventual actual-helper regression methods (NOT imported or compiled):
prior10 actual-recorder/privacy/transparency cases, with V2 decode comparison for
the1938 witness, plus7 V2 codec cases. Codec cases cover immutable closed registry,
historical V1 decode, selected old fallback retention, all2430 bounded collection
length combinations comparing DECODED state to actual V1 formatter, BUSY/UNAVAILABLE,
duplicate/unknown/wrongversion rejection, oversized/non-ASCII rejection. No mirrored
helper codec implementation or AST-only behavioral assertion. Tests reference
actual future helper API, absent at BASE; do not integrate/discover/run now.
The exhaustive-length case is one pure regression method, not2430 test IDs.
No shared mandatory inventory update authorized.

CONTRACT_COMPATIBILITY: V1 historical wire/retention unchanged; V2 explicit new
prefix and closed decoder required. This is a fixture-only proposal, not transport
or module ABI. Root must approve registry, decoder failure semantics and recorder
API before existing two held paths can change. No timing/cadence/security/frame
change requested. All physical/runtime/provider admissions unchanged.
CONFLICTS: review1 V1 addition conflict resolved IN DESIGN by380-byte key savings;
implementation, actual pure verification and wire-parser adoption remain HELD.
BLOCKERS: Root exact API review; subsequent separate implementation/test scope.
NEXT_ACTIONS: Root/A8 source review only; no tests, imports, compile, fixture or push.


## A8 source correction: closed enums and historical sentinel acceptance

Positive1938-byte retention witness now uses legal maximum code16, not reserved31.
Two-digit width and all size bounds remain identical.31 appears only in explicit
invalid-code negative source: formatter defaults the entire invalid pre input to
two zero/default rows; strict decoder rejects wire code31 rather than roundtrip it.
This corrects a proposal-test defect, not an observed helper failure; no run.

Historical V1 decoder accepts EXACTLY these existing emergency sentinel shapes:
{code:"DIAGNOSTIC_UNAVAILABLE",v:1}, emitted by emit_failure exception fallback;
{code:"DIAGNOSTIC_UNAVAILABLE",truncated:true,v:1}, emitted by formatter size fallback.
Absence of truncated in the first is preserved, not filled with a fabricated bool.
No observer/connections/stores/io/stage is required for those exact sentinel
contexts. Normal full V1 records retain their existing validated schema; arbitrary
partial records, extra keys, false truncated sentinel, duplicate keys or alternate
codes do not gain emergency-sentinel acceptance. Decode returns original object
unchanged plus pre=None. Encoder V2 unavailable still has explicit t:true/v:2;
V1 emergency without truncated is historical decode-only compatibility, never
permission to omit required fields from normal V2 records.All17 existing proposed method IDs remain; both corrections are assertions
inside existing codec methods, not new test IDs. Existing helper/test paths remain IMPLEMENTATION_HELD.
