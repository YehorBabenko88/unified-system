# Consul: независимая проверка сохранённых метаданных

| Requirement ID | Repository | PR | Exact HEAD | Test name | Environment | Expected result | Actual result | Evidence link | Status | Severity | Required correction |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A8-CONSUL-METADATA-BYTES | Grid / Unified support | — | Пакет данных, не исходный commit | Seal / raw bytes / receipt consistency | A8 stdlib, offline | Все члены пакета совпадают с seal | Все9 файлов совпали по длине и SHA256 | [verification](verification.json),[seal](SHA256.original.json) | PASS scoped data | — | Не переносить на подпись или native gate |
| A8-CONSUL-CHECKSUM | Grid / Unified support | — | Consul1.22.2 metadata | Уникальные строки SHA256SUMS | Только данные | Точные archive names и хеши | Windows checksum совпал с заново хешированным существующим архивом; Linux строка совпала с ранее рассмотренным pin, сам архив в этой фазе не перечитывался | verification /checksums.txt.partial | PASS scoped comparison | — | Publisher authentication отдельно |
| A8-CONSUL-PUBLISHER | Grid / Unified support | — | Тот же пакет | Cryptographic signature /trusted signer | NOT_RUN | Квалифицированная проверка точных checksum bytes и подписанта | Подписи сохранены и побайтно равны; криптографически не проверены; ключ не импортирован и не выбран | verification /signature files /publisher-key.txt.partial | BLOCKED /NOT_RUN | Acceptance blocker | Отдельная квалифицированная signature verification и независимая привязка ключа |

Проверен seal SHA256 `0f184c96564016e1ddd1b6a2c7ef501a5820b707227323e74daa37bc1164cff9`. Оригинальные script/receipt/analysis сохранены как данные, не импортированы и не исполнены. Receipt содержит6 последовательных GET и66517 байт; каждая запись соответствует сохранённым байтам и URL. Это проверка согласованности оригиналов, не независимая инструментальная регистрация сетевой активности, TLS или скорости.

Пять HTTP200 тел точно равны записанным Content-Length, но исходные статусы `FAILED_NO_RETRY_OR_FALLBACK` и ошибка `RESPONSE_SOCKET_DEADLINE_UNAVAILABLE` сохранены. HTTP429 security page тоже сохранена; её нельзя считать успешным получением страницы безопасности. Ошибка загрузчика не воспроизводилась A8; объяснение закрытием HTTPResponse.fp остаётся анализом A2, а не новым результатом A8. Длины сами по себе не доказывают подпись или подлинность издателя.

Текст bulletin содержит заявленный fingerprint `C874011F0AB405110D02105534365D9472D7468F` и2030, но это текстовая ссылка, не самостоятельно вычисленный fingerprint ключа или проверка срока действия. Равенство generic/keyid signatures не доказывает валидность подписи. Никаких новых загрузок, GPG/native/version probes, keyring/truststore/security changes или archive execution A8 не выполнял.

RELEASE_MANIFEST_STATUS: этот пакет не утверждает release assembly.
NODE_INVENTORY_STATUS: без новой проверки.
CONTRACT_STATUS: DATA ONLY /public DENY /native permission отсутствует.
OFFLINE_TESTS: scoped raw-byte/hash/data verification PASS.
WINDOWS_CI: не проверялся в этой фазе.
PHYSICAL_TESTS: BLOCKED.
P0_P1_P2: новые source/runtime дефекты этой фазой не классифицируются; итоговый реестр не закрывается метаданными.
EVIDENCE: verification.json и сохранённые оригиналы.
NEXT_ACTIONS: отдельный qualified signature-verification review; сохранить исходные failed/429 statuses.
GO_NO_GO: NO-GO.
TAILSCALE_REMOVAL_ACCEPTANCE: BLOCKED /NO-GO.

Publication check exception: exact retained `key-update-bulletin.html.partial` contains upstream trailing whitespace. Its raw bytes and seal are preserved; only this original HTML is excluded from whitespace lint, alongside raw Git diff evidence. No source normalization is applied.
