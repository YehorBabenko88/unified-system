# MASTER CODEX — STORAGE CHECKPOINT V3 DECISION

**Выбор: OPTION 1 — APPROVED.**

Утверждаю новый формат checkpoint:

- `committed_at_utc: null`
- `commit_time_status: UNKNOWN_COMMIT_INSTANT`
- Отдельное достоверное время наблюдения подтверждённой записи.

## Обязательные условия

1. Не подменять consensus commit time временем наблюдения, получения ACK или локальными часами worker.
2. `UNKNOWN_COMMIT_INSTANT` означает только отсутствие достоверного точного времени commit. Это не должно автоматически означать, что commit не состоялся.
3. Факт commit подтверждать независимо: через authoritative committed revision, commit identity и проверяемое evidence.
4. Время наблюдения хранить в отдельном поле с явно определённым источником и семантикой, например `confirmed_observed_at_utc`.
5. Если факт commit не подтверждён, использовать отдельный статус `COMMIT_UNCONFIRMED` или согласованный эквивалент. Не выдавать такую запись за committed.
6. Сохранить обратную совместимость со старым форматом checkpoint. Не изменять его семантику задним числом.
7. Определить canonical encoding для `null`, timestamps, status и evidence references.
8. Добавить regression tests:
   - Commit подтверждён, точное время неизвестно.
   - Commit не подтверждён.
   - Позднее наблюдение подтверждённой записи.
   - Повторное наблюдение.
   - Crash/restart.
   - Повторная загрузка checkpoint.
   - Несовместимая версия схемы.
   - Stale worker и fencing.
9. Не использовать timestamp как замену revision, fencing token или authority verification.

## Разрешение

DESIGN_DECISION: APPROVED

CHECKPOINT_V3_TIME_SEMANTICS: APPROVED

RUNTIME_DEPLOYMENT: NOT_AUTHORIZED_BY_THIS_DECISION

PHYSICAL_INSTALLATION: NOT_AUTHORIZED_BY_THIS_DECISION

FULL_SYSTEM_ACCEPTANCE: PENDING

Продолжай реализацию в рамках ранее утверждённого scope и согласованных контрактов. Передай обновлённую спецификацию Agent 3, Agent 4, Agent 5 и Integration Owner.
