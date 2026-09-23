.DEFAULT_GOAL := help
UV ?= uv
RUN := $(UV) run --frozen

.PHONY: help
help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

.PHONY: install
install:  ## Create .venv with every extra + dev tools (uv) and install git hooks
	$(UV) sync --all-extras
	$(RUN) pre-commit install

.PHONY: lint
lint:  ## Ruff lint + format check
	$(RUN) ruff check .
	$(RUN) ruff format --check .

.PHONY: format
format:  ## Auto-fix lint issues and format
	$(RUN) ruff check --fix .
	$(RUN) ruff format .

.PHONY: typecheck
typecheck:  ## mypy --strict
	$(RUN) mypy

.PHONY: arch
arch:  ## Architecture contracts (import-linter; DESIGN section 6)
	$(RUN) lint-imports

.PHONY: test
test:  ## Fast hermetic tests
	$(RUN) pytest -m "not network and not slow"

.PHONY: test-all
test-all:  ## Everything, including network and slow tests
	$(RUN) pytest

.PHONY: cov
cov:  ## Tests with coverage report
	$(RUN) pytest -m "not network and not slow" --cov --cov-report=term-missing:skip-covered

.PHONY: dbt
dbt:  ## Build and test the dbt project against data/warehouse.duckdb
	cd transform && $(UV) run --frozen dbt build --profiles-dir .

.PHONY: check
check: lint typecheck arch test  ## What CI runs: lint + types + architecture + tests

.PHONY: dagster
dagster:  ## Dagster UI on :3000 (assets, schedules, runs)
	$(RUN) dagster dev -m gridcast.orchestration.definitions

.PHONY: mlflow
mlflow:  ## MLflow UI on :5001 over the local tracking store
	$(RUN) mlflow ui --backend-store-uri sqlite:///data/mlflow.db --port 5001

.PHONY: clean
clean:  ## Remove caches and build artefacts (keeps data/)
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov dist build transform/target transform/logs
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
