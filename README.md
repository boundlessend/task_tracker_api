# Task Tracker API

## локальный запуск

### 1. клонировать репозиторий

```bash
git clone git@github.com:boundlessend/task_tracker_api.git
cd task-tracker-api
```

### 2. создать и активировать виртуальное окружение

```bash
python -m venv venv
source venv/bin/activate
```

### 3. установить зависимости

```bash
py tasks.py install
```

### 4. запустить проект

```bash
py tasks.py run
```

после старта сервис будет тут:

```text
http://127.0.0.1:8000
```

## проверка health-эндпоинта

```bash
curl http://127.0.0.1:8000/health
```

ожидается:

```json
{"status":"ok","service":"Task Tracker API","env":"dev","debug":true}
```

## запуск тестов

```bash
py tasks.py test
```
