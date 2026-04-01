install:
	python -m pip install --upgrade pip
	python -m pip install -r requirements-dev.txt

run:
	docker compose up --build

db-up:
	docker compose up -d db

migrate:
	alembic upgrade head

test:
	pytest
