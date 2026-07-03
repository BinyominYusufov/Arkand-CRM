# ARKAND · Финансовый модуль (Часть 6 + Часть 0/7 провизорно)

CRM-экосистема холдинга ARKAND: финансовый отдел — приходы/расходы, кассы с
лимитами, взаиморасчёты и долги, зарплата, сводные отчёты, консолидация владельцев.

**Стек:** Django 5.2 + DRF + SQLite (WAL) · React 19 + TS + Vite (FSD) ·
TanStack Query · i18next (ru/tj) · lucide-react · Recharts ·
pytest · Vitest + MSW · Playwright.

## Запуск одной командой

```powershell
.\start.ps1
```

Скрипт сам создаст venv, поставит зависимости, применит миграции, наполнит базу
демо-данными (`seed_demo`) и поднимет backend (127.0.0.1:8000) + frontend
(127.0.0.1:5173) в отдельных окнах.

### Вручную

```powershell
# backend
cd backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python manage.py migrate
.\.venv\Scripts\python manage.py seed_demo
.\.venv\Scripts\python manage.py runserver

# frontend (второй терминал)
cd frontend
npm install
npm run dev
```

## Демо-пользователи (пароль у всех: `arkand2026`)

| Email | Роль |
|---|---|
| nigina@arkand.tj | Главный бухгалтер |
| firuz@arkand.tj, manizha@arkand.tj | Бухгалтеры |
| jamshed@ / farrukh@ / sino@ / dilnoza@arkand.tj | Кассиры (каждый — своя касса) |
| owner@arkand.tj, umed@arkand.tj | Владельцы (read + approve, раздел «Холдинг») |
| rustam@arkand.tj | Менеджер (доступ к своему бизнесу) |
| admin@arkand.tj | Суперпользователь (/admin) |

## Тесты

```powershell
cd backend; .\.venv\Scripts\python.exe -m pytest      # backend: сервисы, права, API (покрытие ≥85%)
cd frontend; npm run test                             # компонентные (Vitest + RTL + MSW)
cd frontend; npm run test:e2e                         # UI/E2E (Playwright, сам поднимает всё на e2e.sqlite3)
```

## Структура

```
backend/
  config/            # settings (SQLite PRAGMA, JWT, DRF), urls
  apps/core/         # Часть 0: Holding, Business, User, роли (data-driven), BusinessAccess
  apps/accounts/     # JWT, /me (роль, права, доступные бизнесы)
  apps/finance/      # ФНС-01…04: приходы (pending→confirmed), расходы, прибыль
  apps/cash/         # КАС-01…04: кассы, лимиты, изоляция
  apps/settlements/  # БАР-01…04 + ХОЛ-30…33 (holding_rules.py — конфиг правил)
  apps/payroll/      # ЗРП-01…05: движок схем (fixed / percent / tiered flat+marginal)
  apps/reports/      # ФНС-10…13
  apps/overlay/      # Часть 7 (провизорно): owner-only консолидация + экспорт v1
  apps/audit/        # журнал действий (before/after)
frontend/
  src/app|pages|widgets|features|entities|shared   # FSD, импорты только вниз
  src/shared/config/tokens.css                     # дизайн-токены ARKAND
  src/shared/lib/i18n/{ru,tj}.json                 # локализация
  e2e/                                             # Playwright-сценарии
```

## Точки конфигурации (предварительные правила — менять здесь)

- `backend/apps/settlements/holding_rules.py` — ХОЛ-30…33: авто-долг, неттинг,
  порог одобрения владельцем, бартер, срок «просрочен». `# TODO: заменить на реальные`.
- `backend/apps/core/rbac.py` — ролевая матрица прав (data-driven, БД перекрывает дефолт).
- `frontend/src/shared/assets/brand/` — логотип: положите `arkand_logo.png`,
  компонент `BrandLogo` подхватит его автоматически (сейчас SVG-плейсхолдер).

## Замечания

- Деньги — только `Decimal(14,2)`, в JSON — строкой с 2 знаками.
- Идемпотентность денежных операций — условный `UPDATE` по статусу + unique-констрейнты
  (SQLite: `select_for_update` не используется).
- Celery/Redis не вводились: тяжёлые расчёты синхронные в `services.py` (точка расширения).
- `core` — заглушка Части 0 (`# TODO: свериться с реальной Частью 0`).
