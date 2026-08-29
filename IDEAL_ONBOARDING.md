# Intercom Connector — идеальный первый запуск

Источник: `ONBOARDING_FIRST_LAUNCH_STANDARD.md`. Целевой пользователь: Head of
Support/Growth в SaaS-компании на Intercom.

## 1. Credential type
API key (private-app Access Token, одно поле).

## 2. Идеальный флоу
1. **Первое открытие** — `Empty` со ссылкой "Settings > Developer Hub > Your app >
   Access Token" + объяснение, что нужно сначала создать private app внутри Intercom.
2. **Форма** — access_token (password-type) с лейблом.
3. **После успеха** — `audit_workspace_health` сразу: открытые разговоры/среднее время
   ответа — актуально для Head of Support, отслеживающего SLA команды.
4. **Fin AI Agent context** — если в аккаунте активен Fin (AI-агент Intercom) —
   идеально: явный индикатор его статуса/использования на первом экране, т.к. это
   отдельная, важная для этой аудитории фича.
5. **Ошибка "token revoked"** — конкретное сообщение, если приложение удалено/токен
   отозван в Developer Hub.

## 3. Разница с реализацией сейчас
См. `UI_COMPONENT_PLAN.md` §0.
