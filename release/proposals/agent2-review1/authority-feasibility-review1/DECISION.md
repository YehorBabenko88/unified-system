# Единственный authority: границы реализуемости, review 1

Статус: OWNER_REVIEW_REQUIRED / NO-GO для управляющих mutations. Это дополнение к HA-AUTHORITY-DESIGN.md, а не разрешение изменять контракт или исходники. Единственный authority остаётся существующий Grid Consul/Raft. Физические проверки не выполнялись.

## Проверяемая база

Grid source для текущего анализа: `71084a336520187d6e260531a2f5d15555ba0e0c`, tree `f50311e41f135dc5b4cc64693872fd4831df7afe`. Это позднее исследование budget-anchor базы, а не молчаливая замена исходной design-базы Grid55 или утверждённого integration pin. Изучены `grid/coordination.py`, `grid/coordination_commands.py`, `grid/coordination_budget_anchor.py`, `grid/control_snapshot_ring.py`. Fixture PR262 не изменяет этот production code. Unified P0 PR25 — только deny-only профиль; наличие его Draft PR не означает готовность HA.

`ConsulSessionAuthority` делает consistent read и проверяет локальный monotonic deadline, затем отправляет `/txn` с check-session/check-index. Между проверкой и применением транзакции остаётся интервал произвольной длительности. `SetResearchControl` имеет атомарные command/idempotency/aggregate проверки, но не предоставляет универсальную Storage publication или HTTP Control API. Локальный snapshot ring не является глобальным commit journal.

## Доказуемое ограничение времени

Клиент проверяет lease при t=9000, deadline=10000. Процесс останавливается до send либо запрос задерживается перед применением. В t=10001 session invalidation ещё не закоммичен; KV/index/session прежние. Native KV predicates принимают транзакцию. Увеличение числа prechecks оставляет тот же последний интервал. Если invalidation закоммичен первым, check-session защищает: это гарантия порядка событий, а не строгого wall-clock deadline.

API не возвращает timestamp применения FSM. Два исполнения с apply=9900 и apply=10001 могут иметь одинаковые KV, индексы, receipt и response time=11000. Поле caller_timestamp, HTTP Date или timestamp перед RPC не различает эти исполнения и не является `committed_at`.

Термины требуют отдельного ACK: Raft majority commit и последующее FSM apply различаются. Здесь apply — момент проверки KV predicates/публикации состояния в модели; точное время majority commit модель не наблюдает. Контрпример send после deadline допускает и majority commit, и apply после deadline. Для queued-before-deadline случая не следует выводить время majority commit из apply. Контракт обязан выбрать, к какому serialization event относится deadline и committed_at; Consul HTTP KV response точного timestamp ни одного из них не предоставляет.

