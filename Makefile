install:
	python -m pip install --upgrade pip
	python -m pip install -r requirements-dev.txt

run:
	python -m app

test:
	pytest
