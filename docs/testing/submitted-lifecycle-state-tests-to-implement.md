Testing Strategy for "Submitted" Lifecycle State

  Unit Tests ✅ Recommended

  What to test:
  1. API Gateway (microservices_gateway.py)
    - _submit_evaluation() publishes "submitted" event
   with correct data
    - Single eval endpoint publishes "submitted"
  before queuing
    - Batch endpoint generates unique eval_ids and
  publishes events for each
    - Error handling when publishing fails
  2. Storage Worker (storage-worker/app.py)
    - handle_evaluation_submitted() creates record
  with correct status
    - Missing field validation (eval_id, code)
    - Error handling for storage service failures

  Why: Fast feedback, easy to mock dependencies,
  catches logic errors early

  Integration Tests ✅ Highly Recommended

  What to test:
  1. Event Flow (API → Redis → Storage Worker →
  Storage Service)
    - Submitted event published by API is received by
  storage worker
    - Storage worker successfully creates evaluation
  record
    - State transitions: submitted → queued → running
  → completed
  2. Batch Processing
    - All evaluations in batch get "submitted" status
    - Background processing updates statuses correctly
    - Rate limiting and retry logic works
  3. Status Endpoint
    - Returns correct status for evaluations in each
  state
    - 202 response for non-terminal states

  Why: Critical to verify components communicate
  correctly through Redis pub/sub

  E2E Tests ✅ Recommended (But Selective)

  What to test:
  1. Happy Path
    - Submit evaluation → See "submitted" status →
  Transitions through states → Completion
    - Batch submission of 10 evaluations → All show
  proper status progression
  2. Error Scenarios
    - Submit when queue service is down
    - Submit when storage is unavailable
    - Network interruption during batch processing

  Why: Validates the entire user experience, catches
  frontend/backend integration issues

  What NOT to Test Exhaustively

  1. Every State Transition Combination - Focus on
  critical paths
  2. All Error Message Variations - Test categories,
  not every string
  3. Performance Under Load - Save for dedicated
  performance testing

  Proposed Test Structure

  tests/
  ├── unit/
  │   ├── api/
  │   │   ├── test_submit_evaluation.py
  │   │   └── test_batch_submission.py
  │   └── storage_worker/
  │       └── test_event_handlers.py
  ├── integration/
  │   ├── test_evaluation_lifecycle.py
  │   ├── test_batch_processing.py
  │   └── test_redis_events.py
  └── e2e/
      ├── test_single_evaluation_flow.py
      └── test_batch_evaluation_flow.py

  Testing Tools Recommendation

  - Unit: pytest with mocking (unittest.mock or
  pytest-mock)
  - Integration: pytest with docker-compose test
  environment
  - E2E: Playwright or Cypress for frontend, pytest
  for API workflows

  Priority Order

  1. Integration tests first - Most bang for buck,
  catches real issues
  2. Key unit tests - For complex logic (batch
  processing, retry logic)
  3. E2E smoke tests - Basic flows to ensure system
  works end-to-end

  This approach gives confidence in the new
  functionality without over-investing in tests that
  might change as the system evolves.