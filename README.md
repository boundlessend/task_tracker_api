# Task Tracker API

## локальный запуск

### 1. клонировать репозиторий

```bash
git clone git@github.com:boundlessend/task_tracker_api.git
cd task_tracker_api
```

### 2. создать и активировать виртуальное окружение

macOS / linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. установить зависимости

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

## как устроены env-файлы

в проекте три файла с настройками:

- `.env.example` — шаблон и список нужных переменных
- `.env.dev` — локальный конфиг для разработки
- `.env.test` — конфиг для тестов

приложение читает профиль по флагу `APP_ENV`:
- `APP_ENV=dev` → загружается `.env.dev`
- `APP_ENV=test` → загружается `.env.test`

ключевые переменные для базы:

- `DATABASE_URL` — строка подключения к базе
- `DATABASE_ECHO` — печатать ли SQL в логи

## запуск PostgreSQL и миграций

### docker compose

поднять базу, применить миграции и запустить приложение:

```bash
docker compose up --build
```

после запуска будут доступны:

- `PostgreSQL` на `127.0.0.1:5432`
- API на `http://127.0.0.1:8000`

отдельные полезные команды:

```bash
docker compose up -d db
docker compose run --rm migrate
docker compose logs -f app
docker compose down
```

## как проверить что миграции применились

посмотреть текущую ревизию:

```bash
alembic current
```

посмотреть историю:

```bash
alembic history
```

проверить таблицы в базе можно так:

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
```

ожидаются таблицы:

- `alembic_version`
- `users`
- `tasks`
- `comments`
- `task_history`

## основные эндпоинты

### health

```bash
curl http://127.0.0.1:8000/health
```

### пользователи

создать пользователя:

```bash
curl -X POST http://127.0.0.1:8000/users \
  -H 'Content-Type: application/json' \
  -d '{
    "username": "misha",
    "email": "misha@example.com",
    "full_name": "Майкл Джордан"
  }'
```

### задачи

создать задачу:

```bash
curl -X POST http://127.0.0.1:8000/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "Поднять PostgreSQL",
    "description": "Добавить docker compose и миграции",
    "author_id": 1,
    "assignee_id": 1,
    "status": "todo"
  }'
```

получить список задач с фильтрами и сортировкой:

```bash
curl 'http://127.0.0.1:8000/tasks?status=todo&assignee_id=1&sort_by=updated_at&sort_order=desc'
```

поиск по задачам:

```bash
curl 'http://127.0.0.1:8000/tasks/search?q=миграц'
```

сводка по статусам:

```bash
curl 'http://127.0.0.1:8000/tasks/summary/statuses'
```

обновить статус задачи:

```bash
curl -X PATCH http://127.0.0.1:8000/tasks/1/status \
  -H 'Content-Type: application/json' \
  -d '{
    "status": "done",
    "changed_by_user_id": 1
  }'
```

### комментарии

создать комментарий:

```bash
curl -X POST http://127.0.0.1:8000/comments \
  -H 'Content-Type: application/json' \
  -d '{
    "task_id": 1,
    "author_id": 1,
    "text": "Историю изменений тоже добавим"
  }'
```

список комментариев по задаче:

```bash
curl 'http://127.0.0.1:8000/comments?task_id=1'
```

## запуск тестов

```bash
pytest .
```

или:

```bash
make test
```

тесты используют отдельную `sqlite`-базу и перед каждым запуском прогоняют миграции `Alembic`.

## структура миграций

- `0001_initial_tables` — создает `users`, `tasks`, `comments`, связи и базовые ограничения
- `0002_task_history_and_indexes` — добавляет `task_history` и индексы под реальные сценарии чтения
