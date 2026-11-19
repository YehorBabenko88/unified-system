# Autonomous release recovery implementation plan

Goal: repair reproducible P0 source defects and independently qualify one immutable candidate cohort. Release remains NO_GO until all mandatory gates pass.

Specification: MASTER #111, assignments #117–#122 and the user's UNIFIED RELEASE engineering request. Execution is explicitly authorized in isolated branches, with no production changes or real trades.

## Ownership and dependencies

| Task | Agent | Isolated checkout | Owned files/components | Completion evidence |
|---|---|---|---|---|
| Math precision | math_p0 | work/math-p0 | canonical market_profile_math and numerical tests | exact sums/FLOOR/delta/ratio; 100k; installed wheel; SHA |
| Windows recovery | windows_p0 | work/unified-windows | TLS/mux teardown and related offline tests | reproduced failure then regression; preserve C3; SHA |
| Durable paper recovery | data_qa | work/terminan-qa | PaperJournal/ledger/archive and direct tests | ACK/retry/restart/digest; installed tests; SHA |
| Cohort acceptance | root | work/release-control | integration_tests, cohort workflow, release manifest/docs | independently installed immutable wheels and four OS/Python jobs |

No concurrent edits to the same checkout. Root reviews each diff before pinning. Existing owner branches are preserved; fixes use new stacked Draft PRs. Grid is sole market producer, Math sole domain compute, Terminan sole paper/strategy owner, Unified sole lifecycle owner.

## Execution checks

- [x] Read MASTER and latest GPT remarks; fetch A–F assignments.
- [x] Inventory every open PR and non-main branch across six repositories; save dependency mapping and exact HEADs.
- [x] Reproduce Math defect independently on original source (100k: wrong FLOOR bucket; traps in accumulation and ratio).
- [ ] Review fixes and run independent installed acceptance.
- [ ] Freeze actual reviewed source HEADs in crossrepo-cohort.json.
- [ ] Build wheels with source SHA/digest receipts and validate installed import origins.
- [ ] Run Windows/Linux Python 3.11/3.12 hosted acceptance; retain failing evidence.
- [ ] Publish source changes, test outcomes, blockers and next queue to MASTER.

## Blocking gates

P0: Windows native timeout/TLS/mux/SQLite; canonical Math context dependence; original historical data recovery and real-source trust; protected C3 operator admission; independent all-history/LFS security clearance. P1: cohort pin drift and missing independent wheel evidence. Physical SSH/LAN/PG/rollback and original user data require separately authorized infrastructure access. No synthetic fixture establishes live qualification.

Review focus: one-shot inputs; exact per-price distribution rather than counts; late bucket ordering; crash before/after atomic ACK; hostile Decimal context on restart; Windows background worker cleanup; false acceptance from checkout imports or moving SHA pins.
