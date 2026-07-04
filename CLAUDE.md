    # CLAUDE.md

    This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

    ## Проект

    Финансовый модуль CRM холдинга ARKAND (Часть 6 ТЗ + провизорные Часть 0/core, ХОЛ-30…33 и Часть 7/overlay). Два независимых приложения: `backend/` (Django 5.2 + DRF + SQLite) и `frontend/` (React 19 + TS + Vite, FSD). Язык проекта — русский (комментарии, тесты, коммуникация).

    ## Команды

    ```powershell
    .\start.ps1                     # всё сразу: venv, миграции, seed, оба сервера

    # Backend (из backend/, python = .venv\Scripts\python.exe)
    .venv\Scripts\python.exe manage.py runserver        # API на 127.0.0.1:8000
    .venv\Scripts\python.exe manage.py seed_demo        # демо-данные (только на пустую БД)
    .venv\Scripts\python.exe -m pytest                  # все тесты + coverage (fail-under 85%)
    .venv\Scripts\python.exe -m pytest apps/finance/tests/test_api.py --no-cov -q   # один файл
    .venv\Scripts\python.exe -m pytest apps/cash -k limit --no-cov                  # по маске

    # Frontend (из frontend/)
    npm run dev          # Vite на 127.0.0.1:5173, /api проксируется на :8000
    npm run test         # Vitest (компонентные, MSW)
    npx vitest run src/widgets/tx-table   # один файл/каталог
    npm run test:e2e     # Playwright: сам мигрирует+сидит e2e.sqlite3 и поднимает оба сервера
    npx tsc --noEmit -p tsconfig.app.json # typecheck (НЕ tsc -b в параллельных агентах — гонка tsbuildinfo)
    ```

    Частичные прогоны pytest — всегда с `--no-cov` (иначе валится порог покрытия из pytest.ini).

    Демо-пользователи: пароль у всех `arkand2026`; `nigina@arkand.tj` (главбух), `firuz@`/`manizha@` (бухгалтеры), `jamshed@`/`farrukh@`/`sino@`/`dilnoza@` (кассиры своих касс), `owner@`/`umed@` (владельцы), `admin@` (superuser).

    ## Архитектура backend

    Модульный монолит со строгим сервисным слоем. В каждом app: `models.py` (только структура), `selectors.py` (только чтение), `services.py` (**единственное место записи в БД**), тонкие `views.py`/`serializers.py`. Бизнес-логика во views/serializers — нарушение архитектуры.

    Инварианты денег (обязательны, проверяются тестами):
    - Деньги только `DecimalField(14,2)`; в JSON — строкой с ровно 2 знаками. SQLite теряет масштаб у `Sum()` — любой денежный агрегат перед выдачей пропускать через `apps/core/money.py::q2()`.
    - Каждая денежная мутация: `transaction.atomic()` + запись в `AuditLog.record()` (apps/audit).
    - Идемпотентность — условный `UPDATE` по статусу (`.filter(status=...).update(...)` с проверкой rowcount → `ConflictError`), НЕ `select_for_update` (на SQLite не работает).
    - Финансовые записи не удаляются физически — soft-delete (`is_deleted`).

    Сквозные механизмы:
    - **RBAC data-driven** (`apps/core/rbac.py`): права — строковые коды (`finance.manage`, `cash.view_all`, `overlay.view`…); матрица «роль → права» в `DEFAULT_ROLE_PERMISSIONS`, строки `RolePermission` в БД перекрывают её. DRF-классы в `apps/core/permissions.py` — тонкие обёртки над кодами. Фронтенд получает список прав через `/api/v1/me`.
    - **Изоляция КАС-04** — на уровне queryset в selectors (`accessible_businesses(user)`, `registers_for_user(user)`), а не только в permissions: «чужое» физически не попадает в ответ.
    - **Правила холдинга ХОЛ-30…33** — только в `apps/settlements/holding_rules.py` (порог owner-approval, неттинг, бартер, просрочка). Это предварительные допущения (`# TODO`), менять правило = менять конфиг. Сервисы читают правила исключительно оттуда.
    - **overlay** (Часть 7) — read-only поверх селекторов `apps/reports` (логику не дублировать), доступ только `overlay.view` (по умолчанию — только owner, даже главбуху 403). Контракт экспорта версионируется (`EXPORT_FORMAT`/`EXPORT_VERSION` в apps/overlay/views.py).
    - Единый формат ошибок API `{code, message, details}` — `apps/core/exceptions.py` (DomainError-иерархия + exception handler). Новые доменные ошибки наследовать от `DomainError`.
    - `seed_demo` (apps/core/management) зовёт те же сервисы, что и API, с фиксированным seed — данные проходят инварианты и аудит. E2E зависит от конкретных сидированных сущностей (суммы 6 000/75 000, «Касса Проект-Бюро» ~88% лимита, просроченный долг и т.п.) — меняя сидер, проверяй `frontend/e2e/`.

    Тестовая инфраструктура: фикстуры в `backend/conftest.py`, фабрики в `apps/testing/factories.py`. Тестовая БД — SQLite in-memory, параллельные прогоны безопасны.

    ## Архитектура frontend

    FSD: `app → pages → widgets → features → entities → shared`, импорты только вниз, слайсы одного слоя друг друга не импортируют. Alias `@/` → `src/`.

    - Все API-хуки (TanStack Query) уже в `entities/*` — новые запросы добавлять туда, страницы ходят только через них.
    - Цвета — только CSS-переменные из `shared/config/tokens.css`; hex в компонентах запрещён. Деньги: `--money-in`/`--money-out`/`--money-zero`, бренд-вишнёвый для денег не используется. Светлая схема принудительно (`color-scheme: only light` — не убирать, иначе браузерное авто-затемнение ломает вид).
    - Деньги в UI — только `<Money>` / `formatMoney` (`shared/lib/money.ts`); статусы — `<StatusBadge>`; строчные действия — `<IconButton>` (aria-label обязателен). Иконки только lucide-react.
    - Все строки — через i18next; словари `shared/lib/i18n/{ru,tj}.json` держать синхронными по ключам.
    - Компонентные тесты: `renderWithProviders` из `shared/test/render.tsx` + MSW v2 (`server.use(http.get(...))`), сервер в `shared/test/msw.ts`. Intl ru-RU вставляет NBSP в числа — в ассертах нормализовать пробелы.
    - Vite привязан к `127.0.0.1` (vite.config) — на этой машине `localhost` резолвится в `::1`; не убирать host.

    ## E2E (Playwright)

    `playwright.config.ts`: два webServer (Django на e2e.sqlite3 через env `ARKAND_DB_NAME` + Vite), `e2e/global-setup.ts` пересоздаёт базу и сидит заново на каждый прогон. `workers: 1`, `retries: 0` — сценарии мутируют данные, повторы дают ложные падения. Логин в тестах — через UI-хелпер `e2e/helpers.ts`.

    ## Известные особенности

    - `backend/requirements.txt` запинен через `pip freeze` (UTF-16 BOM — pip читает нормально).
    - Python в системе только 3.14 → Django зафиксирован на 5.2.x (LTS с поддержкой 3.14).
    - Логотип: положить `arkand_logo.png` в `frontend/src/shared/assets/brand/` — `BrandLogo` подхватит его автоматически через `import.meta.glob`; сейчас используется SVG-плейсхолдер.
    - Celery/Redis сознательно не вводятся (ТЗ): тяжёлые расчёты синхронно в services.
