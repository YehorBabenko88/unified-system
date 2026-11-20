# Owned PostgreSQL source port

Grid295 c9ffdaa2af52c4d55871a48655a77a0c669da80f grid/ml_windows_job.py blob f30a09a3af647518d69f7787879defc4d5fa8ab5 moves to the single Unified implementation unified_system/windows_job.py. Only descriptive ML wording changes. Existing bounded synchronous quiescence, handle retention on failure, kill-on-close and suspended assignment are preserved; native behavior is not qualified by pure fakes. No active Grid job path remains in service_postgres. Original repository/blob is preserved.

Owned receipt schema v2 rejects old v1 semantics. Planning takes explicit private credential source and auth_sha256. Dedicated unified.market-data.postgres-auth.v1 binds node, release, canonical market_data commit, database and user; its password never enters public runtime configuration or receipt. Protected credential ACL admission, exact digest and owner-phase checks still precede native initialization. Old Grid/global/fleet credential shapes are refused.

Service activation descriptor/credential production and typed consumer capability propagation require coordinated source integration. No actual database, service, security setting, network listener or installer is modified. Existing historical receipts are preserved and cannot be silently adopted.
