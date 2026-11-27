# LAN — единый запрос утверждения дизайна

Это конкретный пакет для существующего запроса Agent1, не новая физическая операция.

Предлагается Approach A: прикладной mTLS-транспорт между шестью enrolled узлами плюс существующий fixed read-only SSH observer. Отдельные bounded control/data queues, frame/byte/connection limits, backpressure, bounded retry, persistent cluster network/Bybit egress accounting и conservative closed fallback. Registry, node SAN identity, trust/leaf pins, source provenance и least-privilege admission остаются обязательными.

Точное содержимое и raw SHA256: current-full-feature-approval-index-v2.json и перечисленные неизменённые файлы. Full LAN package raw SHA256 f0d2eb3ccd96d263bdbedc2a2bcdd43238a542807c81e7e2531dccb9225cd7f8; frozen closed Egress profile raw16606dee585398ae6d92139ffc1cf2ed37a4d2e08759aaa08f0c3b85958b8049. Старые источники/status paragraphs сохраняются как история; текущие пояснения ниже имеют явный приоритет только для статуса.

Запрашивается разрешение на независимую реализацию и тестирование LAN/network-budget closed profile в выделенных Agent1 файлах/ветке. Предлагаемый компонентный baseb12c6c24 — исторический исходный компонент; актуальная интеграция Rootc9f3735 содержит дополнительно исправленный fail-closed provider probe. Agent1 не может переопределить его: скрипт и shared wiring вне scope.

Не предоставляются: runtime admission, physical installation, реальные provider sends, trust-store/key provisioning, изменение портов/firewall/DNS/роутера/Tailscale, merge protected branches или реальные ордера. Никаких production Code Signing сертификатов дизайн не создаёт. Изолированные TLS test fixtures не являются operational trust/publisher certificates.

Открытые технические gates сохраняются: actual native identity/key/IPC admission; exact Control multiplex ABI; actual sole-authority transaction/proof adapters; Bybit provider-time policy/shared NAT accounting/paused-sender containment; owned commissioning/installer/rollback; Windows/hosted/physical qualification. Approval не заменяет их фиктивными providers/clock/booleans и не разрешает несовместимые shared contracts. До этого product runtime закрыт.

Основание для отдельного утверждения — прямые сообщения владельца в Agent1 chat01a1b15d-1ac2-7742-ae74-cc5a482d717b:
- BASE BRANCH DECISION, turn01a1b160-677e-74a3-bd59-2811a79bcd1a: «Передай design document главному Integration Owner и мне на утверждение, соблюдая установленный brainstorming workflow.»
- LAN DESIGN REVISION3, turn01a1b16f-749a-71a1-a344-bf17a9a6a450: «Представь полный design document на утверждение перед реализацией.»

Это прямое user restriction, а не только требование SKILL. Независимые negative/simulator tests разрешены и продолжаются; отсутствие ответа не считается согласием.
