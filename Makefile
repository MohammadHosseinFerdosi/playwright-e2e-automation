.PHONY: install install-dev browsers lint format typecheck smoke regression ui ui-debug collect steps-audit allure-generate allure-report allure-serve clean

PYTEST := pytest
# Live Feature/Scenario/step lines in the terminal (pytest-bdd). Allure still collects separately.
GHERKIN := --gherkin-terminal-reporter
export PYTHONPATH := .

# Build static HTML under allure-report/ from the latest allure-results/ (no browser open).
# ALLURE_NO_ANALYTICS avoids Allure CLI phoning home (can fail offline / in sandbox).
define ALLURE_GENERATE
	@if [ ! -d allure-results ] || [ -z "$$(ls -A allure-results 2>/dev/null)" ]; then \
		echo "No allure-results/ to generate from. Run pytest first."; \
	else \
		if [ -d allure-report/history ]; then \
			mkdir -p allure-results/history; \
			cp -R allure-report/history/. allure-results/history/; \
		fi; \
		if command -v allure >/dev/null 2>&1; then \
			ALLURE_NO_ANALYTICS=true allure generate allure-results --clean -o allure-report \
				&& echo "Allure HTML report → allure-report/index.html"; \
		elif command -v npx >/dev/null 2>&1; then \
			ALLURE_NO_ANALYTICS=true npx --yes allure-commandline generate allure-results --clean -o allure-report \
				&& echo "Allure HTML report → allure-report/index.html"; \
		else \
			echo "Allure CLI not on PATH (and no npx). Kept raw allure-results/."; \
		fi; \
		python3 scripts/allure_dashboard.py; \
	fi
endef

install:
	pip install .

install-dev:
	pip install -e ".[dev]"
	pre-commit install

# Platform network blocks cdn.playwright.dev — always use the internal proxy.
browsers:
	PLAYWRIGHT_DOWNLOAD_HOST=https://example.com/raw-playwright-proxy/ playwright install chromium

lint:
	ruff check .
	python3 scripts/check_step_style.py

format:
	ruff format .
	ruff check --fix .

# Static type gate for scripts/ (basedpyright). Fail on errors; see [tool.basedpyright].
typecheck:
	@cmd=$$(command -v basedpyright 2>/dev/null || true); \
	if [ -z "$$cmd" ] && [ -x .venv/bin/basedpyright ]; then cmd=.venv/bin/basedpyright; fi; \
	if [ -z "$$cmd" ]; then \
		echo "basedpyright not found — run: pip install -e '.[dev]'"; \
		exit 1; \
	fi; \
	"$$cmd" --level error scripts tests

# Local runs write JUnit + Allure raw results (pytest.ini --alluredir), then HTML under allure-report/.
# -vv is required with GHERKIN so Given/When/Then lines print (plain -v only shows Scenario).
smoke:
	$(PYTEST) -m "smoke and api" -vv $(GHERKIN) --junitxml=report.xml
	$(ALLURE_GENERATE)

regression:
	$(PYTEST) -m "api and regression" -vv $(GHERKIN) --junitxml=report.xml
	$(ALLURE_GENERATE)

ui:
	$(PYTEST) -m "e2e and smoke" -vv $(GHERKIN) --junitxml=report.xml
	$(ALLURE_GENERATE)

# Watch UI in a real Chrome window (local only — not for CI).
ui-debug:
	$(PYTEST) -m "e2e and smoke" -vv $(GHERKIN) --headed --slow-mo 250 --junitxml=report.xml
	$(ALLURE_GENERATE)

# --alluredir away from allure-results/: addopts includes --clean-alluredir.
collect:
	$(PYTEST) --collect-only -q --alluredir=.tmp/allure-collect

# Runtime step-binding audit (IDE "undefined step" squiggles are not this).
# pytest-bdd --generate-missing; known Outline-placeholder false positives are documented
# in docs/framework/regex-and-bdd-guide.md §10.
steps-audit:
	$(PYTEST) --generate-missing --feature tests/bdd/features tests/bdd

# Needs Allure CLI on PATH: https://docs.qameta.io/allure/#_installing_a_commandline
allure-generate:
	$(ALLURE_GENERATE)

allure-report:
	ALLURE_NO_ANALYTICS=true allure generate allure-results --clean -o allure-report && allure open allure-report

allure-serve:
	ALLURE_NO_ANALYTICS=true allure serve allure-results

clean:
	find . -type d -name "__pycache__" -not -path "./.venv/*" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache allure-results allure-report allure-dashboard .tmp/* report.xml
