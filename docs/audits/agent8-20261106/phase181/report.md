# MCI: независимое подтверждение отказа обязательного CI

| Requirement ID | Repository | PR | Exact HEAD / tree | Test name | Environment | Expected result | Actual result | Evidence link | Status | Severity | Required correction |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A8-F40 | unified-system | 81 | e869d8365c7e54ed3da3739d9cdf15948f37f022 / 8de558ea63b82a0b710a1dcea3459996057cb216 | MCI exact test inventory | GitHub Ubuntu24.04 + Windows, attempt1 | Все обязательные ID проверены и выполнены | Оба задания требуют47, обнаруживают58; AssertionError до выполнения тестов | [run](https://github.com/YehorBabenko88/unified-system/actions/runs/42869185791), [independent proof](verification.json) | FAIL | P1 | Строго включить все58 ID, отклонять дубликаты и подтвердить hosted successor |

Свежие GET run/jobs/artifacts/logZIP сопоставлены с точным исходным кодом. 58=50 Mission+8 Journal; отсутствуют10 continuation и существующий owned-temp-alias. Это отдельный дефект конфигурации CI, не F26 heartbeat. Оригинальные логи сохранены; артефактные payload этой фазы не квалифицированы. Исправление на96b проверяется отдельно в phase183; исходный отказ не переписан в PASS.

RELEASE_MANIFEST_STATUS: не утверждённая сборка. NODE_INVENTORY_STATUS: новой проверки нет. CONTRACT_STATUS: без новых полномочий. OFFLINE_TESTS: только A8 AST/raw-hash/data verification. WINDOWS_CI: данный обязательный gate FAIL. PHYSICAL_TESTS: BLOCKED. P0_P1_P2: 8 открытых P1 /8 P2; отсутствие P0 не доказано. EVIDENCE: оригиналы и verification.json. NEXT_ACTIONS: exact successor hosted MCI; без rerun со стороны A8. GO_NO_GO: NO-GO. TAILSCALE_REMOVAL_ACCEPTANCE: BLOCKED/NO-GO.
