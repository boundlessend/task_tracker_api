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

- `.env.example` — **шаблон** и список нужных переменных
- `.env.dev` — **реальный** конфиг для локального запуска
- `.env.test` — **реальный** конфиг для тестов

приложение **не читает** `.env.example` напрямую.

приложение читает профиль по флагу `APP_ENV`:
- `APP_ENV=dev` → загружается `.env.dev`
- `APP_ENV=test` → загружается `.env.test`

### как пользоваться `.env.example`

если в проекте ещё нет `.env.dev` или `.env.test`, их удобно создавать на основе шаблона.

macOS / linux:

```bash
cp .env.example .env.dev
cp .env.example .env.test
```

после нужно поправить значения под нужный режим
Например:
- в `.env.dev` оставить `APP_ENV=dev`
- в `.env.test` поставить `APP_ENV=test`
- при необходимости развести порты и флаги `DEBUG`

### 4. запустить проект

основной способ:

```bash
python -m app
```

(опционально) если установлен `make`:

```bash
make run
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
pytest .
```

или, если есть `make`:

```bash
make test
```

## запуск через docker

### собрать образ

```bash
docker build -t task-tracker-api .
```

### запустить контейнер напрямую

```bash
docker run --rm -p 8000:8000 \
  -e APP_ENV=dev \
  -e APP_HOST=0.0.0.0 \
  -e APP_PORT=8000 \
  task-tracker-api
```

### проверить health из контейнера

```bash
curl http://127.0.0.1:8000/health
```

ожидается:

```json
{"status":"ok","service":"Task Tracker API","env":"dev","debug":false}
```

## docker compose

### поднять приложение одной командой

```bash
docker compose up --build
```

### запустить в фоне

```bash
docker compose up -d --build
```

### посмотреть логи

```bash
docker compose logs -f app
```

### остановить проект

```bash
docker compose down
```

### пересобрать образ без кеша

```bash
docker compose build --no-cache
```

### проверить health после запуска

```bash
curl http://127.0.0.1:8000/health
```

### тесты через тот же compose-файл

```bash
docker compose --profile test run --rm tests
```
