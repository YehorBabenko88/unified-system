# Primary Git source pin correction

Original PROTOCOL.md97bc538785bc696826348928c3c26b5757fd52622d7cdbe5a74a4e62ca3bd566
is preserved. Its ObjectStore4f6c9de... and manifest8e83c449... hashes identify
physical CRLF workspace bytes and are NOT primary Git source pins. They do not
admit an executable source capsule by normalization equivalence.

Actual raw primary Git bytes at Unified f9f2d04595cf2360dab78980996ae6c34c9e26fc,
tree7fa3c8ad67c4efece7e2a692f48fb63a9e40ffd3:

- unified_system/storage/object_store.py: 9211 bytes,
  primary Git blob OID92b90bd39328c15f3ad987e45e5807d6732b02bd,
  SHA256193c4e68e48dcdda212412ed7bd00d23afa04fe36bffb84c074948602bb8f739.
- unified_system/storage/manifest.py: 4614 bytes,
  primary Git blob OIDaaac94646a7f1d0b5dce453e1a7082a7a4fa1efe,
  SHA25643f7eb6961248d7ec21e4f2ab0d4e2c0e70876590d590ccd7cf18b934c9605e1.

Agent3 independently read these exact objects with git --no-replace-objects show
and hashed returned bytes without shell/text newline conversion. Actual tests
must load primary-byte-verified source with its complete pinned dependency closure;
these two files alone are not a capsule or approval of arbitrary import origins.
No edits to A4 source or original preimages/inventory. Positive capability/API
admission remains pending separately; fixed fixture/pure codec test scope only.
