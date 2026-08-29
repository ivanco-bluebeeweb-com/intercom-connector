# Intercom Connector — UI component plan

Источники: `ui-primitives-reference.md`, `UI_INTERFACE_STANDARD.md`, `concepts/panels.md`.
Основано на `POST_CONNECT_EXPERIENCE.md` этого приложения.

## 1. Компоненты

| Экран | Примитивы | Почему именно эти |
|---|---|---|
| Sidebar (left) | `ui.Column`(align="start") + `ui.Text`(workspace) + `ui.Divider` + navigation `ui.ListItem`(Inbox/Contacts/Campaigns) + `ui.Button`("App settings") | Без карточек по стандарту. |
| Conversation Inbox (center, `center_overlay=True`) | `ui.Stats`(Open/Waiting/Closed today) + `ui.List`(conversations: contact name, snippet, unread indicator via `ui.Badge`) | `List` с бейджем непрочитанного — стандартный inbox-паттерн живого чата. |
| Conversation Thread | Back-button + `ui.Timeline`(messages: visitor/agent/bot, время) + `ui.TextArea`(param_name="reply", label="Ответ", placeholder="Написать посетителю...") + `ui.Button`("Отправить") + `ui.Select`(assignee) | Timeline — прямое отражение живого чата в хронологии. |
| Contact 360 (боковая панель внутри Thread или отдельный overlay) | `ui.KeyValue`(email/company/plan/last seen) + `ui.TagInput`(applied tags, editable=True) + `ui.List`(past conversations) | `TagInput` — реальный примитив SDK для chips-тегов (нет отдельного Tags, см. `UI_COMPONENT_VOCABULARY.md` §4). |
| Campaign/Bot Builder | `ui.List`(campaigns, статус active/paused) + `ui.Chart`(type="line" — engagement over time) | Обзор автоматических кампаний и их эффективности. |
| Help Center Articles | `ui.DataTable`(title, views, helpful %) + `ui.Button`("Создать статью") | Управление базой знаний. |
| App Settings | `ui.Accordion`([Connections+Disconnect, Auto-assignment Rules, Webhooks CRUD]) | Централизованные настройки по стандарту. |

## 2. User flow

1. **SESSION INIT** → `__panel__intercom_sidebar` рендерит workspace + разделы,
   `auto_action` открывает Inbox с непрочитанными.
2. Inbox: List диалогов (unread Badge) → клик → `ui.Call(conversation_id=...)` →
   Conversation Thread на том же center handler.
3. Conversation Thread: Timeline сообщений + TextArea ответа снизу → Button
   "Отправить" → `ui.Call(action=send_reply)` → `refresh_panels=["intercom_thread"]`.
4. Select "Назначить" на Thread → `ui.Call(action=assign_conversation)` →
   `refresh_panels=["intercom_inbox","intercom_thread"]`.
5. Клик на имя контакта в Thread → раскрывает/открывает Contact 360 (KeyValue + Tags +
   List past conversations).
6. Раздел "Campaigns" → List кампаний → клик → Chart engagement конкретной кампании.
7. Раздел "Help Center" → DataTable статей → "Создать статью" → Form overlay
   (TextInput title, TextArea content).
8. "App settings" → Accordion: Connections, Auto-assignment Rules, Webhooks.

## 3. Конкретные экраны (screens)

### Screen: Inbox (`intercom_inbox`, default)
- Stats row: `Open`, `Waiting`, `Closed today`.
- List диалогов: contact name, snippet последнего сообщения, unread Badge, time.

### Screen: Conversation Thread (`intercom_inbox` + `conversation_id`)
- Back-button "← К диалогам".
- Timeline сообщений (visitor слева, agent/bot справа — визуально различимы).
- Панель контакта сбоку: KeyValue (email/plan/last seen), Tags.
- Внизу: TextArea "Ответ" (placeholder "Написать посетителю..."), Select "Назначить",
  Button "Отправить".

### Screen: Campaigns (`intercom_campaigns`)
- List кампаний со статусом (Badge active/paused).
- Клик → Chart (line): engagement за последние 30 дней.

### Screen: Help Center (`intercom_help_center`)
- Button "Создать статью" вверху.
- DataTable: title, views, helpful % — row-click → редактор статьи (TextArea).

### Screen: App settings (`intercom_settings`)
- Accordion "Подключение": workspace, Rotate/Disconnect (Dialog-подтверждение).
- Accordion "Автоназначение": правила (List + Form добавления правила).
- Accordion "Webhooks": List + Button "Добавить".
