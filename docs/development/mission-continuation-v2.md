# Development continuation v2

Root-approved implementation choice: extend the existing marker-v2 Journal, not a controller or executor. Preserve closed v1 task validation, put and projection contracts. New closed development-continuation/version-2 receipts bind a complete current task snapshot SHA256 to explicit source HEAD/tree, status, last verified result, evidence, retry budget, next descriptive step, blocker and authorization references.

The checkpoint API uses the existing global sequence CAS and capacity reservation. Replay validates every historical binding against its contemporaneous task. Later task drift marks the retained checkpoint stale through replay, including A-to-B-to-A changes; only an explicit appended checkpoint refreshes it. Returning to the original digest never reactivates an old checkpoint. Retry maximum is fixed (0..32), usage never decreases, including after restart or stale refresh. No implicit v1 conversion occurs. Old binaries are not forward compatible with new receipt kinds.

Implementation sequence: regression tests first; closed metadata validation and replay; explicit checkpoint and detached projection; bounded local verification. Process restart proof, if separately run, is PYTHON_RESTART_NOT_CODEXAPP_RESTART. Actual Codex app restart is not tested here.

All statuses, source pins, result scopes and authorization references are observations, not provenance or permissions. Next steps are descriptions, never executed commands. Public submit remains DENY; node/native/runtime/physical/trading grants are false. D4 remains disabled and PC4 blocked. No scheduling, retry execution, dispatch, network, native execution or admission is introduced. Original receipts are retained; no migration or repair is provided.
