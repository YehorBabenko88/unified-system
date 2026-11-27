# Inactive application boundary v2

The closed installation-transaction DTO now uses unified.installation-transaction.v2 and application_boundary=EXISTING_EPHEMERAL_GUARD_UNCHANGED. This declares preservation of the existing ephemeral application guard; it does not prove or grant filesystem, native service, distributed consensus, install or source authority. V1 and grid_boundary are refused, with no adapter or alias.

The sole source_plan producer and validate_plan consumer change together. Supervisor preparation passes the DTO through; its two active schema expectations change to v2. Root lifecycle/Consul comments now identify the canonical Root owner. Historical records, raw archives and old schema evidence remain immutable.

TDD uses only selected actual validate_plan AST with pure path/format fixtures; source_plan is inspected as AST and never called. All effectful imports/helpers, installer prepare/apply/dry-run, SQL, native/service/registry/PowerShell, threads and sockets remain unexecuted. Full installer/supervisor integration tests are HELD_LOCAL. Existing app-only uninstall retention, blocked configuration/full purge, inactive staging/retained logical rollback and native hold are unchanged. No Root pins, Source802 inputs or32role bytes are changed.

Private implementation sequence: isolate from e4cdfd5fa88857936a5b896b9f7742e2913d048d; RED the eight pure contract cases; change the closed v2 field and active assertions/comments; GREEN both Python versions; verify inverse and unchanged protected bytes; freeze for independent QA before publication.
