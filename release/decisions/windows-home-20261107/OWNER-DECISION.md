# MASTER CODEX — WINDOWS 11 HOME QUALIFICATION DECISION

Выбор: OPTION 1 — APPROVED.

Разрешаю отдельную квалификацию Windows 11 Home для PC1 и LS7.
Windows 11 Pro не является обязательным требованием для всех worker-узлов.

LS5, PC4 и PC3 остаются координаторами. PC1 и LS7 — обычные worker-узлы с возможностью запуска Terminan. Не назначать им роли координаторов без отдельной проверки и утверждения.

Обязательные проверки Windows Home:
1. OpenSSH client/server и LAN-аутентификация.
2. Windows Services и автозапуск Unified.
3. Запуск приложений без постоянных административных прав.
4. mTLS и защищённое хранение ключей.
5. Named Pipe ACL и IPC.
6. Windows Firewall и совместимость с ESET.
7. Python/Node/native runtime.
8. Math/Strattester/MetaAnalyse worker execution.
9. Scheduler, checkpoint/resume и восстановление.
10. Storage access, data integrity и disk budgets.
11. Terminan UI, RBAC и Control API.
12. Recovery после restart и user logoff.
13. LAN без обязательной зависимости от Tailscale.
14. Отсутствие зависимости от Pro-only функций Windows.

Если функция требует Windows Pro — эквивалентная реализация с теми же гарантиями безопасности либо конкретная функция BLOCKED. Не ослаблять security gates.

Раздельные WINDOWS_PRO_QUALIFICATION и WINDOWS_HOME_QUALIFICATION. PC1 и LS7 проверять независимо; PASS Pro не переносить на Home. Изолированные и Windows CI-тесты до physical deployment.

Не менять редакцию Windows, не обновлять Home до Pro автоматически, не изменять системные политики, Firewall, ESET или Tailscale; не устанавливать компоненты до installation gate.

PHYSICAL_DEPLOYMENT_HOME = BLOCKED до обязательных проверок.
MASTER_MISSION = IN_PROGRESS / NO-GO.
Продолжать разработку и изолированные тесты без остановки остальных направлений.
