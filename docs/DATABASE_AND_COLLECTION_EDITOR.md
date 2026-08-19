# SQLite и редактор коллекций ПРИЗМА

## Хранилище

Прототип использует:

- SQLAlchemy 2;
- Alembic;
- SQLite `data/prisma.sqlite`;
- файловое хранилище `data/collections/<collection_id>/`.

Адрес БД можно заменить переменной `PRISMA_DATABASE_URL`. ORM-модели не
используют SQLite-специфические типы, поэтому тот же слой рассчитан на будущий
PostgreSQL.

## Таблицы

```text
collections
    id, name, width, depth, is_active
    time_mode, time_limit_ms
    created_at, updated_at

stimulus_types
    id, name

collection_types
    collection_id, type_id, row_index

collection_items
    collection_id, type_id, level_index
    image_path, created_at
```

Уникальные ограничения не позволяют повторить строку типа внутри коллекции или
создать два изображения одного типа на одном уровне.

## Миграции и seed

При старте FastAPI:

1. выполняется `alembic upgrade head`;
2. если коллекций нет, создаётся тестовая коллекция;
3. генерируются 20 нейтральных SVG-заполнителей для четырёх типов и пяти
   уровней.

Seed идемпотентен и не перезаписывает пользовательские данные.

## Правила редактора

Черновик:

- ширина не меньше двух;
- глубина всегда нечётная, включая черновики;
- типы и изображения разрешено заполнять постепенно;
- поддерживаются `timeout_skip`, `timeout_mark`, `no_limit`.

Активация разрешена только когда:

- глубина нечётная и не меньше пяти;
- заданы все строки типов;
- типы не повторяются;
- загружены все изображения;
- временные настройки корректны.

Любое изменение или замена изображения переводит активную коллекцию в черновик.
Это не позволяет незаметно изменить опубликованный тест без повторной проверки.

## Изображения

Поддерживаются JPEG, PNG, WebP, GIF и SVG размером до 10 МБ. В БД хранится
только относительный внутренний путь. Исходное имя файла не используется как
идентификатор.

UI поддерживает выбор файла и drag-and-drop. Перед загрузкой изображения нужно
задать тип соответствующей строки.

## API

```text
GET    /api/v1/collections
POST   /api/v1/collections
GET    /api/v1/collections/{id}
PUT    /api/v1/collections/{id}
POST   /api/v1/collections/{id}/activate
POST   /api/v1/collections/{id}/deactivate
POST   /api/v1/collections/{id}/rows/{row}/levels/{level}/image
```
