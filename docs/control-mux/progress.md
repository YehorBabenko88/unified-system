# SDD ledger — plan: docs/control-mux/runtime-plan.md
Base360c5cdc / treec8cc05a06cd2c9cfca6317ad06e1af1efefd0050. New branch feature/agent2-control-mux-runtime-20261107. PR31 ref unchanged.
Pre-flight: codec exactbytes->commandpreimages; Root current native auth->same Consul txn authorization records; store actual receipts->HTTP. No external domain producer currently available.
Task1 partial: codec RED missingmodule then4PASS; commands RED missingmodule then6PASS; defaultHTTP boundary RED missingmodule then7PASS. Interpreter A6schema-venv read-only deps, Python test reports in Agent2 work/mux-*.log. No actual OPEN/Consul runtime claim.
Ruling: plan saved under explicitly allocated docs/control-mux instead of shared docs/superpowers; no unallocated files touched.
Ruling: isolated Consul stand authorized by Root directowner continuation 2026-11-07. Scratch native exe read-only pin41762ef5...; no services/firewall/security/provider actions. Real qualification pending.

Incremental review p0_code_review: no codec/preimage defect; found default503 envelope and HEAD body. Both observed RED (error+failure), fixed, 9testsPASS. Real stand bootstrap run:3persistentBoltDBvoters/1leader, eachconsistentHTTPraftread, all3ownedPopenhandles stopped. Evidence outputs/CONTROL-MUX-REAL-CONSUL-STAND-BOOTSTRAP.json in Agent2workspace; no productOPEN/endpointqualification.
