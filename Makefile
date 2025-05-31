.PHONY:\
	run\
	test\
	build\
	lint\
	format\
	renew-container\
	reload-boards\

TAG=$(shell git rev-parse --short HEAD)

run:
	poetry run uvicorn futaba2dat.main:app \
		--host 0.0.0.0 \
		--port 8001 \
		--reload \
		--reload-dir futaba2dat \
		--reload-dir static \
		--reload-dir templates \
		--proxy-headers \
		--forwarded-allow-ips "*"

docker-run:
	docker run -d \
		--restart always \
		--name futaba2dat \
		--env 'TZ=Asia/Tokyo' \
		--env 'DB_NAME=/app/db/log.sqlite' \
		-p 8000:80 \
		-v ./db:/app/db \
		futaba2dat:$(TAG)

docker-shell:
	docker exec -it futaba2dat bash

clean:
	docker stop futaba2dat
	docker rm futaba2dat
	docker rmi futaba2dat

test:
	poetry run pytest

build:
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