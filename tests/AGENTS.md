# tests/ - Test Suite

Pytest-based test suite mirroring the src/ structure.

## Structure

```text
tests/
├── core/           # Tests for src/core/
│   ├── test_task_parser.py
│   ├── test_task_decomposer.py
│   ├── test_team_composer.py
│   └── ...
├── orchestrator/   # Tests for src/orchestrator/
│   ├── test_agent_runner.py
│   └── ...
└── conftest.py     # Shared fixtures
```

## Running Tests

```bash
# All tests
pytest tests/

# Specific module
pytest tests/core/test_task_parser.py

# With coverage
pytest --cov=src tests/

# Verbose output
pytest -v tests/
```

## Test Conventions

1. **Mirror src/ structure** - `src/core/foo.py` → `tests/core/test_foo.py`
2. **Descriptive names** - `test_parse_extracts_constraints_from_goal`
3. **Fixtures in conftest.py** - Shared test data and mocks
4. **Unit over integration** - Fast, isolated tests preferred

## Key Fixtures

From `conftest.py`:

- Sample tasks and goals
- Mock agents and teams
- Test configurations

## Coverage Goals

Target: 80%+ coverage on core modules.

Priority:

1. `core/` - Critical path, high coverage
2. `orchestrator/` - Execution logic
3. `models/` - Data validation

## Related

- Source code: [src/](../src/AGENTS.md)
- CI/CD: Tests run on every commit
