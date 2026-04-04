# Task Tracker API

## установка

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

## локальный запуск

```bash
cp .env.example .env.dev
python -m app
```

Swagger UI:

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

Запустить тесты:

```bash
make test
```

Запустить все проверки:

```bash
make check
```

Остановить docker compose:

```bash
make down
```

## примеры ручек

создать задачу:

```bash
curl -X POST http://127.0.0.1:8000/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "Подготовить api note",
    "description": "Согласовать контракт",
    "author_id": 1,
    "assignee_id": 2,
    "status": "todo"
  }'
```

получить список задач:

```bash
curl 'http://127.0.0.1:8000/tasks?status=todo&assignee_id=2&sort_by=updated_at&sort_order=desc'
```

обновить задачу:

```bash
curl -X PATCH http://127.0.0.1:8000/tasks/12 \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "Подготовить краткий api note",
    "description": null
  }'
```

назначить исполнителя:

```bash
curl -X POST http://127.0.0.1:8000/tasks/12/assign \
  -H 'Content-Type: application/json' \
  -d '{
    "assignee_id": 2
  }'
```

добавить комментарий:

```bash
curl -X POST http://127.0.0.1:8000/tasks/12/comments \
  -H 'Content-Type: application/json' \
  -d '{
    "author_id": 1,
    "text": "Первый комментарий"
  }'
```

получить саммари:

```bash
curl http://127.0.0.1:8000/tasks/summary
```

выгрузить CSV:

```bash
curl -OJ http://127.0.0.1:8000/tasks/export
```
