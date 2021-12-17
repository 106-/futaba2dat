.PHONY:\
	run\

run:
	poetry run uvicorn futaba2dat.main:app --host 0.0.0.0 --port 80 \
		--reload --reload-dir futaba2dat --reload-dir static --reload-dir templates