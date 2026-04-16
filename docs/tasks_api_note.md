# api note

## что изменилось

- задача использует связи `owner` и `assignee`
- комментарий является отдельной сущностью и хранит явную связь с автором
- чтение одной задачи возвращает связанные данные: владельца, исполнителя, комментарии и историю
- у задачи есть системные поля `created_at`, `updated_at`, `closed_at`
- для задач и комментариев используются раздельные модели создания, обновления и чтения

## формат ошибок

все бизнес-ошибки и ошибки валидации возвращаются в едином формате:

```json
{
  "error_code": "validation_error",
  "message": "запрос не прошел валидацию",
  "details": [
    {
      "location": ["body", "title"],
      "message": "поле обязательно",
      "error_type": "missing"
    }
  ]
}
```

основные коды ошибок:
- `validation_error`
- `task_not_found`
- `comment_not_found`
- `task_conflict`
- `task_already_closed`
- `data_integrity_error`

---

## `POST /tasks`

создает задачу

### request body

```json
{
  "title": "Подготовить api note",
  "description": "Согласовать контракт",
  "owner_id": "11111111-1111-4111-8111-111111111111",
  "assignee_id": "22222222-2222-4222-8222-222222222222",
  "status": "todo",
  "due_date": null
}
```

### response `201 Created`

возвращает полную задачу со связанными сущностями

---

## `GET /tasks`

возвращает список задач

все datetime-поля сериализуются в московском времени `+03:00`

### query params

- `status`: `todo | in_progress | done`
- `owner_id`: `uuid`
- `assignee_id`: `uuid`
- `limit`: `1..100`
- `offset`: `integer >= 0`
- `sort_by`: `created_at | updated_at`
- `sort_order`: `asc | desc`

### response `200 OK`

```json
{
  "items": [
    {
      "id": "33333333-3333-4333-8333-333333333333",
      "title": "Подготовить api note",
      "description": "Согласовать контракт",
      "status": "todo",
      "owner_id": "11111111-1111-4111-8111-111111111111",
      "assignee_id": "22222222-2222-4222-8222-222222222222",
      "due_date": null,
      "archived_at": null,
      "created_at": "2026-04-03T10:00:00+03:00",
      "updated_at": "2026-04-03T10:05:00+03:00",
      "closed_at": null,
      "comment_count": 1,
      "owner": {
        "id": "11111111-1111-4111-8111-111111111111",
        "username": "ivan",
        "full_name": "Ivan Ivanov"
      },
      "assignee": {
        "id": "22222222-2222-4222-8222-222222222222",
        "username": "anna",
        "full_name": "Anna Smirnova"
      }
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

---

## `GET /tasks/{task_id}`

возвращает одну задачу со связанными данными

### response `200 OK`

```json
{
  "id": "33333333-3333-4333-8333-333333333333",
  "title": "Подготовить api note",
  "description": "Согласовать контракт",
  "status": "in_progress",
  "owner_id": "11111111-1111-4111-8111-111111111111",
  "assignee_id": "22222222-2222-4222-8222-222222222222",
  "due_date": null,
  "archived_at": null,
  "created_at": "2026-04-03T10:00:00+03:00",
  "updated_at": "2026-04-03T10:05:00+03:00",
  "closed_at": null,
  "comment_count": 1,
  "owner": {
    "id": "11111111-1111-4111-8111-111111111111",
    "username": "ivan",
    "full_name": "Ivan Ivanov"
  },
  "assignee": {
    "id": "22222222-2222-4222-8222-222222222222",
    "username": "anna",
    "full_name": "Anna Smirnova"
  },
  "comments": [
    {
      "id": "44444444-4444-4444-8444-444444444444",
      "task_id": "33333333-3333-4333-8333-333333333333",
      "author_id": "11111111-1111-4111-8111-111111111111",
      "text": "Первый комментарий",
      "created_at": "2026-04-03T10:06:00+03:00",
      "updated_at": "2026-04-03T10:06:00+03:00",
      "author": {
        "id": "11111111-1111-4111-8111-111111111111",
        "username": "ivan",
        "full_name": "Ivan Ivanov"
      }
    }
  ],
  "history": [
    {
      "id": "55555555-5555-4555-8555-555555555555",
      "task_id": "33333333-3333-4333-8333-333333333333",
      "changed_by_user_id": "11111111-1111-4111-8111-111111111111",
      "action": "created",
      "old_status": null,
      "new_status": "todo",
      "comment_text": null,
      "created_at": "2026-04-03T10:00:00+03:00",
      "changed_by": {
        "id": "11111111-1111-4111-8111-111111111111",
        "username": "ivan",
        "full_name": "Ivan Ivanov"
      }
    }
  ]
}
```

---

## `PATCH /tasks/{task_id}`

частично обновляет задачу

можно менять только:
- `title`
- `description`
- `due_date`

нельзя менять:
- `id`
- `owner_id`
- `assignee_id`
- `status`
- `archived_at`
- `created_at`
- `updated_at`
- `closed_at`
- `comment_count`
- `owner`
- `assignee`
- `comments`
- `history`

---

## `POST /tasks/{task_id}/assign`

назначает исполнителя задаче

- обновляет `assignee_id`
- если задача была в `todo`, переводит ее в `in_progress`

---

## `POST /tasks/{task_id}/close`

закрывает задачу

- переводит задачу в `done`
- заполняет `closed_at`
- повторное закрытие возвращает `409`

---

## `PATCH /tasks/{task_id}/status`

меняет статус задачи

- при переводе в `done` заполняет `closed_at`
- при возврате из `done` в другой статус очищает `closed_at`
- пишет запись в `TaskHistory`

---

## `POST /tasks/{task_id}/comments`

создает комментарий у задачи

### request body

```json
{
  "author_id": "11111111-1111-4111-8111-111111111111",
  "text": "Первый комментарий"
}
```

### response `201 Created`

```json
{
  "id": "44444444-4444-4444-8444-444444444444",
  "task_id": "33333333-3333-4333-8333-333333333333",
  "author_id": "11111111-1111-4111-8111-111111111111",
  "text": "Первый комментарий",
  "created_at": "2026-04-03T10:06:00+03:00",
  "updated_at": "2026-04-03T10:06:00+03:00",
  "author": {
    "id": "11111111-1111-4111-8111-111111111111",
    "username": "ivan",
    "full_name": "Ivan Ivanov"
  }
}
```

---

## `PATCH /comments/{comment_id}`

частично обновляет комментарий

### request body

```json
{
  "text": "Обновленный комментарий"
}
```

---

## `GET /tasks/export`

выгружает csv со столбцами:

```text
id,title,description,status,owner_id,owner_username,owner_full_name,assignee_id,assignee_username,assignee_full_name,due_date,archived_at,closed_at,created_at,updated_at,comment_count
```
