# Intercom Connector — Preparation

**Статус:** Фаза 1-2 (Discovery + архитектурные решения) завершены. Влад
заявил объём разработки прямым поручением 2026-08-23 — «разработай это
приложение в максимальной форме со всеми доступными функциями с их
стороны и всеми возможными функциями внутри нашего приложения для
повышения эффективности» — что закрывает Шаг 5
`CONNECTOR_DISCOVERY_STANDARD.md` (объём = Ярус 1+2+3, без
дополнительного запроса подтверждения).

**Владелец продукта:** vlad@bluebeeweb.com
**Дата подготовки:** 2026-08-23, v0.1
**Vikunja task:** #2308 (BBW Imperal Apps), `[App Development] Intercom Connector`, оформлена по образцу задач #2149 (Tray.ai) и #2143 (Pipedream).

**Почему сейчас:** Intercom — рыночный лидер customer messaging /
support platform, прямой конкурент HubSpot Service Hub / Zendesk.
Портфель Imperal уже покрывает CRM/CS (HubSpot, Salesforce, Follow Up
Boss, Buildium/Yardi для вертикали недвижимости), но не имеет ни одного
коннектора к вертикали «customer messaging + AI support agent» —
Intercom закрывает эту нишу первым, включая доступ к Fin (AI-агенту).

---

## 1. Паспорт приложения

**Название в Marketplace (display_name): «Intercom»**. Внутренний
app_id/папка: `intercom-connector`.

**Intercom Connector** — коннектор к Intercom REST API v2.16
(контакты, компании, разговоры, тикеты, статьи/Help Center, News,
сообщения, теги/сегменты, data attributes/events, admin/team, Fin Agent
API, AI Content/external pages, Data Export) плюс входящие вебхуки.
BYOK: пользователь подключает свой собственный Intercom-workspace через
Access Token своего приватного приложения (Developer Hub). Imperal
ничего не хостит и не проксирует помимо самого запроса.

---

## 2. Ключевые факты об Intercom API (см. `CONNECTOR_DISCOVERY.md`)

### 2.1 Одна REST-поверхность, но региональный базовый URL

В отличие от PagerDuty (4 поверхности) Intercom — одна REST API
(`api.intercom.io`), но её **базовый хост меняется по региону хостинга
данных workspace**: `api.intercom.io` (US, по умолчанию), `api.eu.intercom.io`
(EU), `api.au.intercom.io` (AU). Неверный хост для чужого региона либо
не отвечает, либо возвращает ошибку авторизации, которая выглядит как
неверный токен — критично не перепутать. `connect_intercom` поэтому
явно спрашивает регион (или по умолчанию пробует US, затем даёт понятную
ошибку с подсказкой сменить регион, если он и правда другой).

### 2.2 Access Token vs OAuth — Access Token наш путь

Access Token выдаётся сразу при создании приватного приложения в
Developer Hub (Configure → Authentication), без review со стороны
Intercom. Подходит один-в-один под нашу модель (пользователь читает
СВОИ данные). OAuth нужен только публичным Marketplace-приложениям,
которые лезут в ЧУЖИЕ workspace — не наш случай, значит по авторизации
публикационных блокеров быть не должно.

### 2.3 Вебхуки настраиваются ТОЛЬКО через Developer Hub UI, не через API

В отличие от Shopify/HubSpot/Stripe/PagerDuty (где вебхуки создаются
REST-вызовом), Intercom не даёт API для создания webhook subscription —
это делается вручную в Developer Hub конкретного приложения (Configure →
Webhooks), подписка привязана к App, а не к одному workspace. Коннектор
не может предложить `create_webhook`; вместо этого даёт `get_webhook_setup_instructions`
(инструкция) и `verify_webhook_signature` (валидация уже настроенного
вебхука на входе) — честно отражая ограничение самого сервиса, а не
коннектора.

### 2.4 Rate limits: 10 000/мин на приложение, 25 000/мин на workspace, окна по 10 сек

Подтверждено (`developers.intercom.com/docs/references/rest-api/errors/rate-limiting`,
2026-08-23): и приватные, и публичные приложения по умолчанию — 10 000
запросов/минуту на приложение и 25 000/минуту на workspace, честно
распределённые по 10-секундным окнам (166 запросов/10 сек при лимите
1000/мин — пример из доков; конкретные цифры видны в заголовках
`X-RateLimit-*` каждого ответа). Клиент коннектора обязан читать эти
заголовки и явно поднимать типизированную ошибку на 429, а не тихо
падать.

### 2.5 Fin Agent API — отдельная, более новая поверхность с ограниченным доступом