Основания: [native transaction predicates](https://developer.hashicorp.com/consul/api-docs/txn), [session TTL/reaping semantics](https://developer.hashicorp.com/consul/api-docs/session). Вывод о невозможности — наш анализ этих primitives, а не заявление поставщика. Приостановленный исполнитель после authorization также может позднее выполнить внешний socket send; fencing KV само по себе не останавливает уже допущенный внешней системой эффект.

`bounded_consul_api_counterexamples.py` и JSON содержат десять детерминированных случаев, включая отрицательные controls. Это модель API predicates, не реальный Consul, не тест Raft и не physical HA evidence.

## Минимальный допустимый closure протокол

Реализуемая гарантия: публикация проверяет последнюю COMMITTED eligibility, ownership и allocation. Ненаблюдаемое повреждение носителя не обнаруживается из KV: healthy и corrupt диск с одинаковым KV неразличимы.

1. Storage готовит immutable closure attestation: полный transitive manifest, object/version IDs, allocation records, digest и coverage identity. Пути и allocation IDs никогда не переиспользуются.
2. Все объекты удерживаются durable holds. GC сначала CAS AVAILABLE -> DELETING, убедившись в отсутствии holds; publication проверяет те же состояния. Сначала удалить файл и затем записать tombstone недопустимо.
3. Каждая наблюдённая LOST/corrupt/revoked eligibility атомарно увеличивает epoch соответствующего volume/instance. Publication check-index проверяет bounded vector этих epochs, closure attestation, holds, assignment/lease revisions и generation. Это устраняет неограниченную reverse fanout, но требует участия ВСЕХ mutators. Один mutator, обходящий epoch, разрушает гарантию.
4. В том же transaction publication переводит все transitive holds в committed ownership, проверяет coverage registry (включая перекрытия с другими segment IDs), переносит Storage-verified staged/quarantine allocation bytes в used и списывает reservation. Caller estimates не допускаются.
5. Closure/epoch/hold vector должен помещаться в лимиты реально закреплённой версии Consul. До измеренного bound и алгоритма отказа для oversized closure — NO-GO. Деление одной атомарной publication на независимые chunks недопустимо.

Эти шаги ещё не удовлетворяют строгому deadline: expiry predicate отсутствует. Freshness как wall-clock age наследует ту же проблему. Они не делают атомарными filesystem и KV; crash cleanup обязан сохранять holds и учитывать orphan bytes до проверенной reconciliation.

## Требуемое решение владельца

A. Сохранить строгие expiry-at-commit и настоящий committed_at. Тогда требуется отдельно квалифицированный time-aware atomic publication primitive в рамках согласованной архитектуры authority: deadline predicate и timestamp должны принадлежать одному serialization point с fencing, idempotency, closure и allocation. Нужны определение часов/uncertainty и проверяемая семантика pause/recovery. Текущий Consul KV API этого не даёт. Это запрос архитектурного решения, не разрешение создавать второй authority.

B. Отдельно утвердить изменение контракта на expiry/revocation, упорядоченные committed authority events; timestamps сообщают observation interval, а не точное время commit. Тогда Consul session/index/CAS могут реализовать изменённую гарантию. Нельзя называть этот вариант выполнением исходного strict-time контракта.

До решения A/B mutations остаются закрыты. Это временный gate, а не завершение платформы. SQL now(), reaper, sidecar, новая БД или другая KV сами по себе не доказывают A; отдельные Consul+SQL commits создают дополнительную атомарность, которую нужно доказать.

## Конкретная следующая реализация после ACK/allocation

Кандидаты additive Grid modules (пути пока НЕ выделены): `grid/control_contracts_v2.py` — typed envelopes и pinned domain schema registry; `grid/control_identity.py` — verified principal/capability provider; `grid/control_projection_v2.py` — consistent authority root, durable view journal/cursors; `grid/control_api_v2.py` — authenticated read-only routes. Точные endpoints и error ABI находятся в соседнем Control Sync v2 пакете. Подключение router и изменение blanket readiness guard принадлежат ROOT; нельзя ослаблять DCS/PG guards неявно.

Существующие `grid/coordination.py`, `grid/coordination_commands.py` и budget anchor остаются source-owner locked. Для mutable функций нужны owner-reviewed интерфейсы `publish(prepared_closure, expected_generation, expected_revisions, idempotency_key)` и `invalidate_eligibility(expected_epoch, reason, evidence_ref)` с одной atomic boundary; они НЕ являются уже существующими API. Unified `ha_authority_client.py` — клиент Grid, без собственного лидерства. Scheduler потребляет assignment/lease; Storage владеет verification/allocation/GC; Terminan отображает подтверждённый view и отдельно connection liveness. LAN transport не принимает решения authority и не подтверждает commit.

Полезная независимая работа: read-only real producer, authentication и consistent projection после exact ACK; contract fault tests, replay/cursor recovery, cache corruption tests. Успех read-only producer не открывает mutations и не заменяет Windows HA acceptance.

## Изолированная матрица проверки

* Time: pause до send, queue перед apply, invalidation до/после txn, clock uncertainty, response loss, restart. Проверять A либо явно утверждённый B.
* Closure: concurrent revoke/LOST/GC, stale eligibility index, transitive child deletion, coverage overlap, oversized attestation, concurrent allocation debit, orphan recovery.
* Producer: consistent read failure -> UNKNOWN, authenticated NO_QUORUM evidence, stale snapshot/cursor, restart journal, changed authorization view, retained replay bounds.
* Реальный Consul: 3 независимых voters LS5/PC4/PC3, 1/2 и 2/1 partitions, simultaneous restart, no forced LS5 failback, stale owner rejection, commit receipt replay. Windows/Linux CI и физический Windows quorum — отдельные обязательные evidence, сейчас NOT_RUN.

P0: strict-time primitive/contract decision; closure enforcement across all writers; authenticated producer identity/read barrier. P1: replay durability/limits, bounded closure limits, Windows qualification. P2: operational diagnostics and preferred-node presentation. GO только для review/design и согласованного read-only implementation; NO-GO для HA acceptance, deployment и mutable completion.
