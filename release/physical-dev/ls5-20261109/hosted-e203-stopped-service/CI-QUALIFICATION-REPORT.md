# PR69 stopped-service hosted evidence

Exact source: `e203c0bbeaa176a843a7d80b2eadfefe8fce7385`. Captured 2026-11-09 23:16 UTC (2026-11-10 Europe/Berlin).

Both attempt-1 runs completed successfully: PR 42716081580 and push 42716071876. Four GitHub-hosted jobs cover Windows2022 and Windows2025. Each original log proves 15 regression cases passed, then PASS_COMPONENT_STOPPED_SERVICE_ONLY. This is 60 executions of 15 distinct cases.

All four artifact ZIP SHA256 values match GitHub metadata; internal report manifest hashes match. Reports bind exact source head/tree before/after and confirm native_create_inspect plus APP_ONLY removal (SCM/code absent; state, ownership and uninstall journal retained).

Scope remains DISPOSABLE_HOSTED_STOPPED_SERVICE_ONLY: service_start NOT_RUN; source_proof NOT_EVALUATED; activation BLOCKED; physical NOT_RUN; execution_authority=false; installation_closure=false; publisher_authenticated=false. No full CI matrix or LS5 physical/backend/native worker result follows.

Original JSON, ZIPs and stderr are private local evidence. No retries, dispatch, rerun, cancellation, local native execution or source changes. Other queued runs were not reobserved.

## Original capture SHA256

- `42716081580-run.json`: `066aaac1ed6f1ef7a611a6835346181e1609e249ae7dc10b18ead0b742e03ca9`
- `42716081580-jobs.json`: `a70e3f22a29b652d56c5d201ee18422d4fd036f6802102ad53ce1a55dc27ff5b`
- `42716081580-logs.zip`: `c01080f8709b1d3c2d5062bf34a307a653b7b508cbc36ba7d87a27fd68db26d9`
- `42716081580-artifacts.json`: `ddb5f52f7612e077d512ac2f57c8cd17bc131fd40d865a4de1b10e78c71280e2`
- `42716071876-run.json`: `a34a394abf038b484cd2655d0c57b009c672b6073da57386dbacbeafed13f425`
- `42716071876-jobs.json`: `bf06312a017c1b358976ba21acf7ac6b7e67ca793da399d45b628c055b798b69`
- `42716071876-logs.zip`: `02bfa2e7aff0579d91a5264092db3d6b806074375106688aa87b87ea660bb66c`
- `42716071876-artifacts.json`: `a89bfe5179433bb6470301c47ff0a4b205e550c414f4d876d03905138fdbb000`
- `artifact-13718637089.zip`: `c3180be5547f06f1739084d4cad4a29fe834ef1da3edccfd110315315d413e3a`
- `artifact-13718237782.zip`: `32bb64d282bc6dfb3f6bcf64d847ceefea7ad13b0403092053f2a8629e41daf3`
- `artifact-13718756017.zip`: `c201ff70620e7f8363b8b78df90e76da6991249b976aaf61aeefc6c234c057e6`
- `artifact-13716594619.zip`: `0cd9e52f653fbacb4f16c39d79a2bc8c5fe781521a432c30ef5da94918a1f093`
