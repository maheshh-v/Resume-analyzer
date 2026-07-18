# RecruitX top-level Makefile. Eval harness + test entry points.
# The harness imports the backend from apps/api at runtime (see evals/harness/pipeline.py),
# so it runs against the SAME venv the backend uses.

ifeq ($(OS),Windows_NT)
  VENV_PY := apps/api/.venv/Scripts/python.exe
else
  VENV_PY := apps/api/.venv/bin/python
endif
PY := $(if $(wildcard $(VENV_PY)),$(VENV_PY),python)

.PHONY: help eval eval-report eval-build eval-test test-api test

help:
	@echo "eval         - run the three eval runners (prints JSON, no files written)"
	@echo "eval-report  - aggregate all runners into evals/results/ (latest.json + latest.md)"
	@echo "eval-build   - regenerate golden_v1.jsonl + fixtures from the authoring script"
	@echo "eval-test    - run the eval harness unit + integration tests"
	@echo "test-api     - run the backend test suite (apps/api)"
	@echo "test         - run everything (api + evals)"

eval:
	$(PY) -m evals.runners.run_claim_extraction
	$(PY) -m evals.runners.run_citation_validity
	$(PY) -m evals.runners.run_verdict_accuracy

eval-report:
	$(PY) -m evals.report

eval-build:
	$(PY) evals/datasets/build_golden.py

eval-test:
	$(PY) -m pytest evals/tests -q

test-api:
	cd apps/api && $(if $(wildcard .venv/Scripts/python.exe),.venv/Scripts/python.exe,.venv/bin/python) -m pytest -q

test: test-api eval-test
