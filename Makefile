.PHONY: install test lint typecheck check dev demo-reset demo-preview seed-validate requirement-coverage app-boundary bench bench-smoke media screens

install:
	cd app/backend && python -m pip install -e '.[dev]'
	cd app/web && npm install

test:
	python -m pytest tests -q
	cd app/web && npm test -- --run

lint:
	ruff check app/backend/src tests
	cd app/web && npm run lint

typecheck:
	mypy app/backend/src
	cd app/web && npm run typecheck

check: seed-validate requirement-coverage app-boundary lint typecheck test

dev:
	python scripts/dev.py

dev-docker:
	docker compose up --build  # future container path, not required locally

demo-reset:
	python scripts/demo/reset_demo.py

demo-preview:
	python scripts/demo/reset_demo.py --seed-preview

seed-validate:
	python scripts/data/validate_seed.py data/scenarios/lunch-rush.json

requirement-coverage:
	python scripts/quality/check_requirement_coverage.py docs/requirements/traceability.md

app-boundary:
	python scripts/repo/check_app_boundary.py

bench:
	python scripts/bench/routing_benchmark.py --export-lab-trace
	python scripts/media/render_search_gif.py

bench-smoke:
	python scripts/bench/routing_benchmark.py --smoke

media:
	python scripts/media/render_search_gif.py

screens:
	cd app/web && npx playwright test --grep @screens
