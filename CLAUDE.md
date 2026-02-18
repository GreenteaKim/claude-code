# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Python 3.9 Data/ML study project. Virtual environment is at `.venv/`.

## Commands

```bash
# Activate venv
source .venv/bin/activate

# Install dependencies (including dev tools)
pip install -e ".[dev]"

# Run all tests
pytest

# Run a single test file
pytest tests/test_example.py

# Run a single test by name
pytest tests/test_example.py::test_placeholder

# Lint
ruff check .

# Format
ruff format .

# Type check
mypy src/
```

## Structure

```
src/        # importable Python modules
tests/      # pytest test files
notebooks/  # Jupyter notebooks for exploration
data/
  raw/      # original, unmodified data (gitignored)
  processed/ # cleaned/transformed data
```

## Dependencies

Declared in `pyproject.toml`. Core: `numpy`, `pandas`, `scikit-learn`, `matplotlib`, `jupyter`. Dev: `pytest`, `ruff`, `mypy`.

Add new dependencies to `pyproject.toml` then run `pip install -e ".[dev]"` to sync.
