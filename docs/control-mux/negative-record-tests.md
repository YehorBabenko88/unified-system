# Additional isolated negative record tests

This test-only extension follows exact PR32 head5fd0ccbd28c79fb5ff040ecb1030462ac4baef35. Product modules, frozen Review4 and GET review2 schema/model/plan bytes remain unchanged. It does not authorize endpoint activation or transfer any earlier scoped ACK.

Six actual native KV fault windows cover missing response, mismatched response hash, wrong receipt request, PENDING with terminal evidence, nonempty204, and a hash-consistent response bound to another close target. Reconciliation must return unavailable and leave connection debt unchanged. The fixture restores original bytes through native writes, so native receipt ModifyIndex can advance; this is not an assertion that adversarial Consul writers cannot rewrite trusted state.

Eight additional actual transaction races revoke each of principal/session/enrollment/policy after its native index was captured, immediately before prepare or final native transaction. Each guarded native transaction must reject. Preparation leaves no original intent; final rejection leaves the same original PENDING intent and bounded pending hold, no receipt and no parent state/debt release. Current identity is restored by the isolated fixture only. Evidence retains checked/changed actual native indices and attempted serialized transaction SHA256, not a fabricated success flag or wall-clock proof.

The mandatory real case inventory is now42: all previous28 plus14 negatives. Cooperative real-case timeout is150seconds (extended from90 for the additional native round trips); outer qualification child stays240seconds. Context-manager cleanup tracks and stops only its owned process handles even on timeout. All fixtures bind loopback and remain explicitly synthetic identity; they do not qualify authentication, containment, snapshot producer, Windows fleet or native listener.

Fresh raw-source qualification is required for this test-only source head. Exact5fd evidence and A6 GET model ACK remain separately pinned; no old PASS is relabeled.
