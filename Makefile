.PHONY: dev build build-py build-cpp test test-unit test-integration test-e2e lint typecheck format run bench bench-regress clean

PYTHON ?= python3
PIP ?= $(PYTHON) -m pip
CMAKE_BUILD_DIR ?= hwprobe/build

dev:
	$(PIP) install -e ".[dev]"

build: build-py build-cpp

build-py:
	$(PIP) install -e .

build-cpp:
	cmake -S hwprobe -B $(CMAKE_BUILD_DIR) -DCMAKE_BUILD_TYPE=Release
	cmake --build $(CMAKE_BUILD_DIR) -j

test: test-unit

test-unit:
	$(PYTHON) -m pytest tests/unit -v

test-integration:
	RUN_INTEGRATION=1 $(PYTHON) -m pytest tests/integration -v

test-e2e:
	$(PYTHON) -m pytest tests/e2e -v -m e2e

test-cpp:
	cd $(CMAKE_BUILD_DIR) && ctest --output-on-failure

lint:
	$(PYTHON) -m ruff check src tests bench
	$(PYTHON) -m black --check src tests bench

typecheck:
	$(PYTHON) -m mypy

format:
	$(PYTHON) -m ruff check --fix src tests bench
	$(PYTHON) -m black src tests bench

run:
	$(PYTHON) -m hw_preflight.cli run --json out.json --md out.md

bench:
	$(PYTHON) -m bench.run_suite_bench --repeats 5

bench-regress:
	$(PYTHON) -m bench.run_suite_bench --repeats 5 --check-regress --threshold 0.30

clean:
	rm -rf $(CMAKE_BUILD_DIR) build dist *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +
