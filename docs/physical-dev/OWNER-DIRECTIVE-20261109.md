# CODEX — MASTER MISSION PHYSICAL DEVELOPMENT LOOP
## Real Windows Testing + Parallel Runtime Integration

**Дата:** 2026-11-09  
**MASTER MISSION:** IN_PROGRESS / NO-GO

### 0. Основание

Проверенный Unified PR #68:

`ba2b1cec0c2b114586afb73696e282117eede987`

Agent 8 phase135 подтвердил 21 isolated native negative test PASS.

Root сообщил 145 локальных mandatory PASS и 22 direct-target PASS.

Hosted CI на exact HEAD не завершён.

Существующие runtime и physical gates остаются закрытыми.

### 1. Решение

Разрешаю продолжать разработку одновременно с практическими проверками на физических Windows-компьютерах.

Разрешение строго ограничено:

- Read-only inventory.
- Проверкой фактических ресурсов и доступов.
- Запуском подготовленных disposable тестов в отдельных непривилегированных пользовательских процессах после подтверждения их изоляции.
- Синтетическими исследовательскими заданиями.
- Сбором журналов собственных тестовых процессов.
- Исправлением исходного кода через отдельные GitHub branches/PR.

**Не разрешаю автоматически устанавливать Windows Services, изменять production databases, ACL, Firewall, ESET, Tailscale или действующий Consul.**

Полноценное развёртывание допускается отдельными release gates.

### 2. Немедленно — LS5 readiness

ROOT должен выполнить read-only проверку LS5:

1. Host identity, OS/build.
2. Disk free space.
3. CPU/RAM.
4. Existing Windows Services.
5. PostgreSQL instances/ports.
6. Consul processes/ports.
7. SSH и Tailscale status.
8. Existing installation directories.
9. ACL потенциального disposable-каталога.
10. Запущенные Grid/Strattester/Terminan процессы.
11. Backup и rollback readiness.
12. Конфликты портов и CPU/memory budgets.

Если disposable-каталог доступен для небезопасной подмены, выбрать подходящее изолированное расположение; не ослаблять ACL.

Опубликовать `LS5-PHYSICAL-DEV-READINESS.json`.

### 3. Первый реальный Windows-пилот

После успешного readiness выполнить отдельный disposable smoke на LS5.

Использовать:

- Immutable pinned package.
- Тестовую БД/каталог.
- Синтетический BTCUSDT dataset.
- Existing Strattester target.
- Existing MetaAnalyse target.
- Local verified artifact.
- Disposable Terminan rendering.

Никаких настоящих API-запросов к бирже.

Не использовать рабочий PostgreSQL или production credentials.

Проверить:

- Запуск.
- Stop.
- Resource bounds.
- Log collection.
- Actual target execution.
- Artifact SHA256.
- Rendering.
- No unexpected filesystem changes.
- Complete cleanup собственных тестовых процессов.

Не выдавать этот запуск за distributed E2E.

### 4. Параллельный P0 — Commissioner

Agent 2 + Agent 5 + ROOT:

Реализовать one-shot native job commissioner в отдельной ветке.

Использовать:

- Single-job profile-v2.
- Все 20 полей target request.
- Native13 reference binding.
- Authenticated principal.
- Authority proof.
- Real quota admission.
- Worker/resource containment.
- Lease/fencing.
- Immutable job intent.
- Idempotency.
- UNKNOWN reconciliation.

Не создавать второй Scheduler.

Не выдавать local session capture за worker permit.

Сначала disposable Consul + synthetic worker tests.

### 5. Параллельный P0 — Storage

Agent 4 + ROOT:

Реализовать native committed publication:

- Immutable result bytes.
- Content digest.
- Authoritative revision.
- Publication receipt.
- Dataset provenance.
- Fencing.
- Reader projection.
- Crash recovery.

До подтверждённой публикации сохранять `LOCAL_UNATTESTED`.

### 6. Параллельный P0 — Terminan

Agent 6:

Реализовать authenticated scientific-result endpoint.

Проверить:

- Principal identity.
- RBAC.
- Artifact visibility.
- Provenance.
- Dataset version.
- Simulation status.
- Result digest.
- Rendering consistency.

Сначала disposable frontend/backend.

### 7. Parallel Fix Loop

Для каждого дефекта:

REPRODUCE
→ LOG
→ FAILING REGRESSION
→ FIX IN GITHUB
→ LOCAL TEST
→ HOSTED CI
→ A8 REVIEW
→ PIN ARTIFACT
→ REDEPLOY DISPOSABLE
→ RETEST.

Не менять исходники непосредственно на тестовом компьютере без GitHub commit.

Не перезапускать защищённые single-use diagnostics автоматически.

Не выполнять бесконечные GitHub Actions reruns.

### 8. CI и F26

На PR #68 hosted evidence остаётся queued.

ROOT должен:

- Зафиксировать exact run IDs.
- Проверить runner labels и job assignment.
- Исследовать причины F26.
- Не считать queued ошибкой кода.
- Не объявлять hosted PASS.
- Продолжать независимые локальные разработки.

### 9. Следующий этап — координаторы

После отдельного security admission создать disposable тестовый Consul cluster LS5/PC4/PC3.

Обязательные prerequisites:

- Verified node identities.
- mTLS.
- No conflict with existing ports/services.
- Protected storage.
- Bounded CPU/RAM/disk.
- Independent rollback.
- Approved networking.
- Proven absence of production side effects.

Без прохождения этих условий физический многоузловой тест остаётся BLOCKED.

Не выполнять разрушительные fault-injection тесты офисного кластера.

### 10. Workers

После PASS coordinator stage подключать:

PC2 → PC1 → LS7.

Для PC1/LS7 отдельная Windows 11 Home qualification.

Не переносить Windows Pro PASS на Home.

### 11. Ограничения

- Public submit: DENY.
- Real provider sends: BLOCKED.
- Real trading: PROHIBITED.
- Production migration: BLOCKED.
- Main merge: NOT AUTHORIZED.
- Tailscale removal: BLOCKED.
- Office service replacement: BLOCKED.
- Destructive fault injection: BLOCKED.

### 12. Следующий отчёт

ROOT должен вернуть:

LS5_IDENTITY:
LS5_ACL:
LS5_RESOURCE_BUDGET:
LS5_PORT_COLLISIONS:
LS5_BACKUP_READY:
DISPOSABLE_PACKAGE_SHA:
DISPOSABLE_SMOKE:
DIRECT_TARGET_RESULT:
TERMINAN_RENDER:
COMMISSIONER_IMPLEMENTATION:
SCHEDULER_ADMISSION:
STORAGE_PUBLICATION:
HOSTED_CI:
F26_STATUS:
A8_REVIEW:
NEXT_PHYSICAL_STAGE:
GO_NO_GO:

**START NOW: LS5 read-only readiness, затем безопасный disposable smoke, одновременно реализуя commissioner, Storage и Terminan.**

Не завершать MASTER MISSION на очередном отчёте NO-GO. Продолжать исправления и проверки до фактической end-to-end приёмки.