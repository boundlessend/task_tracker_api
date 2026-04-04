install:
	python -m pip install --upgrade pip
	python -m pip install -r requirements-dev.txt

run:
	docker compose up --build

run-local:
	python -m app

down:
	docker compose down

db-up:
	docker compose up -d db

migrate:
	alembic upgrade head

format:
	black . -l 79

format-check:
	black --check .

lint:
	flake8

test:
	TEST_POSTGRES_DATABASE_URL=postgresql+psycopg://task_tracker:task_tracker@127.0.0.1:5432/task_tracker_test \
	pytest -q

check: format-check lint test
