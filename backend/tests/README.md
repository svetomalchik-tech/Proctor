# Unit Tests

Comprehensive unit test suite for the Proctoring System backend.

## Test Structure

```
tests/
├── __init__.py
├── test_behavior_analyzer.py    # Behavior analysis & pattern detection tests
├── test_screen_analyzer.py      # Screen activity monitoring tests
├── test_rate_limiter.py         # Rate limiting middleware tests
└── conftest.py                  # Pytest fixtures and configuration (future)
```

## Running Tests

### Run all tests
```bash
cd backend
pytest
```

### Run specific test file
```bash
pytest tests/test_behavior_analyzer.py -v
```

### Run specific test class
```bash
pytest tests/test_behavior_analyzer.py::TestBehaviorAnalyzerRiskScoring -v
```

### Run specific test function
```bash
pytest tests/test_behavior_analyzer.py::TestBehaviorAnalyzerRiskScoring::test_risk_score_capped_at_max -v
```

### Run with coverage report
```bash
pip install pytest-cov
pytest --cov=app --cov-report=html --cov-report=term-missing
```

### Run only fast tests (exclude slow)
```bash
pytest -m "not slow"
```

## Test Categories

### Unit Tests (Current)
- **Behavior Analyzer**: Pattern detection, risk scoring, event processing
- **Screen Analyzer**: Screen event processing, severity calculation, app blocking
- **Rate Limiter**: Rate limiting logic, IP tracking, middleware functionality

### Future Tests (Planned)
- **Integration Tests**: API endpoints, database operations, WebSocket connections
- **E2E Tests**: Full session workflows, multi-user scenarios
- **Performance Tests**: Load testing, stress testing

## Test Coverage Goals

| Module | Current Coverage | Target Coverage |
|--------|-----------------|-----------------|
| behavior_analyzer.py | ~85% | 90%+ |
| screen_analyzer.py | ~90% | 90%+ |
| rate_limiter.py | ~95% | 90%+ |
| session_manager.py | 0% | 85%+ |
| cv_processor.py | 0% | 80%+ |
| api/proctoring.py | 0% | 85%+ |

## Writing New Tests

### Test Naming Convention
```python
class TestClassName:
    """Test class for ComponentName."""
    
    def test_specific_behavior(self):
        """Test description should explain what is being tested."""
        pass
```

### Test Structure (AAA Pattern)
```python
def test_example():
    # Arrange - setup test data
    analyzer = BehaviorAnalyzer("test_session")
    
    # Act - execute the code being tested
    result = analyzer.get_risk_assessment()
    
    # Assert - verify the outcome
    assert result["risk_level"] == "LOW"
```

### Fixtures (in conftest.py)
```python
import pytest

@pytest.fixture
def sample_event():
    return Event(
        timestamp=time.time(),
        event_type="face_detected",
        severity=SeverityLevel.LOW
    )

def test_with_fixture(sample_event):
    assert sample_event.event_type == "face_detected"
```

## Continuous Integration

Tests are automatically run on:
- Every pull request
- Every merge to main branch
- Daily scheduled runs (for flaky test detection)

### CI Requirements
- All tests must pass before merging
- Code coverage must not decrease
- No new warnings introduced

## Troubleshooting

### Common Issues

**Import errors:**
```bash
# Ensure you're in the backend directory
cd backend
export PYTHONPATH=$(pwd)
pytest
```

**Async test errors:**
```bash
# Make sure pytest-asyncio is installed
pip install pytest-asyncio
```

**OpenCV/MediaPipe warnings:**
```bash
# These are expected during tests using CV components
# Tests are designed to work around initialization warnings
```

## Best Practices

1. **Keep tests independent** - Each test should run in isolation
2. **Use descriptive names** - Test names should explain the scenario
3. **Test edge cases** - Boundary conditions, empty inputs, errors
4. **Mock external dependencies** - Database, APIs, file system
5. **Follow AAA pattern** - Arrange, Act, Assert
6. **Don't test implementation details** - Test behavior, not internal structure

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio documentation](https://pytest-asyncio.readthedocs.io/)
- [Python testing best practices](https://docs.python-guide.org/writing/tests/)
