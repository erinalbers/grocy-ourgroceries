# Testing the Grocy-OurGroceries Sync Tool

This directory contains tests for the Grocy-OurGroceries sync tool.

## Running Tests

To run the tests, use the following command from the v2 directory:

```bash
pytest
```

To run tests with coverage report:

```bash
pytest --cov=clients --cov=sync --cov=utils
```

To generate an HTML coverage report:

```bash
pytest --cov=clients --cov=sync --cov=utils --cov-report=html
```

## Test Structure

- `conftest.py`: Contains shared fixtures and mock data for tests
- `test_grocy_client.py`: Tests for the Grocy API client
- `test_ourgroceries_client.py`: Tests for the OurGroceries API client

## Adding Tests

When adding new tests:

1. Use the existing fixtures in `conftest.py` where possible
2. Mock external dependencies to avoid making real API calls
3. Follow the naming convention `test_<function_name>_<scenario>`
4. Add appropriate assertions to verify behavior

## Test Coverage

The tests aim to cover:

- Normal operation paths
- Error handling and edge cases
- Retry logic
- Caching behavior
