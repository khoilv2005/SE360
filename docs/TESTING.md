# Testing Guide for UIT-Go

This guide covers all testing practices for the UIT-Go ride-hailing platform.

## 📋 Table of Contents

- [Test Structure](#test-structure)
- [Running Tests](#running-tests)
- [Test Coverage](#test-coverage)
- [Writing New Tests](#writing-new-tests)
- [CI/CD Integration](#cicd-integration)

## 🏗️ Test Structure

```
SE360/
└── tests/
    ├── requirements.txt               # Test dependencies
    ├── test_userservice.py            # Auth & password tests
    ├── test_userservice_crud.py       # User CRUD operation tests
    ├── test_tripservice.py            # Trip management tests
    ├── test_driverservice.py          # Driver profile & wallet tests
    ├── test_locationservice.py        # Geospatial & WebSocket tests
    ├── test_paymentservice.py         # Payment & VNPay tests
    └── smoke_test.py                  # Integration tests (post-deployment)
```

## 🚀 Running Tests

### Prerequisites

```bash
# Install test dependencies
cd tests/
pip install -r requirements.txt
```

### Run All Unit Tests

```bash
# Run all tests (excluding smoke tests)
pytest tests/ --deselect tests/smoke_test.py -v

# Run with coverage report
pytest tests/ --deselect tests/smoke_test.py --cov=. --cov-report=html
```

### Run Tests by Service

```bash
# UserService tests
pytest tests/test_userservice.py tests/test_userservice_crud.py -v

# TripService tests
pytest tests/test_tripservice.py -v

# DriverService tests
pytest tests/test_driverservice.py -v

# LocationService tests
pytest tests/test_locationservice.py -v

# PaymentService tests
pytest tests/test_paymentservice.py -v
```

### Run Smoke Tests (Integration)

```bash
# After deployment, test live endpoints
export API_URL=http://<INGRESS_IP>
python tests/smoke_test.py
```

## 📊 Test Coverage

### Coverage Goals

| Component | Current Coverage | Target Coverage |
|-----------|------------------|-----------------|
| **UserService** | ~60% | 70%+ |
| **TripService** | ~50% | 70%+ |
| **DriverService** | ~50% | 70%+ |
| **LocationService** | ~40% | 70%+ |
| **PaymentService** | ~50% | 70%+ |

### Generate Coverage Report

```bash
# Generate HTML coverage report
pytest tests/ --deselect tests/smoke_test.py \
    --cov=UserService \
    --cov=TripService \
    --cov=DriverService \
    --cov=LocationService \
    --cov=PaymentService \
    --cov-report=html \
    --cov-report=term

# Open report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## ✍️ Writing New Tests

### Test Structure

```python
"""
Description of test module
Run with: pytest tests/test_yourservice.py -v
"""
import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

# Set environment variables BEFORE imports
os.environ.setdefault("REQUIRED_VAR", "test_value")

# Add service to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'YourService'))

# Import after env vars set
import crud
import schemas


class TestYourFeature:
    """Test specific feature"""

    @pytest.mark.asyncio
    async def test_your_function(self):
        """Test description"""
        # Arrange
        mock_db = AsyncMock()

        # Act
        result = await your_function(mock_db)

        # Assert
        assert result is not None
```

### Best Practices

1. **Arrange-Act-Assert**: Structure tests with clear sections
2. **Use Mocks**: Mock database and external service calls
3. **Async Tests**: Use `@pytest.mark.asyncio` for async functions
4. **Descriptive Names**: Test names should describe what they test
5. **Independent Tests**: Each test should be independent
6. **Test Edge Cases**: Test error conditions and edge cases

### Example: Testing CRUD Operation

```python
@pytest.mark.asyncio
async def test_create_user_success(self):
    """Test successful user creation"""
    # Arrange
    mock_db = AsyncMock(spec=AsyncSession)
    user_data = schemas.UserCreate(
        username="testuser",
        email="test@example.com",
        password="password123"
    )

    # Mock database operations
    with patch('crud.get_user_by_email', return_value=None):
        # Act
        created_user = await crud.create_user(mock_db, user_data)

    # Assert
    assert created_user is not None
    assert created_user.email == user_data.email
```

## 🔄 CI/CD Integration

### GitHub Actions Workflow

Tests run automatically on every push to `main`:

```yaml
# .github/workflows/deploy.yml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Run unit tests
        run: pytest tests/ --deselect tests/smoke_test.py
        continue-on-error: false  # Fail build if tests fail
```

### Local Pre-commit Testing

```bash
# Run tests before committing
pytest tests/ --deselect tests/smoke_test.py -v

# Or create a pre-commit hook
cat > .git/hooks/pre-commit <<'EOF'
#!/bin/bash
pytest tests/ --deselect tests/smoke_test.py -q || exit 1
EOF

chmod +x .git/hooks/pre-commit
```

## 🐛 Debugging Failed Tests

### Verbose Output

```bash
# Show detailed output
pytest tests/test_userservice.py -vv

# Show print statements
pytest tests/test_userservice.py -s

# Stop on first failure
pytest tests/test_userservice.py -x
```

### Run Specific Test

```bash
# Run specific test class
pytest tests/test_userservice.py::TestUserCRUD -v

# Run specific test method
pytest tests/test_userservice.py::TestUserCRUD::test_create_user_success -v
```

## 📈 Improving Test Coverage

### Priority Areas

1. **Critical Paths**: Authentication, payment processing, trip creation
2. **Error Handling**: Test all exception scenarios
3. **Edge Cases**: Empty inputs, invalid data, boundary conditions
4. **Integration Points**: Service-to-service communication

### Coverage Report Analysis

```bash
# Find untested code
pytest tests/ --deselect tests/smoke_test.py \
    --cov=UserService \
    --cov-report=term-missing

# Look for lines marked with "!"
# These indicate untested code paths
```

## 🔍 Test Types

### Unit Tests
- Test individual functions/methods in isolation
- Mock all external dependencies
- Fast execution (milliseconds)

### Integration Tests (Smoke Tests)
- Test service endpoints with real infrastructure
- Run after deployment
- Slower execution (seconds)

### Contract Tests
- Test API schemas match expectations
- Ensure backward compatibility
- TODO: Implement with Pact

### Load Tests
- Test system under load
- TODO: Implement with Locust or k6

## 📚 Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Python unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [Testing FastAPI](https://fastapi.tiangolo.com/tutorial/testing/)

## 🎯 Next Steps

1. ✅ Increase coverage to 70%+ for all services
2. ⏳ Add contract tests with Pact
3. ⏳ Implement load testing with Locust
4. ⏳ Add mutation testing with mutmut
5. ⏳ Setup test database fixtures
