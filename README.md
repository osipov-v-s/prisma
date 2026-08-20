# ПРИЗМА Desktop

Desktop-приложение для попарного выбора изображений, регистрации времени реакции,
математической обработки и экспорта PDF/XLSX.

В версии 2.0 нет локального web-сервера: React вызывает Electron IPC, а Electron
передаёт запросы одному Python worker через stdin/stdout. Математическое ядро
остаётся изолированным и не дублируется в TypeScript.

## Запуск для разработки и отладки

### 1. Установите инструменты

Нужны:

- Python 3.11 или новее;
- Node.js 22 или новее;
- pnpm 11.19;
- Git — только если проект получается через репозиторий.

После установки Python и Node.js откройте PowerShell и проверьте версии:

```powershell
python --version
node --version
corepack enable
corepack prepare pnpm@11.19.0 --activate
pnpm --version
```

### 2. Подготовьте проект

Перейдите в корень проекта, затем создайте виртуальное окружение и скачайте
Python/Node.js-зависимости:

```powershell
cd D:\PRISMA
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev,desktop-build]"
pnpm install
```

### 3. Запустите Desktop в режиме разработки

```powershell
pnpm desktop:dev
```

Vite автоматически обновляет React-интерфейс. Логи Electron и Python-worker
показываются в запустившем команду терминале. Инструменты разработчика Chromium
открываются через `Ctrl+Shift+I` или меню `View → Toggle Developer Tools`.

Для изолированной от установленного приложения тестовой базы задайте отдельную
папку перед запуском:

```powershell
$env:PRISMA_DATA_ROOT = "$PWD\.dev-data"
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
pnpm --filter @prisma/desktop smoke
pnpm --filter @prisma/desktop smoke:runner
```

## Сборка приложения

Одна команда работает на текущей платформе:

```powershell
.\.venv\Scripts\python.exe scripts\build.py
```

Windows-установщик создаётся в `src/desktop/release/`.

## Если приложение не подключается

Надпись «Подключение к сервису» означает, что окно ещё не получило ответ от
локального Python-worker. Начиная с версии 2.0.1 вместо бесконечного ожидания
показывается причина ошибки, а технический журнал сохраняется в
`%APPDATA%\@prisma\desktop\data\worker.log`.

Ошибки React, загрузки изображений, preload и Electron записываются отдельно в
`%APPDATA%\@prisma\desktop\data\desktop.log`. `worker.log` содержит только
сообщения Python, поэтому ошибки интерфейса в нём не появляются.

В режиме разработки Electron использует отдельный каталог:
`%APPDATA%\Electron\data`. В нём находятся dev-версии `desktop.log`,
`worker.log` и `prisma.sqlite`. Если перед запуском задан `PRISMA_DATA_ROOT`,
все три файла находятся в указанном каталоге.

После установки новой версии полностью закройте старое окно ПРИЗМА и запустите
приложение снова. Пользовательская SQLite-база при обновлении сохраняется.

## Структура

- `prisma/analytics` — изолированное научное ядро и его модели;
- `src/core` — общие dataclass-модели приложения;
- `src/db` — простой `sqlite3` и SQL-миграции;
- `src/service` — auth, коллекции, эксперименты и отчёты;
- `src/worker.py` — JSON-lines bridge для Electron;
- `src/desktop` — Electron main/preload и renderer entry;
- `packages/ui` — React-компоненты, страницы и стили;
- `tests` — тесты ядра, сервисов, миграции и worker-протокола.

Существующая `prisma.sqlite` переносится автоматически: таблицы и данные не
пересоздаются. Подробнее: `docs/REFACTORING_DECISIONS.md`.

Математический baseline сверяется с `Попарное сравнение.xlsx` и
`Входящие данные и их отбор.xlsx`. Формулы, правила уровней, допущения и
обнаруженная опечатка исходной таблицы описаны в
`docs/ANALYTICS_DECISIONS.md` и `docs/ANALYTICS_EXAMPLE.md`.
