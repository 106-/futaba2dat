.PHONY:\
	run\
	test\
	build\
	lint\
	format\
	reload-boards\

run:
	poetry run uvicorn futaba2dat.main:app \
		--host 0.0.0.0 \
		--port 8001 \
		--reload \
		--reload-dir futaba2dat \
		--reload-dir static \
		--reload-dir templates

docker-run:
	docker run -d \
		--restart always \
		--name futaba2dat \
		--env 'TZ=Asia/Tokyo' \
		-p 8001:80 \
		futaba2dat

docker-shell:
	docker exec -it futaba2dat bash

clean:
	docker stop futaba2dat
	docker rm futaba2dat
	docker rmi futaba2dat

test:
	poetry run pytest

build:
	docker build -t futaba2dat .

lint:
	poetry run flake8 ./futaba2dat ./tests

format:
	poetry run isort ./futaba2dat ./tests
	poetry run black ./futaba2dat ./tests

reload-boards:
	poetry run python -m tools.make_boards