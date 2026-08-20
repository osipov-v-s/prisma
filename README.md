# ПРИЗМА Desktop

Desktop-приложение для попарного выбора изображений, регистрации времени реакции,
математической обработки и экспорта PDF/XLSX.

В версии 2.0 нет локального web-сервера: React вызывает Electron IPC, а Electron
передаёт запросы одному Python worker через stdin/stdout. Математическое ядро
остаётся изолированным и не дублируется в TypeScript.

## Запуск для разработки

Нужны Python 3.11+, Node.js и pnpm.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev,desktop-build]"
pnpm install
pnpm desktop:dev
```

При первом запуске автоматически создаются SQLite-база, SQL-схема, демонстрационная
коллекция и две учётные записи:

- `admin` / `admin123`;
- `user` / `user1234`.

## Проверка

```powershell
.\.venv\Scripts\python.exe -m pytest -q
pnpm desktop:typecheck
pnpm desktop:build
```

## Сборка приложения

Одна команда работает на текущей платформе:

```powershell
.\.venv\Scripts\python.exe scripts\build.py
```

Windows-установщик создаётся в `src/desktop/release/`.

## Структура

- `prisma/analytics` — неизменяемое научное ядро;
- `src/core` — общие dataclass-модели приложения;
- `src/db` — простой `sqlite3` и SQL-миграции;
- `src/service` — auth, коллекции, эксперименты и отчёты;
- `src/worker.py` — JSON-lines bridge для Electron;
- `src/desktop` — Electron main/preload и renderer entry;
- `packages/ui` — React-компоненты, страницы и стили;
- `tests` — тесты ядра, сервисов, миграции и worker-протокола.

Существующая `prisma.sqlite` переносится автоматически: таблицы и данные не
пересоздаются. Подробнее: `docs/REFACTORING_DECISIONS.md`.
