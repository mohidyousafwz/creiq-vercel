# CREIQ Test Suite

This directory contains comprehensive tests for the CREIQ ARB website automation project.

## Quick Start

### Install Test Dependencies
```bash
pip install -r tests/requirements-test.txt
```

### Run All Tests
```bash
python run_tests.py
# or
python -m pytest tests/ -v
```

### Run with Coverage
```bash
python -m pytest tests/ --cov=src/creiq --cov-report=html
```

## Test Structure

```
tests/
├── test_playwright_automation.py  # Main test suite with 30 tests
├── requirements-test.txt          # Test dependencies
├── TEST_SUMMARY.md               # Detailed test documentation
└── README.md                     # This file
```

## Test Files

### test_playwright_automation.py
Comprehensive test suite for the PlaywrightAutomation class:
- **30 tests** covering all major functionality
- **80% code coverage** for playwright_automation.py
- Unit tests, integration tests, and edge case tests
- Full mocking of Playwright components

## Key Features

### 1. Comprehensive Coverage
- Initialization and configuration
- Browser lifecycle management
- Roll number processing
- Error handling and recovery
- Graceful shutdown support
- File operations

### 2. Test Categories
- **Unit Tests**: Test individual methods in isolation
- **Integration Tests**: Test end-to-end workflows
- **Edge Case Tests**: Test unusual scenarios and error conditions

### 3. Testing Best Practices
- Pytest fixtures for setup/teardown
- Mocking for external dependencies
- Parameterized tests for multiple scenarios
- Temporary files for safe file testing
- Clear test naming and documentation

## Running Specific Tests

### Run a single test
```bash
python -m pytest tests/test_playwright_automation.py::TestPlaywrightAutomation::test_initialization -v
```

### Run tests matching a pattern
```bash
python -m pytest tests/ -k "roll_number" -v
```

### Run with specific markers (when implemented)
```bash
python -m pytest tests/ -m "unit" -v
python -m pytest tests/ -m "integration" -v
```

## Coverage Reports

After running tests with coverage, view the HTML report:
```bash
# Generate report
python -m pytest tests/ --cov=src/creiq --cov-report=html

# View report (Windows)
start htmlcov/index.html

# View report (Mac/Linux)
open htmlcov/index.html
```

## Continuous Integration

These tests are designed to run in CI/CD pipelines. The exit code will be:
- `0` if all tests pass
- Non-zero if any tests fail

## Writing New Tests

When adding new tests:
1. Follow the existing naming convention: `test_<feature>_<scenario>`
2. Use appropriate fixtures for setup
3. Mock external dependencies
4. Include both success and failure cases
5. Document complex test logic
6. Clean up any created resources

## Troubleshooting

### Import Errors
Ensure the project root is in your Python path:
```bash
export PYTHONPATH="${PYTHONPATH}:${PWD}"  # Unix/Mac
set PYTHONPATH=%PYTHONPATH%;%CD%         # Windows
```

### Environment Variables
Tests use a `.env.test` file for test configuration. This is created automatically by `run_tests.py`.

### Mock Issues
If mocks aren't working correctly, ensure you're patching at the correct import location. 