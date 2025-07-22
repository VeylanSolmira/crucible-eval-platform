# Testing Strategy for Crucible Platform

## Overview
This document outlines our testing approach for different components and why we chose each tool.

## Testing Components by Area

### Python Backend Testing
**Choice: pytest**
- **Why**: Industry standard, rich ecosystem, async support, fixtures for reusability
- **Key plugins**:
  - `pytest-asyncio` - Async test support
  - `pytest-timeout` - Prevent hanging tests  
  - `pytest-xdist` - Parallel execution
  - `pytest-mock` - Enhanced mocking
- **Use for**: Unit tests, integration tests, API tests

### TypeScript/Frontend Testing
**Choice: Jest + React Testing Library**
- **Why**: Jest is the React standard, fast, great mocking
- **React Testing Library**: Tests components like users interact with them
- **Use for**: Component unit tests, utility functions, hooks

### End-to-End Testing
**Choice: Playwright (Python bindings)**
- **Why**: 
  - Can write E2E tests in Python (consistency)
  - Cross-browser support
  - Built-in waiting/retry logic
  - Network interception capabilities
- **Use for**: Full user workflows, cross-service scenarios

### Performance Testing
**Choice: Locust (Python)**
- **Why**: Python-based, scalable, good for API load testing
- **Alternative**: k6 if we need more advanced scenarios
- **Use for**: Load testing, stress testing, spike testing

### Security Testing
**Choice: Custom Python scripts + Tools**
- **Why**: Flexibility to test our specific isolation requirements
- **Tools**: 
  - Trivy for container scanning
  - Custom scripts for network isolation verification
  - Input fuzzing with hypothesis
- **Use for**: Container escape attempts, resource limits, input validation

### Infrastructure Testing
**Choice: pytest + testinfra**
- **Why**: Test infrastructure as code, verify container configs
- **Use for**: Docker configurations, service health, volume mounts

## Test Organization

```
tests/
├── unit/              # Fast, isolated tests
│   ├── python/        # Backend unit tests (pytest)
│   └── typescript/    # Frontend unit tests (jest)
├── integration/       # Service interaction tests (pytest)
├── e2e/              # Full workflows (playwright)
├── performance/      # Load tests (locust)
├── security/         # Security-specific tests
├── fixtures/         # Shared test data
└── conftest.py       # Shared pytest configuration
```

## Common Patterns

### Polling/Waiting (pytest)
```python
# Instead of time.sleep(), use fixtures
@pytest.fixture
def wait_for():
    def _wait(condition, timeout=10, interval=0.5):
        end_time = time.time() + timeout
        while time.time() < end_time:
            if condition():
                return True
            time.sleep(interval)
        return False
    return _wait
```

### API Client (pytest)
```python
@pytest.fixture
def api_client():
    return TestClient(base_url="http://localhost/api")
```

### Database State (pytest)
```python
@pytest.fixture
def clean_db():
    # Setup
    yield
    # Teardown - clean test data
```

## Migration Plan

1. **Phase 1** (Now): Convert existing tests to pytest
   - Redis state test
   - Core flow tests
   
2. **Phase 2**: Add frontend tests when needed
   - Jest setup
   - Component tests
   
3. **Phase 3**: E2E tests for critical paths
   - Playwright setup
   - User journey tests

## Why This Approach?

1. **Python-first**: Most of our code is Python, so Python testing tools
2. **Gradual complexity**: Start simple (pytest), add tools as needed
3. **Reusability**: Fixtures prevent code duplication
4. **CI/CD friendly**: All tools work well in automated pipelines
5. **Developer experience**: Good IDE support, clear error messages

## Database Testing Strategy

### Unit Tests: Skip Database Tests
**Why**: Unit tests should be fast and isolated. Testing database models/operations in unit tests:
- Requires real database setup (not a unit test anymore)
- Tests the ORM framework, not our code
- Provides false confidence with SQLite when production uses PostgreSQL
- No business logic to test - just CRUD operations

### Integration Tests: Test Full Database Flow
**This is where database testing belongs:**
- Test complete flows: API → Service → PostgreSQL → Response
- Use real PostgreSQL (via Docker or test database)
- Test transactions, constraints, indexes work correctly
- Verify PostgreSQL-specific features (JSONB, arrays, etc.)
- Test error handling and rollbacks

**Example Integration Test:**
```python
def test_evaluation_full_lifecycle(api_client, test_db):
    # Submit evaluation via API
    resp = api_client.post("/api/eval", json={...})
    eval_id = resp.json()["eval_id"]
    
    # Verify stored in PostgreSQL correctly
    eval = test_db.query(Evaluation).filter_by(id=eval_id).first()
    assert eval.status == "queued"
    
    # Update via API
    api_client.put(f"/api/eval/{eval_id}", json={"status": "completed"})
    
    # Verify database updated
    test_db.refresh(eval)
    assert eval.status == "completed"
```

### When Database Unit Tests Make Sense
Only when you have complex database-specific logic:
- Custom stored procedures or functions
- Complex materialized views
- Performance-critical query optimization
- Database-specific business logic

We don't have any of these - our database is simple storage.