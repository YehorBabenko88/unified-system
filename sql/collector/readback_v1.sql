-- SOURCE ONLY. Bind $1=context_id and $2=binding_sha256; read-only projection.
BEGIN READ ONLY;
SELECT c.context_id, c.instrument_id, c.binding_sha256, c.store_id,
       c.custody, c.lifecycle_state, i.identity_kind, i.identity_contract_sha256,
       p.observation_sha256, p.raw_journal_digest, p.local_lifecycle_sequence,
       p.native_outcome, p.publication_confirmed
FROM collector_metadata_v1.context AS c
JOIN collector_metadata_v1.instrument AS i USING (instrument_id)
LEFT JOIN collector_metadata_v1.local_checkpoint AS p USING (context_id)
WHERE c.context_id = $1 AND c.binding_sha256 = $2;
SELECT observation_sha256, raw_journal_digest, payload_sha256,
       payload_byte_count, observation_kind, continuity
FROM collector_metadata_v1.observation_ref
WHERE context_id = $1 AND EXISTS (
    SELECT 1 FROM collector_metadata_v1.context
    WHERE context_id = $1 AND binding_sha256 = $2)
ORDER BY observation_sha256
LIMIT 17;
SELECT hold_id, reason FROM collector_metadata_v1.retention_hold
WHERE context_id = $1 AND EXISTS (
    SELECT 1 FROM collector_metadata_v1.context
    WHERE context_id = $1 AND binding_sha256 = $2)
ORDER BY hold_id LIMIT 129;
COMMIT;
