.PHONY:\
	run\
	test\
	build\
	lint\
	format\

run:
	poetry run uvicorn futaba2dat.main:app --host 0.0.0.0 --port 80 \
		--reload --reload-dir futaba2dat --reload-dir static --reload-dir templates

test:
	poetry run pytest

build:
	docker build -t futaba2dat .

lint:
	poetry run flake8 ./futaba2dat ./tests

format:
	poetry run isort ./futaba2dat ./tests
	poetry run black ./futaba2dat ./tests