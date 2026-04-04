# API note по задачам

## формат ошибок

Все бизнес-ошибки и ошибки валидации возвращаются в одном формате:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Запрос не прошел валидацию.",
    "details": [
      {
        "loc": ["body", "title"],
        "message": "Поле title не может быть null.",
        "type": "value_error"
      }
    ]
  }
}
```

Основные коды ошибок:
- `validation_error` — запрос не прошел валидацию
- `task_not_found` — задача не найдена
- `task_conflict` — конфликт состояния задачи
- `data_integrity_error` — нарушены ограничения данных

---

## `GET /tasks`

Возвращает список задач в согласованной форме.

### query params

- `status`: `todo | in_progress | done`
- `author_id`: `integer > 0`
- `assignee_id`: `integer > 0`
- `limit`: `integer`, по умолчанию `50`, диапазон `1..100`
- `offset`: `integer >= 0`, по умолчанию `0`
- `sort_by`: `created_at | updated_at`, по умолчанию `updated_at`
- `sort_order`: `asc | desc`, по умолчанию `desc`

### response `200 OK`

```json
{
  "items": [
    {
      "id": 12,
      "title": "Подготовить api note",
      "description": "Согласовать контракт",
      "status": "todo",
      "author_id": 1,
      "assignee_id": 2,
      "author_username": "ivan",
      "assignee_username": "anna",
      "due_date": null,
      "archived_at": null,
      "created_at": "2026-04-03T10:00:00",
      "updated_at": "2026-04-03T10:05:00",
      "comment_count": 1
    }
  ],
  "meta": {
    "limit": 50,
    "offset": 0,
    "count": 1,
    "total": 1
  }
}
```

### status codes

- `200 OK`
- `422 Unprocessable Entity`

---

## `GET /tasks/{task_id}`

Возвращает одну задачу.

### response `200 OK`

```json
{
  "id": 12,
  "title": "Подготовить api note",
  "description": "Согласовать контракт",
  "status": "todo",
  "author_id": 1,
  "assignee_id": 2,
  "author_username": "ivan",
  "assignee_username": "anna",
  "due_date": null,
  "archived_at": null,
  "created_at": "2026-04-03T10:00:00",
  "updated_at": "2026-04-03T10:05:00",
  "comment_count": 1
}
```

### status codes

- `200 OK`
- `404 Not Found`

---

## `POST /tasks`

Создает задачу.

### request body

```json
{
  "title": "Подготовить api note",
  "description": "Согласовать контракт",
  "author_id": 1,
  "assignee_id": 2,
  "status": "todo",
  "due_date": null
}
```

### response `201 Created`

Возвращается полная задача в той же схеме, что и в `GET /tasks/{task_id}`.

### status codes

- `201 Created`
- `400 Bad Request`
- `422 Unprocessable Entity`

---

## `PATCH /tasks/{task_id}`

Частично обновляет задачу.

### request body

Разрешено менять только:
- `title`
- `description`
- `due_date`

Пример:

```json
{
  "title": "Подготовить краткий api note",
  "description": null,
  "due_date": null
}
```

### точные правила `PATCH`

- если поле **не передано**, оно **не меняется**
- если `description` передан как `null`, поле **очищается**
- если `due_date` передан как `null`, поле **очищается**
- `title = null` недопустим и приводит к `422`
- менять нельзя: `id`, `author_id`, `assignee_id`, `status`, `archived_at`, `created_at`, `updated_at`, `comment_count`, `author_username`, `assignee_username`
- если в body передано запрещенное поле, запрос считается невалидным и возвращает `422`

### response `200 OK`

Возвращается полная задача в той же схеме, что и в `GET /tasks/{task_id}`.

### status codes

- `200 OK`
- `404 Not Found`
- `422 Unprocessable Entity`

---

## `POST /tasks/{task_id}/assign`

Назначает исполнителя задаче.

### request body

```json
{
  "assignee_id": 2
}
```

### response `200 OK`

Возвращается полная задача в обновленном виде.

### status codes

- `200 OK`
- `400 Bad Request`
- `404 Not Found`
- `422 Unprocessable Entity`

---

## `POST /tasks/{task_id}/comments`

Создает комментарий у задачи.

### request body

```json
{
  "author_id": 1,
  "text": "Первый комментарий"
}
```

### response `201 Created`

```json
{
  "id": 7,
  "task_id": 12,
  "author_id": 1,
  "author_username": "ivan",
  "text": "Первый комментарий",
  "created_at": "2026-04-03T10:10:00"
}
```

### status codes

- `201 Created`
- `400 Bad Request`
- `404 Not Found`
- `422 Unprocessable Entity`

---

## `GET /tasks/{task_id}/comments`

Возвращает комментарии задачи.

### response `200 OK`

```json
[
  {
    "id": 7,
    "task_id": 12,
    "author_id": 1,
    "author_username": "ivan",
    "text": "Первый комментарий",
    "created_at": "2026-04-03T10:10:00"
  }
]
```

### status codes

- `200 OK`
- `404 Not Found`

---

## `POST /tasks/{task_id}/archive`

Архивирует задачу.

### request body

Тело запроса не требуется.

### response `200 OK`

Возвращается полная задача, где `archived_at` заполнен.

### status codes

- `200 OK`
- `404 Not Found`
- `409 Conflict` — задача уже в архиве

---

## `GET /tasks/summary`

Возвращает краткую сводку по задачам.

### response `200 OK`

```json
{
  "total": 3,
  "archived": 1,
  "by_status": [
    {
      "status": "done",
      "task_count": 1
    },
    {
      "status": "in_progress",
      "task_count": 1
    },
    {
      "status": "todo",
      "task_count": 1
    }
  ]
}
```

### status codes

- `200 OK`

---

## `GET /tasks/export`

Выгружает задачи в CSV.

### query params

Поддерживает те же фильтры и сортировку, что и `GET /tasks`, кроме `limit` и `offset`.

### response `200 OK`

- `Content-Type: text/csv; charset=utf-8`
- `Content-Disposition: attachment; filename="tasks.csv"`

CSV-колонки:

```text
id,title,description,status,author_id,author_username,assignee_id,assignee_username,due_date,archived_at,created_at,updated_at,comment_count
```

### status codes

- `200 OK`
- `422 Unprocessable Entity`

---

## короткие примеры запросов

### создать задачу

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

### получить список задач

```bash
curl 'http://127.0.0.1:8000/tasks?status=todo&assignee_id=2&sort_by=updated_at&sort_order=desc'
```

### обновить задачу

```bash
curl -X PATCH http://127.0.0.1:8000/tasks/12 \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "Подготовить краткий api note",
    "description": null
  }'
```

### назначить исполнителя

```bash
curl -X POST http://127.0.0.1:8000/tasks/12/assign \
  -H 'Content-Type: application/json' \
  -d '{
    "assignee_id": 2
  }'
```

### добавить комментарий

```bash
curl -X POST http://127.0.0.1:8000/tasks/12/comments \
  -H 'Content-Type: application/json' \
  -d '{
    "author_id": 1,
    "text": "Первый комментарий"
  }'
```

### архивировать задачу

```bash
curl -X POST http://127.0.0.1:8000/tasks/12/archive
```
