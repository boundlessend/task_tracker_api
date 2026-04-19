# task tracker api

## установка

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

## локальный запуск

```bash
cp .env.example .env.dev
python -m app
```

по умолчанию локальный запуск использует sqlite-файл `task_tracker.db`. При первом старте приложение само создает схему и добавляет демо-данные.

демо-пользователи:

```text
ivan / ivan@example.com
anna / anna@example.com
```

swagger ui:

```text
http://127.0.0.1:8000/docs
```

## запуск через docker compose

```bash
docker compose up --build
```

## миграции

применить миграции:

```bash
alembic upgrade head
```

текущая ревизия:

```bash
alembic current
```

## основные команды make

установить зависимости:

```bash
make install
```

поднять приложение локально:

```bash
make run-local
```

поднять через docker compose:

```bash
make run
```

применить миграции:

```bash
make migrate
```

форматировать код:

```bash
make format
```

проверить форматирование:

```bash
make format-check
```

запустить flake8:

```bash
make lint
```

запустить тесты:

```bash
make test
```

запустить все проверки:

```bash
make check
```

остановить docker compose:

```bash
make down
```

## примеры ручек

создать задачу:

```bash
curl -X POST http://127.0.0.1:8000/tasks   -H 'Content-Type: application/json'   -d '{
    "title": "подготовить api note",
    "description": "согласовать контракт",
    "owner_id": "11111111-1111-4111-8111-111111111111",
    "assignee_id": "22222222-2222-4222-8222-222222222222",
    "status": "todo"
  }'
```

получить список задач:

```bash
curl 'http://127.0.0.1:8000/tasks?status=todo&owner_id=11111111-1111-4111-8111-111111111111&assignee_id=22222222-2222-4222-8222-222222222222&sort_by=updated_at&sort_order=desc'
```

обновить задачу:

```bash
curl -X PATCH http://127.0.0.1:8000/tasks/33333333-3333-4333-8333-333333333333   -H 'Content-Type: application/json'   -d '{
    "title": "подготовить краткий api note",
    "description": null
  }'
```

назначить исполнителя:

```bash
curl -X POST http://127.0.0.1:8000/tasks/33333333-3333-4333-8333-333333333333/assign   -H 'Content-Type: application/json'   -d '{
    "assignee_id": "22222222-2222-4222-8222-222222222222"
  }'
```

добавить комментарий:

```bash
curl -X POST http://127.0.0.1:8000/tasks/33333333-3333-4333-8333-333333333333/comments   -H 'Content-Type: application/json'   -d '{
    "author_id": "11111111-1111-4111-8111-111111111111",
    "text": "первый комментарий"
  }'
```

получить саммари:

```bash
curl http://127.0.0.1:8000/tasks/summary
```

выгрузить csv:

```bash
curl -OJ http://127.0.0.1:8000/tasks/export
```
