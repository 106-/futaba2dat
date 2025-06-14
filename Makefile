.PHONY:\
	run\
	test\
	test-integration\
	test-all\
	build\
	lint\
	format\
	renew-container\
	reload-boards\

TAG=$(shell git rev-parse --short HEAD)
PORT?=80

run:
	mkdir -p ./db
	DB_NAME=./db/log.sqlite poetry run uvicorn futaba2dat.main:app \
		--host 0.0.0.0 \
		--port $(PORT) \
		--reload \
		--reload-dir futaba2dat \
		--reload-dir static \
		--reload-dir templates \
		--proxy-headers \
		--forwarded-allow-ips "*"

docker-run: docker-build
	mkdir -p ./db
	docker run --rm \
		--name futaba2dat \
		--env 'TZ=Asia/Tokyo' \
		--env 'DB_NAME=/app/db/log.sqlite' \
		-v "$(PWD)/db:/app/db" \
		-p $(PORT):80 \
		futaba2dat:$(TAG)

clean:
	docker images 'futaba2dat' --format '{{.Repository}}:{{.Tag}}' | xargs -r docker rmi

test:
	poetry run pytest -m "not integration"

test-integration:
	poetry run pytest -m integration -v

test-all:
	poetry run pytest -v

docker-build:
	docker build -t futaba2dat:$(TAG) .

lint:
	poetry run ruff check ./futaba2dat ./tests

format:
	poetry run ruff check --fix ./futaba2dat ./tests
	poetry run ruff format ./futaba2dat ./tests

renew-container:
	docker compose pull
	docker compose up -d

reload-boards:
	poetry run python -m tools.make_boards