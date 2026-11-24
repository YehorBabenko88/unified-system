# Proposed logical codec composition: bounded Root review

DESIGN ONLY / NO-GO. ROOT-COMPOSITION.json identifies relative immutable layers
and effective schema paths. All four original seals/members were size/SHA256
verified and preserved; old deficient proposals remain history, not effective
schemas. This is not an approved wire ABI, implementation base or native plan.

Root read review1 CONTRACT and its five schemas, review2/3 complete addenda,
review4 complete disclosure contract/composition/private/public schemas and the
review3 receipt conditions/native session definition. Selected read-only regex,
literal pairing and public-branch predicates were checked with the standard
library; Root did not run builders, schema engines, applications or native calls.

Scoped design direction ACK:

- Explicit proposed namespaces remain rejected by current consumers until adoption.
- Review3 native SessionID has canonical lowercase36hex and no version/variant
  restriction; client/job/actor UUIDv4 remains distinct. Syntax is not authority.
- Queue PLUS_ONE/sequence1/previous0 and cancel MINUS_ONE/sequence2/previous1
  are explicit. Quota arithmetic, exact old state, actor/original/phase/native
  joins and real all-writer CAS proof remain mandatory and unimplemented.
- Review4 public no-disclosure branch contains only schema/status; selection
  must be resource-blind. Private known history survives expiry without exposure.
  LOGICAL_HISTORY requires a real fixed current reader, coherent snapshot and
  final visibility revalidation; JSON is never a grant. No scientific payload.
- Dedicated bounded adapter around the existing Journal is a design allocation
  proposal only. Attempt-local rejection/non-send is not original-wide absence;
  pending UNKNOWN custody cannot be evicted/refunded/rekeyed. No shared Journal
  code change or widening of native16KiB is approved.

Owner A4/A5/A6 exact successor reviews are retained, each direction-only. They
do not provide full semantic tests, actual API, source adoption or native proof.
Queue22ops/10166B and cancel25ops/10638B are one FORMAT_ONLY sample, not a maximum,
valid authorization, executed transaction, load test or transport compatibility.
Client envelope and server-internal Consul plan are separate boundaries; actual
outer/context/capture/response/custody limits and ABI still need agreement.

Strict D4 option1 remains current: logical mutations DISABLED. Actual old broker
P2 requires NATIVE_SESSION_INVALIDATION_NOT_UTC_AT_COMMIT and does not satisfy
that strict guarantee. An operator question about a separately versioned design
was raised; no answer/approval is assumed and old profiles are unchanged.
Implementation base NONE_APPROVED, operator HA approval absent, no actual positive
resource/consume/start/publication/current scientific READ APIs. No native send,
private commissioner, physical installation, provider/trading operation or merge.
