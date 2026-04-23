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

по умолчанию локальный запуск использует sqlite-файл `task_tracker.db`. при первом старте приложение само создает схему и добавляет демо-данные.

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

## учебная аутентификация

логин выдает простой bearer-токен формата `stub:<username>`:

```bash
curl -X POST http://127.0.0.1:8000/auth/login   -H 'Content-Type: application/json'   -d '{"username": "ivan"}'
```

для защищенных ручек можно использовать либо `authorization: bearer stub:<username>`, либо stub-заголовок `x-auth-user: <username>`.

## примеры ручек

создать задачу:

```bash
curl -X POST http://127.0.0.1:8000/tasks   -H 'Content-Type: application/json'   -H 'x-auth-user: ivan'   -d '{
    "title": "подготовить api note",
    "description": "согласовать контракт",
    "status": "todo"
  }'
```

получить список задач:

```bash
curl 'http://127.0.0.1:8000/tasks?status=todo&sort_by=updated_at&sort_order=desc'   -H 'x-auth-user: ivan'
```

обновить задачу:

```bash
curl -X PATCH http://127.0.0.1:8000/tasks/33333333-3333-4333-8333-333333333333   -H 'Content-Type: application/json'   -H 'x-auth-user: ivan'   -d '{
    "title": "подготовить краткий api note",
    "description": null
  }'
```

назначить исполнителя:

```bash
curl -X POST http://127.0.0.1:8000/tasks/33333333-3333-4333-8333-333333333333/assign   -H 'Content-Type: application/json'   -H 'x-auth-user: ivan'   -d '{
    "assignee_id": "11111111-1111-4111-8111-111111111111"
  }'
```

добавить комментарий:

```bash
curl -X POST http://127.0.0.1:8000/tasks/33333333-3333-4333-8333-333333333333/comments   -H 'Content-Type: application/json'   -H 'x-auth-user: ivan'   -d '{
    "text": "первый комментарий"
  }'
```

получить саммари:

```bash
curl http://127.0.0.1:8000/tasks/summary -H 'x-auth-user: ivan'
```

выгрузить csv:

```bash
curl -OJ http://127.0.0.1:8000/tasks/export -H 'x-auth-user: ivan'
```
