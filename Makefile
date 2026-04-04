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
	pytest -q

check: format-check lint test
