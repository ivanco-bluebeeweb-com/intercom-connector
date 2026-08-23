# Intercom Connector — Connector Discovery

**Дата discovery:** 2026-08-23 (свежее чтение developers.intercom.com — «Intercom and Fin Developer Platform»).
**Статус:** Ярусы 1-3 пройдены. Влад заявил объём заранее прямым поручением, повторяющимся на каждый коннектор («разработай это приложение в максимальной форме со всеми доступными функциями с их стороны и всеми возможными функциями внутри нашего приложения для повышения эффективности») — по `CONNECTOR_DISCOVERY_STANDARD.md` Шаг 5 это закрывает вопрос о форме релиза без переспроса. Делаем Ярус 1+2+3.
**Vikunja task:** #2308 (BBW Imperal Apps), `[App Development] Intercom Connector`, оформлена по образцу задач #2149 (Tray.ai) и #2143 (Pipedream).

---

## 1. Целевой сервис и источники

**Intercom** — один из рыночных лидеров customer messaging / support platform (Messenger виджет, Inbox, Help Center, тикетинг), с 2024-2025 репозиционируется вокруг **Fin** — собственного AI-агента поддержки. Официальная документация сейчас называется **«Intercom and Fin Developer Platform»** (`developers.intercom.com`), актуальная версия REST API — **2.16** (auto-generated из OpenAPI, версионируется независимо от продукта). Есть открытый OpenAPI-репозиторий `github.com/intercom/Intercom-OpenAPI` (поддерживает версии API 2.7+, последнее обновление октябрь 2025).

