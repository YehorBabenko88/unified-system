-- SOURCE ONLY. Root must open the exclusively allocated local.sqlite read-only.
-- URI: file:<admitted absolute path>?mode=ro ; no sqlite3 CLI installation assumed.
PRAGMA query_only = ON;
PRAGMA integrity_check;
SELECT COUNT(*) AS local_record_count FROM transitions;
SELECT sequence, state, previous_hash, digest, receipt
FROM transitions ORDER BY sequence LIMIT 65;
-- SQLite integrity_check is structural only. Journal.read must additionally
-- validate chain hashes; PendingPublicationJournal validates exact original bytes.
-- No dataset catalogue/COMMITTED receipt/source checkpoint table exists here.
