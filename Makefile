.PHONY: install test lint format typecheck run-baseline run-multi benchmark clean

PYTHON := python
ifeq ($(OS),Windows_NT)
ifneq (,$(wildcard .venv/Scripts/python.exe))
PYTHON := .venv/Scripts/python.exe
endif
else
ifneq (,$(wildcard .venv/bin/python))
PYTHON := .venv/bin/python
endif
endif

install:
	$(PYTHON) -m pip install -e ".[dev,llm]"

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check src tests

format:
	$(PYTHON) -m ruff format src tests

typecheck:
	$(PYTHON) -m mypy src

run-baseline:
	$(PYTHON) -m multi_agent_research_lab.cli baseline --query "Research GraphRAG state-of-the-art"

run-multi:
	$(PYTHON) -m multi_agent_research_lab.cli multi-agent --query "Research GraphRAG state-of-the-art"

benchmark:
	$(PYTHON) -m multi_agent_research_lab.cli benchmark

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache dist build *.egg-info
