PYTHON ?= python3

ACTIONS ?= 1000
SEED ?= 42
REQUEST_DELAY ?= 1
DEPTH ?= 5

.PHONY: install test dashboard clean

install:
	$(PYTHON) -m pip install -e .

test:
	$(PYTHON) -m unittest discover 		-s order_book_python/tests 		-t . 		-p "test_*.py" 		-v

dashboard:
	$(PYTHON) -m order_book_python.cli.run_dashboard 		--actions $(ACTIONS) 		--seed $(SEED) 		--validate 		--request-delay $(REQUEST_DELAY) 		--depth $(DEPTH)

clean:
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type f -name "*.py[co]" -delete
	rm -rf build dist *.egg-info
