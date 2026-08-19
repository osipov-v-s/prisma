# Архитектура первого Desktop-прототипа ПРИЗМА

## Вертикальный сценарий

```text
Electron Desktop
    ↓ безопасный preload bridge
React/TypeScript UI
    ↓ HTTP только на 127.0.0.1
FastAPI application-service
    ↓ repositories / SQLAlchemy / SQLite
редактор коллекций и файловое хранилище
    ↓ явный mapper аналитических входных моделей
prisma.analytics
```

TypeScript не содержит математических формул. FastAPI-маршруты также не
выполняют расчёты: они проверяют HTTP-данные, вызывают application-service и
возвращают сериализуемый результат Python-ядра.

## Python application-service

```text
apps/service/prisma_service/
    main.py             создание FastAPI-приложения
    config.py           имя, версия и префикс API
    routes/             тонкие HTTP-маршруты
    models/
        base.py         общая строгая политика входных моделей
        collection.py   snapshot коллекции
        session.py      ответы и метаданные сессии
        analysis.py     настройки и верхнеуровневый запрос
    mappers/            преобразование HTTP → analytics contracts
    services/           сценарии application-service
    demo.py             детерминированные данные вертикального прототипа
    seed.py             идемпотентные тестовые данные SQLite
    storage.py          заменяемое файловое хранилище изображений
```

Модели HTTP не импортируются математическим ядром. Неизвестные поля входного
JSON отклоняются, чтобы исследовательские данные не терялись молча.

## Общий React UI

```text
packages/ui/
    src/
        api.ts
        PrismaApp.tsx
        components/
        types/
            analytics.ts
            service.ts
```

Пакет не зависит от Electron. Он получает адрес Python-сервиса через свойство
компонента, поэтому позднее может быть подключён к PRISMA Web без копирования
экранов и расчётов.

Отсутствующие официальные логотипы показаны текстовыми placeholders. Вымышленные
логотипы не создавались.

## Electron shell

```text
apps/desktop/
    electron/
        main.ts         окно и жизненный цикл Python-процесса
        preload.ts      минимальный IPC bridge
    src/main.tsx        подключение общего UI
```

Применены настройки:

- `contextIsolation=true`;
- `nodeIntegration=false`;
- `sandbox=true`;
- Python API слушает только `127.0.0.1`;
- React-код не запускает процессы и не получает прямой доступ к Node.js.

При закрытии приложения Electron завершает дочерний Python-процесс.

## Реализованный сценарий

1. Electron запускает локальный FastAPI-сервис.
2. UI проверяет `/api/v1/health` с повторными попытками во время старта.
3. Пользователь запускает демонстрационный анализ.
4. Python рассчитывает choice-only и choice+time.
5. UI показывает оба распределения, согласованность, покрытие и версию ядра.

## Границы текущего прототипа

Реализованы SQLite, миграция, seed и редактор коллекций. Пока не реализованы
авторизация, реальная процедура предъявления стимулов, измерение времени в
клиенте, отчёты и установщик Windows. Они должны добавляться отдельными
вертикальными сценариями, не изменяя формулы и не перенося их в UI.
