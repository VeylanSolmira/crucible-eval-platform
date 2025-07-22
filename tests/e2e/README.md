# End-to-End (E2E) Tests

This directory contains end-to-end tests that verify complete user workflows through the entire system stack.

## Purpose

E2E tests validate that:
- Complete user journeys work as expected
- All components integrate correctly
- The system behaves correctly from a user's perspective
- Critical business flows are functioning

## Characteristics

- **Full stack**: Tests span frontend → API → backend → database
- **User-centric**: Simulate real user interactions
- **Browser-based**: Often use tools like Selenium/Playwright
- **Slower execution**: Take longer due to UI interaction
- **High confidence**: Catch integration issues other tests miss

## Test Categories

### User Workflow Tests
Complete user journeys:
- Submit code evaluation via UI
- Monitor evaluation progress
- View completed results
- Download evaluation data

### Integration Flows
Multi-step processes:
- Submit → Process → Store → Retrieve
- Error handling across components
- Concurrent user scenarios
- Session management

### UI Interaction Tests
Frontend-specific flows:
- Form validation
- Real-time updates via WebSocket
- Error message display
- Navigation flows

## Running E2E Tests

```bash
# Run all tests including E2E
python tests/run_tests.py

# Run only E2E tests
python tests/run_tests.py e2e

# Run with browser visible (for debugging)
HEADLESS=false python tests/run_tests.py e2e
```

## Technology Stack

Common E2E testing tools:
- **Playwright**: Modern, fast, reliable browser automation
- **Selenium**: Mature, wide browser support
- **Cypress**: Developer-friendly, great debugging
- **Puppeteer**: Chrome/Chromium focused

## Writing E2E Tests

Example structure:
```python
class TestEvaluationFlow:
    def test_submit_and_monitor_evaluation(self, browser):
        """User can submit code and see results"""
        # Navigate to platform
        browser.goto("http://localhost:3000")
        
        # Enter code in editor
        editor = browser.locator(".monaco-editor")
        editor.type("print('Hello, World!')")
        
        # Submit evaluation
        submit_btn = browser.locator("button:has-text('Submit')")
        submit_btn.click()
        
        # Wait for completion
        browser.wait_for_selector(".evaluation-complete", timeout=30000)
        
        # Verify results
        output = browser.locator(".evaluation-output")
        assert "Hello, World!" in output.text_content()
```

## Best Practices

1. **Use Page Object Model**: Encapsulate page interactions
2. **Wait intelligently**: Use explicit waits, not sleep()
3. **Test data isolation**: Each test should be independent
4. **Screenshot on failure**: Capture state for debugging
5. **Stable selectors**: Use data-testid attributes

## E2E vs Other Test Types

| Aspect | E2E Tests | Integration Tests | Unit Tests |
|--------|-----------|------------------|------------|
| Scope | Full system | Multiple components | Single component |
| Speed | Slow (seconds) | Medium | Fast (ms) |
| Confidence | Highest | High | Medium |
| Debugging | Hardest | Medium | Easiest |
| Flakiness | Most prone | Some | Least |

## Current Status

We have two types of E2E tests:

### API-based E2E Tests (Implemented)
Located in this directory, these test complete workflows through APIs:
- `test_core_flows.py` - Fundamental evaluation workflows (health, submit, lifecycle, errors)
- `test_evaluation_lifecycle.py` - Complete lifecycle from submission to completion
- `test_redis_state_management.py` - Full evaluation with Redis state tracking and cleanup
- `test_fast_failing_containers.py` - Quick-failing evaluations with error capture
- `test_network_isolation.py` - Security validation for network isolation
- `test_filesystem_isolation.py` - Security validation for filesystem isolation
- `test_load.py` - Load testing the full system end-to-end
- `test_priority_queue_e2e.py` - Priority queue evaluation processing
- `test_priority_celery_e2e.py` - Celery priority task execution

### UI-based E2E Tests (Not Yet Implemented)
Browser-based tests for user interactions:
1. Code submission via UI
2. Real-time status updates
3. Result display
4. Error handling in UI
5. Concurrent user scenarios

## Future Enhancements

- Visual regression testing
- Cross-browser testing
- Mobile responsive tests
- Performance testing via E2E
- Accessibility testing