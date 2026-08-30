.PHONY: run test test-integration test-all lint format reload-boards deploy deploy-test deploy-production tail tail-test tail-production

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

deploy: deploy-test

deploy-test:
	$(PYWRANGLER) deploy --env ""

deploy-production:
	$(PYWRANGLER) deploy --env production

tail: tail-test

tail-test:
	$(PYWRANGLER) tail --env ""

tail-production:
	$(PYWRANGLER) tail --env production
