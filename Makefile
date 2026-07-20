PYTHON ?= python3

ACTIONS ?= 1000
SEED ?= 42
REQUEST_DELAY ?= 1
DEPTH ?= 5

.PHONY: install install-dev dashboard simulation test clean

install:
	$(PYTHON) -m pip install -e .

install-dev:
	$(PYTHON) -m pip install -e ".[dev]"

dashboard:
	$(PYTHON) -m order_book_python.cli.run_dashboard \
		--actions $(ACTIONS) \
		--seed $(SEED) \
		--validate \
		--request-delay $(REQUEST_DELAY) \
		--depth $(DEPTH)

simulation:
	$(PYTHON) -m order_book_python.cli.run_simulation \
		--actions $(ACTIONS) \
		--seed $(SEED) \
		--validate

test:
	$(PYTHON) -m pytest order_book_python/tests

clean:
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -prune -exec rm -rf {} +
	find . -type d -name "*.egg-info" -prune -exec rm -rf {} +
