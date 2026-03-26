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

win powershell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
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

win powershell:

```powershell
Copy-Item .env.example .env.dev
Copy-Item .env.example .env.test
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