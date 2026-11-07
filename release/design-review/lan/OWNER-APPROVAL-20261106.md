# MASTER CODEX — FINAL LAN APPROACH A DESIGN APPROVAL

**OWNER DECISION: APPROVED.**

Утверждаю полный LAN Approach A, представленный в пакете:

Repository: `YehorBabenko88/unified-system`

Review commit: `dd8b4ff9ace0a75dd81d0ab654e97a1e2319259a`

Full LAN design SHA256:
`f0d2eb3ccd96d263bdbedc2a2bcdd43238a542807c81e7e2531dccb9225cd7f8`

Frozen Bybit Egress profile SHA256:
`16606dee585398ae6d92139ffc1cf2ed37a4d2e08759aaa08f0c3b85958b8049`

## 1. Разрешение Agent 1

Разрешаю начать ограниченную реализацию и изолированное тестирование Approach A.

Использовать утверждённую компонентную базу:

`b12c6c24eeb2c59aa099f1c516d77508f36b20a6`

Создать отдельную feature-ветку, после проверки актуальности и согласованности базы.

Изменять только выделенные файлы:

- `unified_system/lan_transport.py`
- `unified_system/network_budget.py`
- `tests/test_lan_transport.py`
- `tests/test_network_budget.py`
- `docs/network/lan-transport-design.md`

За изменения shared adapters, installer, native identity, security admission, Control API и Bybit probe отвечает Integration Owner либо отдельно назначенный владелец.

## 2. Обязательная реализация

Реализовать:

- Взаимную аутентификацию mTLS.
- Проверку CA, SAN URI, EKU, сертификатных fingerprints.
- Защищённый peer registry.
- Раздельные bounded control/data connections.
- Ограничения frames, queues и connections.
- Credit-based flow control.
- Backpressure.
- Bounded reconnect и cancellation.
- Application-byte accounting.
- Общие LAN budgets с учётом всех процессов узла.
- Persistent Bybit usage/cooldown.
- Fail-closed budget enforcement.
- Защиту от повторных sends после неопределённого исхода.
- Изолированные negative tests.
- Подготовку Windows qualification evidence.

Не реализовывать второй consensus, собственную authority или отдельный несогласованный глобальный Bybit limiter.

## 3. Обязательные нерешённые интеграции

До runtime admission закрыть:

1. Native identity, key и IPC admission.
2. Точный Control multiplex ABI.
3. Реальный Agent 2 authority/fencing adapter.
4. Bybit provider-time policy.
5. Общий NAT egress accounting.
6. Paused-sender containment.
7. Installer/commissioning/rollback.
8. Windows native acceptance.
9. Независимые integration tests.

Отдельно согласовать существующий Bybit read-only probe `/v5/market/time`. Не допускать прямых HTTP-запросов в обход quota enforcement.

## 4. Запрещённые действия

Это утверждение НЕ разрешает:

- Реальные Bybit provider sends.
- Production runtime admission.
- Физическую установку на офисные ПК.
- Изменение Firewall или ESET.
- Изменение роутера, DNS, DHCP, маршрутов.
- Отключение или удаление Tailscale.
- Trust-store/key provisioning на физических узлах.
- Merge в main.
- Реальные торговые операции.

## 5. Результаты

Agent 1 должен предоставить:

- Feature branch.
- Draft PR.
- Exact HEAD и tree SHA.
- Реализованный transport.
- Реализованный budget enforcement.
- Executable contract tests.
- Negative security tests.
- Изолированный six-node mTLS test.
- Windows CI.
- Remaining integration blockers.
- GO/NO-GO.

Главный Codex обязан интегрировать результат с Agent 2, Agent 3 и остальными модулями только после проверки совместимости.

## 6. Статус

FULL_LAN_DESIGN: APPROVED

AGENT1_ISOLATED_IMPLEMENTATION: AUTHORIZED

ISOLATED_TESTING: AUTHORIZED

REAL_PROVIDER_SENDS: BLOCKED

PRODUCTION_RUNTIME: BLOCKED

PHYSICAL_DEPLOYMENT: BLOCKED_BY_THIS_APPROVAL

TAILSCALE_REMOVAL: BLOCKED

MAIN_MERGE: NOT_AUTHORIZED

Продолжай MASTER MISSION. Не считай design approval доказательством работоспособности runtime.
