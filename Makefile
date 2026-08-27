.PHONY: run test test-integration test-all lint format reload-boards deploy tail

PYWRANGLER := uv run pywrangler

run:
	$(PYWRANGLER) dev

test:
	uv run pytest -m "not integration"

test-integration:
	uv run pytest -m integration -v

test-all:
	uv run pytest -v

lint:
	uv run ruff check ./

format:
	uv run ruff format ./

reload-boards:
	uv run python -m tools.make_boards

deploy:
	$(PYWRANGLER) deploy

tail:
	$(PYWRANGLER) tail
