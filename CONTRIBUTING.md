# Contributing

## Local Setup

1. Create and activate a virtual environment.
2. Install the package in editable mode with dev dependencies.
3. Run the check suite before opening a pull request.

## Required Checks

```powershell
pytest -q
ruff check .
mypy src
python -m btr_ng.cli --help
```

## Working Agreement

- Keep changes small and integrated.
- Add tests with each behavior change.
- Do not introduce public personal data into the repository.
