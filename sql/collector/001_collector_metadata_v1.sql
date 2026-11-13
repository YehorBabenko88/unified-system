-- SOURCE ONLY. Execute only in a newly authorized isolated PostgreSQL database.
-- Fail on namespace reuse. This projection grants no publication authority.
BEGIN;
CREATE SCHEMA collector_metadata_v1;
CREATE TABLE collector_metadata_v1.instrument (
    instrument_id text PRIMARY KEY CHECK (length(instrument_id) BETWEEN 1 AND 256),
    identity_kind text NOT NULL CHECK (identity_kind IN ('SYNTHETIC', 'UNKNOWN')),
    identity_contract_sha256 text CHECK (identity_contract_sha256 ~ '^[0-9a-f]{64}$')
);
CREATE TABLE collector_metadata_v1.context (
    context_id text PRIMARY KEY CHECK (context_id ~ '^[0-9a-f]{32}$'),
    instrument_id text NOT NULL REFERENCES collector_metadata_v1.instrument(instrument_id),
    binding_sha256 text NOT NULL CHECK (binding_sha256 ~ '^[0-9a-f]{64}$'),
    store_id uuid NOT NULL,
    custody text NOT NULL CHECK (custody = 'LOCAL_UNATTESTED'),
    lifecycle_state text NOT NULL CHECK (lifecycle_state IN ('ACTIVE','STOPPED','UNKNOWN','TERMINAL')),
    UNIQUE (context_id, binding_sha256)
);
CREATE TABLE collector_metadata_v1.observation_ref (
    context_id text NOT NULL REFERENCES collector_metadata_v1.context(context_id),
    observation_sha256 text NOT NULL CHECK (observation_sha256 ~ '^[0-9a-f]{64}$'),
    raw_journal_digest text NOT NULL CHECK (raw_journal_digest ~ '^[0-9a-f]{64}$'),
    payload_sha256 text CHECK (payload_sha256 ~ '^[0-9a-f]{64}$'),
    payload_byte_count integer NOT NULL CHECK (payload_byte_count BETWEEN 0 AND 1048576),
    observation_kind text NOT NULL CHECK (observation_kind IN ('OPAQUE','SYNTHETIC','GAP')),
    continuity text NOT NULL CHECK (continuity = 'UNKNOWN'),
    PRIMARY KEY (context_id, observation_sha256),
    UNIQUE (context_id, observation_sha256, raw_journal_digest),
    CHECK (payload_sha256 IS NOT NULL OR payload_byte_count = 0)
);
CREATE TABLE collector_metadata_v1.local_checkpoint (
    context_id text PRIMARY KEY,
    observation_sha256 text NOT NULL,
    raw_journal_digest text NOT NULL,
    local_lifecycle_sequence integer NOT NULL CHECK (local_lifecycle_sequence BETWEEN 1 AND 128),
    native_outcome text NOT NULL CHECK (native_outcome = 'UNKNOWN'),
    publication_confirmed boolean NOT NULL CHECK (publication_confirmed = false),
    FOREIGN KEY (context_id, observation_sha256, raw_journal_digest)
        REFERENCES collector_metadata_v1.observation_ref
            (context_id, observation_sha256, raw_journal_digest)
);
CREATE TABLE collector_metadata_v1.retention_hold (
    context_id text NOT NULL REFERENCES collector_metadata_v1.context(context_id),
    hold_id text NOT NULL CHECK (length(hold_id) BETWEEN 1 AND 256),
    reason text NOT NULL CHECK (length(reason) BETWEEN 1 AND 1024),
    PRIMARY KEY (context_id, hold_id)
);
COMMIT;
