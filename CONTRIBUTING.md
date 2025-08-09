# Contributing

Thanks for your interest in contributing to async-seo-analyzer!

## Local development

- Use Python 3.11+
- Create a virtual environment and install with dev extras:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

## Running tests

```bash
pytest -q
```

## Linting & formatting

This project relies on readable code and docstrings. Please keep functions
well documented and avoid overly terse names. If you add tooling, include it
in dev extras and document it here.

## Submitting changes

- Open a pull request with a clear description.
- Include tests when possible.
- Keep commits focused and small.