`/fin/start` и `/fin/reply` (API 2.14+) позволяют программно вести
диалог с Fin вне обычного Messenger-виджета — например, встроить Fin в
свой собственный канал. Официально доступ **запрашивается отдельной
формой** (`developers.intercom.com/docs/guides/fin-agent-api/setup`) —
это ограничение на стороне Intercom, не коннектора; реализуем функции
полностью, но честно предупреждаем в описании, что аккаунту может
понадобиться отдельный approval от Intercom.

### 2.6 `*.deleted` webhook топики шлют минимальный payload

Зафиксировано для точного описания входящих обработчиков: топики вида
`contact.deleted`/`company.deleted` и т.п. присылают только
идентифицирующие поля, не полный объект — не путать с обычным payload.

---

## 3. Архитектурное решение — BYOK, один Access Token + сохранённый регион

**WHY BYOK**, как и все connector-приложения портфеля
(Shopify/HubSpot/Salesforce/PagerDuty/Stripe и т.д.): Intercom-workspace
— собственность пользователя, Imperal не централизует доступ к чужой
базе клиентов/переписке.

**WHY ОДИН ACCESS TOKEN + ЯВНОЕ ПОЛЕ РЕГИОНА, А НЕ ГЕНЕРИК "API KEY"
БЕЗ КОНТЕКСТА.** В отличие от PagerDuty (два типа credentials) у
Intercom один тип секрета — Access Token, но забыть про регион означает
рабочий, на первый взгляд корректный коннект, который тихо шлёт запросы
не в тот дата-центр. `connect_intercom` поэтому принимает Access Token
**и** `region` (`us`/`eu`/`au`, по умолчанию `us`) как два равноправных
обязательных для явного выбора поля, проверяет токен вызовом `GET /me`
на выбранном базовом URL и хранит оба значения вместе в одном секрете
(JSON: `{"token": ..., "region": ...}`), одной connection на аккаунт.

**WHY НЕТ `create_webhook`/`delete_webhook` (в отличие от большинства
коннекторов портфеля).** Смоделировано честно по факту устройства
сервиса (см. §2.3) — вместо CRUD вебхуков даём `get_webhook_setup_instructions`
(куда именно в Developer Hub идти и что выбрать) плюс
`verify_webhook_signature` для уже настроенного пользователем вебхука.

**WHY FIN AGENT API — ОТДЕЛЬНЫЙ МОДУЛЬ ФУНКЦИЙ, НЕ СМЕШАН С
CONVERSATIONS.** `/fin/start`/`/fin/reply` физически не относятся к
Conversations API (другой контракт запроса/ответа, ограниченный
доступ) — реализованы в `handlers_fin.py`, отдельно от
`handlers_conversations.py`, по аналогии с тем, как PagerDuty разделяет
Events API v2 и Incidents.

---

## 4. Объём релиза — Ярус 1+2+3 (максимум, по прямому поручению)

См. `CONNECTOR_DISCOVERY.md` §3-5 для полного постатейного списка.
Итого ориентировочно ~95-110 функций, разбитых по доменам: connection,
contacts, companies, conversations (+ parts/tags/notes/customer info),
tickets + ticket types + ticket states, articles/help center
(collections/sections), news, messages (in-app/email), admins/teams/away
status, data attributes, data events, segments, tags, subscription
types, calls, visitors, AI content (external pages/content import
sources), Fin Agent API, Data Export + Reporting Data Export, jobs,
брендинг, а также Ярус 3 value-add: audit_inbox_health, get_sla_breach_report,
get_unanswered_conversations_report, bulk_tag_contacts,
bulk_reply_conversations, verify_webhook_signature,
get_webhook_setup_instructions.

---

## 5. Что НЕ делаем (явные границы, см. `CONNECTOR_DISCOVERY.md` §6)

- Не строим `create_webhook`/`update_webhook`/`delete_webhook` — у
  Intercom нет публичного write-API для этого (см. §2.3); коннектор
  даёт инструкцию + верификацию подписи вместо иллюзии полного CRUD.
- Fin Agent API реализуется полностью, но с честным предупреждением про
  отдельный approval-процесс со стороны Intercom (не наше ограничение).
- Messenger-виджет / клиентская установка на сайт (JS SDK) — вне
  скоупа: это фронтенд-интеграция стороннего продукта, не
  серверный REST-функционал, который можно выразить MCP-инструментом.

---

## 6. UI (Фаза 3, см. `UI_INTERFACE_STANDARD.md`)

- Единая кнопка "App settings" в левом сайдбаре (последний элемент).
- Форма подключения (`connect_intercom`) — растянута на всю ширину
  сайдбара, поля с лейربами и контекстными placeholder'ами (Access
  Token, регион — селектор US/EU/AU, опциональный label) — без
  карточной обёртки, `ui.Stack` + `ui.Divider` между секциями.
- Инструкция по кнопке/форме — только в модалке-подсказке, не
  дублируется в сайдбаре (включая инструкцию по настройке вебхука в
  Developer Hub — она тоже только в модалке, не повторяется в сайдбаре).
