# ПРИЗМА Desktop

Desktop-приложение для попарного выбора визуальных стимулов, регистрации времени
реакции, математической обработки и экспорта отчётов. Web-версия оставлена на
следующий этап.

## Быстрый запуск для разработки

Нужны Python 3.11+, Node.js и pnpm.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev,service]"
pnpm install
pnpm desktop:dev
```

Electron сам запускает локальный Python-сервис. При первом запуске создаются
`data/prisma.sqlite`, тестовая коллекция и две учётные записи:

- администратор: `admin` / `admin123`;
- участник: `user` / `user1234`.

## Проверка и сборка

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m alembic check
pnpm desktop:typecheck
pnpm desktop:build
.\scripts\build_desktop.ps1
```

Готовый установщик появляется в
`apps/desktop/release/PRISMA-Desktop-1.0.0-Setup.exe`.

## Где что находится

- `prisma/analytics` — изолированное математическое ядро;
- `prisma/persistence` — SQLAlchemy-модели и репозитории;
- `apps/service/prisma_service` — локальный API, сценарии и отчёты;
- `packages/ui` — React/TypeScript интерфейс;
- `apps/desktop` — Electron и Windows-сборка;
- `migrations` — Alembic-миграции;
- `tests` — математические и сквозные тесты;
- `docs` — решения по формулам, архитектура и соответствие ТЗ.

Научные допущения перечислены в `docs/ANALYTICS_DECISIONS.md`, статус требований —
в `docs/TZ_COMPLIANCE.md`.