Источники, прочитанные 2026-08-23:
- `developers.intercom.com/docs` (Overview)
- `developers.intercom.com/docs/references/introduction` — полный список категорий ресурсов
- `developers.intercom.com/docs/build-an-integration/learn-more/authentication` — Access Token vs OAuth
- `developers.intercom.com/docs/build-an-integration/learn-more/rest-apis` — базовые правила REST API
- `developers.intercom.com/docs/webhooks/setting-up-webhooks` — настройка вебхуков (только через Developer Hub UI, не API)
- `developers.intercom.com/docs/references/webhooks/webhook-models` — полный список webhook topics
- `developers.intercom.com/docs/references/rest-api/errors/rate-limiting` — лимиты
- `developers.intercom.com/docs/references/rest-api/api.intercom.io/conversations/*` — Conversations API
- `developers.intercom.com/docs/references/rest-api/api.intercom.io/tickets*`, `/ticket-types`, `/ticket-states`
- `developers.intercom.com/docs/references/rest-api/api.intercom.io/ai-content/*` — AI Content (external pages / content import sources — Fin's knowledge base)
- `developers.intercom.com/docs/references/rest-api/api.intercom.io/fin-agent` — Fin Agent API (`/fin/start`, `/fin/reply`, готовящийся `/fin/capabilities`)
- `developers.intercom.com/docs/references/rest-api/api.intercom.io/export` / `/reporting-data-export` — Data Export / Reporting Data Export
- `www.intercom.com/help/en/articles/6124430-regional-data-hosting` — региональный хостинг данных

---

## 2. Ключевые архитектурные факты

### 2.1 Авторизация — две модели, не путать
- **Access Token (Bearer)** — для приватных апп на СВОЁМ workspace. Выдаётся сразу при создании app в Developer Hub (Configure → Authentication), без review. **Это наш путь по умолчанию** — как Cin7/PagerDuty/ShipStation/Stripe: простой BYOK token-коннект, пользователь вставляет токен своего приватного Intercom-приложения.
- **OAuth** — обязателен только для ПУБЛИЧНЫХ апп в Intercom App Store, которые лезут в ЧУЖИЕ workspace (требует review со стороны Intercom). Не нужен для нашей модели (BYOK на свой аккаунт) — публикационных блокеров по авторизации быть не должно.

### 2.2 Региональный хостинг данных — критично для базового URL
Workspace может физически храниться в US / EU / Australia, и это **меняет базовый URL** запроса:
- `api.intercom.io` — US (по умолчанию)
- `api.eu.intercom.io` — EU
- `api.au.intercom.io` — Australia

Коннектор обязан хранить выбранный регион вместе с токеном (поле при `connect_intercom`), а не жёстко резолвить `api.intercom.io` — иначе EU/AU-аккаунты будут получать ошибки авторизации при формально верном токене.

### 2.3 Rate limits
- Private apps: **10,000 запросов/минуту на приложение**, **25,000/минуту на workspace** (делится между всеми приватными аппами воркспейса).
- Лимит распределяется по окнам **10 секунд** (10,000/мин → ~1666 запросов/10 сек).
- Заголовки `X-RateLimit-Limit` / `X-RateLimit-Remaining` / `X-RateLimit-Reset`; при превышении — `429`.

### 2.4 Вебхуки — НЕ создаются через REST API
В отличие от Stripe/HubSpot/Shopify (`create_webhook` через API), у Intercom **вебхуки настраиваются только вручную в Developer Hub UI** (Configure → Webhooks), привязаны к App (не к Workspace) — приложение получает события из ВСЕХ workspace, где установлено это App. Коннектор не может программно создавать/удалять webhook-подписки — только **читать статус настройки и подсказывать пользователю**, как и куда идти (аналог ограничения, которое уже встречалось у других сервисов с UI-only настройкой). Подпись вебхука — `X-Hub-Signature` (HMAC-SHA1 по `client_secret` приложения) — коннектор может **верифицировать** входящий вебхук программно, даже не создавая подписку через API.

Полный список категорий webhook topics (для документации/справки внутри приложения, не для CRUD): Admin, Article, Call, Company, Contact, Conversation, Content Stat (banner/carousel/chat/checklist/custom_bot/email/news_item/post/push/series/sms/survey/tooltip_group/tour), Event, API Activity, Jobs, Ping, Subscription (granular.subscribe/unsubscribe), Ticket, Visitor, Data Connector Execution.

### 2.5 Fin Agent API — отдельная, специальная поверхность
`/fin/start` и `/fin/reply` (API v2.14+) позволяют программно вести разговор с Fin вне обычного Messenger-виджета (например, встроить Fin в собственный кастомный канал). Требует отдельного доступа (форма запроса на developers.intercom.com/docs/guides/fin-agent-api/setup) — включаем как отдельные функции, документируя, что может требоваться дополнительное согласование доступа со стороны Intercom.

---

## 3. Карта возможностей (полный обзор ресурсов из reference-раздела)

| Ресурс | Ingress/Egress/Both | Комментарий |
|---|---|---|
| **Admins** | Ingress | Список/чтение админов (агентов), away-status |
| **Away Status Reasons** | Both | Причины статуса "недоступен" |
| **Articles** | Both | Help Center статьи: CRUD, поиск |
| **Help Center (Collections)** | Both | Коллекции статей, иерархия |
| **Internal Articles** | Both | Внутренние (не публичные) статьи для команды |
| **Brands** | Both | Множественные бренды Messenger (Multi-Brand) |
| **Calls** | Ingress | Intercom Phone — метаданные звонков, транскрипты |
| **Companies** | Both | CRUD компаний, attach/detach контактов, list users of company |
| **Contacts** | Both | CRUD контактов (users/leads), поиск, merge, archive/unarchive, list attached companies/conversations/tags/notes/segments |
| **Conversations** | Both | Список/чтение/reply/close/snooze/open/assign/attach contact/detach contact/redact/convert to ticket/list conversation parts |
| **Data Attributes** | Both | Кастомные атрибуты на Contact/Company/Conversation (создание/список/архивирование) |
| **Data Events** | Both | Отправка кастомных событий (Data Events API), список типов саммари |
| **Data Export** (content) | Egress/Ingress | Экспорт статистики контента (email/post/bot/survey/tour/series) |
| **Reporting Data Export** | Egress/Ingress | Enqueue экспорт датасета отчётности, статус job, список датасетов/атрибутов |
| **Emails** | Ingress | Чтение отправленных email-сообщений (для отчётности) |
| **Fin Agent API** | Both | `/fin/start`, `/fin/reply` — программное ведение диалога с Fin |
| **AI Content — External Pages** | Both | CRUD внешних страниц как источника знаний для Fin |
| **AI Content — Content Import Sources** | Ingress | Список/чтение источников импорта контента (интеграции типа Zendesk/Confluence) |
| **Jobs** | Ingress | Статус фоновых задач (используется export-флоу) |
| **Messages** | Egress | Отправка in-app/email сообщений админом контакту |
| **News** | Both | News Items (широковещательные объявления в продукте) — CRUD |
| **Notes** | Both | Заметки на контакте |
| **Segments** | Ingress | Список сегментов контактов (read-only, определяются в UI) |
| **Subscription Types** | Both | Типы email-подписок, подписка/отписка контакта |
| **Switch** | Egress | Отправка SMS-приглашения на переключение в Messenger (Switch API) |
| **Tags** | Both | CRUD тегов, назначение/снятие на Contact/Company/Conversation |
| **Teams** | Ingress | Список команд и их участников |
| **Ticket Type Attributes** | Both | Кастомные атрибуты типа тикета |
| **Ticket Types** | Both | CRUD типов тикетов (структура + иконка) |
| **Ticket States** | Ingress | Список состояний категории (submitted/in_progress/resolved и кастомные) |
| **Tickets** | Both | CRUD тикетов, reply, attach contact, list |
| **Visitors** | Both | Чтение/обновление анонимных посетителей (до конвертации в контакт) |
| **Webhooks (Developer Hub only)** | Ingress (только read статуса) | См. §2.4 — не CRUD через API |

---

## 4. Ярус 1 — Ключевые функции (P0-кандидаты)

`connect_intercom` (access token + регион US/EU/AU, валидация через `GET /me`), `disconnect_intercom`, `list_connections`; Contacts (list/get/create/update/archive/unarchive/delete/merge/search/list companies/list conversations/list tags/list notes); Companies (list/get/create-or-update/delete/list contacts/attach-detach contact); Conversations (list/get/reply/close/snooze/open/assign/attach-detach contact/list parts/search); Tickets (list/get/create/update/reply); Ticket Types (list/get/create/update); Articles (list/get/create/update/delete); Admins (list/get); Tags (list/create/delete/assign/remove); Notes (create/list).

## 5. Ярус 2 — Полное покрытие

| Возможность | Статус | Причина/триггер |
|---|---|---|
| Away Status Reasons CRUD | included | Полнота Admins-домена |
| Help Center Collections CRUD | included | Полное покрытие Help Center наряду с Articles |
| Internal Articles CRUD | included | Полнота Articles-домена |
| Brands (list/get) | included | Multi-Brand аккаунты — read достаточно для отчётности/UI-подсказок |
| Calls (list/get) | included | Read-only метаданные звонков — часть полного покрытия Conversations-экосистемы |
| Data Attributes CRUD | included | Настройка кастомных полей — часть "полного функционала" |
| Data Events (create/list summaries) | included | Событийная аналитика, нужна для полноты |
| Messages (create — send message) | included | Явная egress-возможность из reference |
| News Items CRUD | included | Полнота продуктовых объявлений |
| Segments (list) | included | Read-only справочник, используется в UI подсказках при поиске контактов |
| Subscription Types (list + subscribe/unsubscribe) | included | Управление email-подписками контактов |
| Switch (send) | included | SMS→Messenger переключение — отдельная egress-функция |
| Teams (list/get) | included | Справочник для назначения conversations/tickets |
| Ticket States (list) | included | Read-only справочник состояний |
| Visitors (get/update) | included | Полнота модели контактов (visitor до конвертации) |
| Data Export (content stats) | included | Отчётность по контенту |
| Reporting Data Export (enqueue/status/datasets) | included | Полноценный BI-экспорт |
| AI Content External Pages CRUD | included | Управление базой знаний Fin программно |
| AI Content Import Sources (list/get) | included | Read-only статус интеграций импорта контента |
| Fin Agent API (`/fin/start`, `/fin/reply`) | included | Явно указано в §1 — программный доступ к Fin (может требовать отдельного approval от Intercom на стороне пользователя, это не блокер для кода коннектора) |
| Webhooks CRUD через API | not applicable | Intercom не даёт API для управления webhook-подписками — только Developer Hub UI (см. §2.4) |
| OAuth-флоу для публичных апп | not applicable | Наша модель — BYOK Access Token на собственный workspace, не публичное приложение в App Store |

## 6. Ярус 3 — Функции на нашей стороне (Imperal value-add)

- **`audit_inbox_health`** — агрегированный отчёт по инбоксу: сколько разговоров открыто/не назначено/просрочено по времени первого ответа, разбивка по командам/админам — аналог `audit_account`/`audit_project_health` у других коннекторов.
- **`get_sla_breach_report`** — value-add отчёт: список разговоров, где не выдержан порог первого ответа/резолюции (SLA), т.к. у Intercom нет отдельного "готового" SLA-отчёта в REST API.
- **`bulk_tag_contacts`** — массовое назначение тега на список контактов в одном вызове (Intercom API даёт только по одному контакту за раз).
- **`bulk_reply_conversations`** — массовая рассылка одного и того же ответа/закрытия по нескольким разговорам (например, шаблонный ответ на волну похожих обращений).
- **`verify_webhook_signature`** — верификация `X-Hub-Signature` входящего вебхука (HMAC-SHA1), т.к. Intercom этого сам не проверяет за пользователя — по аналогии со Stripe Connector `verify_webhook_signature`.
- **`get_unanswered_conversations_report`** — отчёт по разговорам без ответа администратора дольше N часов — комбинация Conversations + admin reply timestamps, которой нет 1:1 в нативном API.

---

## 7. Решение по объёму этого захода

Выбрана форма релиза: **Ярус 1 + Ярус 2 + Ярус 3 (максимум)**. Основание — постоянное прямое поручение Влада, действующее на каждый новый коннектор без переспроса («Intercom - разработай это приложение в максимальной форме со всеми доступными функциями с их стороны и всеми возможными функциями внутри нашего приложения для повышения эффективности», 2026-08-23), в точности такая же формулировка уже применялась к DocuSign/Ironclad/PagerDuty/CircleCI/GitLab CI/CD/Cin7 Core/ShipStation. Подтверждено этим же прямым поручением — дополнительный вопрос не требуется по исключению из Шага 5 `CONNECTOR_DISCOVERY_STANDARD.md`.

Ожидаемый масштаб: ~90-110 функций (сопоставимо с PagerDuty ~85-95, WordPress Hub ~264) — оправдано широтой Intercom (Contacts/Companies/Conversations/Tickets/Articles/Help Center/News/Data Export/Fin Agent/Data Attributes/Events — самостоятельные крупные домены).
