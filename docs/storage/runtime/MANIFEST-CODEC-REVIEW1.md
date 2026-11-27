# Local per-instrument manifest candidate codec

This additive isolated codec implements local data validation/readback only.
It is not admitted shared wire, a dataset catalog service, a committed manifest
publisher, replica eligibility or proof-dependent checkpoint recovery adapter.
Exact manifest binding proposal root schema is a599b399cb8809ad72a2ecdb778a4e7e419f88a6cadcf2da20489cf93d12fd10;
its initial Bybit instrument/data-kind profile is intentionally explicit.

decode_manifest accepts only canonical bounded ASCII JSON with closed exact
root/lineage/instrument fields and strict UUID/hash/identifier/u63 checks. Genesis
has revision1 and null predecessor. Later revisions require a predecessor hash.
validate_manifest_successor checks equal immutable lineage, previous exact root
hash and independent manifest revision+1. It does not inspect a trusted current
head or prevent two writers from presenting the same predecessor. Such checks
must be coupled with actual A2 native CAS/proofs in the future admitted adapter.

read_manifest_object reads and hashes actual bytes from the isolated ObjectStore
and validates the root. No referenced segment/coverage/dependency/data-schema object
is read or promoted by this method. A syntactically valid root with missing pages
remains an untrusted claim: closure_verified and publication_confirmed stay false,
and require_publication_authority always raises. No codec/provider callback opens it.

Lineage excludes job/generation and binds exact cluster/dataset/source/partition,
instrument version and data kind. A changed instrument/version/kind is not a
successor. Registry existence/nonreuse/admission is NOT proved by a valid UUID or
tuple. The source uses no default instrument version, clock-as-revision or coercion.
The immutable raw bytes are preserved; decoded mapping copies cannot alter them.

The schema's structural constraints and runtime semantics are distinct: runtime
additionally rejects invalid genesis/predecessor relationships, noncanonical bytes,
duplicate keys, numeric JSON scalars and overflow. Claim construction validates
the same bytes; no fabricated VERIFIED or authority result can be constructed.

P0: actual immutable registry, referenced-object/page/coverage/schema codecs,
native head/version CAS, actor/quota/closure/accounting/replica proof and exact
shared interface admission. P1: full measured atomic ledger/native fault/hosted
and physical evidence. Single-volume local readback never lowers two-copy policy.
No data overwrite/delete, policy operation, office/provider/service/deployment.
