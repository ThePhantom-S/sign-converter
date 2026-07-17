.PHONY: backend lint format test

backend:
	cd apps/backend && uv run uvicorn app.main:app --reload

lint:
	cd apps/backend && uv run ruff check .

format:
	cd apps/backend && uv run black .

test:
	cd apps/backend && uv run pytest
