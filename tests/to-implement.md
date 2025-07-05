What tests could we have at hte unit level 
  and then integration level to help us with issues 
  like this in the future. Just describe them so we 
  can code them later

⏺ Here are the tests that would help catch this type
  of issue:

  Unit Tests

  Frontend Unit Tests

  1. RunningEvaluations Component Tests
    - Test that status from API response is preserved,
   not hardcoded
    - Test the transformation logic for running
  evaluations
    - Verify that status mapping works correctly for
  all valid statuses
    - Test edge cases: missing status, invalid status
  values
  2. React Query Hook Tests
    - Test useRunningEvaluations hook returns data
  with status field
    - Test data transformation doesn't override status
    - Test cache key generation and invalidation
  3. Status Badge Component Tests
    - Test correct styling applied for each status
    - Test status text displays correctly
    - Test animation only shows for 'running' status

  Backend Unit Tests

  1. API Response Serialization
    - Test that evaluation objects include status
  field
    - Test status enum validation
    - Test that running endpoint filters correctly by
  status
  2. Redis State Management
    - Test that status updates are written to Redis
    - Test that running set is updated when status
  changes
    - Test cleanup of completed evaluations from
  running set

  Integration Tests

  Frontend-Backend Integration

  1. Status Update Flow Test
  - Submit evaluation
  - Poll status endpoint
  - Verify frontend displays correct status at each
  stage
  - Verify status transitions: queued → running →
  completed
  - Verify UI updates without page refresh
  2. Running List Consistency Test
  - Submit multiple evaluations
  - Complete some evaluations
  - Verify /api/evaluations?status=running only
  returns actually running
  - Verify frontend list matches backend state
  - Test pagination doesn't affect status display
  3. React Query Cache Test
  - Submit evaluation
  - Let it complete
  - Verify cache invalidation triggers
  - Verify stale data doesn't show wrong status
  - Test refetch intervals work correctly

  End-to-End Integration

  1. Full Lifecycle Test
  - Submit evaluation via UI
  - Monitor WebSocket/polling updates
  - Verify ExecutionMonitor shows correct status
  - Verify Evaluations list shows correct status
  - Test page refresh maintains correct state
  2. Concurrent Evaluation Test
  - Submit 5+ evaluations simultaneously
  - Complete them in different orders
  - Verify all status updates propagate correctly
  - Test no race conditions in status display
  3. Service Restart Resilience
  - Submit evaluation
  - Restart storage-worker mid-execution
  - Verify status updates resume correctly
  - Test Redis state persistence

  API Contract Tests

  1. Status Field Presence Test
  - Call all evaluation endpoints
  - Verify status field is always present
  - Verify status values match enum
  - Test backwards compatibility
  2. Frontend Assumption Tests
  - Mock API responses
  - Test frontend handles missing status gracefully
  - Test frontend handles invalid status values
  - Verify no hardcoded assumptions about status

  These tests would have caught the hardcoded status
  issue early and prevented the 9 rounds of debugging!


  Remember, a refresh of / resolves all of this, so 
  it's not a back end thing, right?

> Doesn't that prove it's a caching or polling thing

⏺ You're absolutely right! If a page refresh fixes it,
   then the backend is working correctly and returning
   the right data. This is definitely a frontend
  caching/polling issue.

  Since refresh fixes it, that means:
  - Backend correctly removes completed evaluations
  from the running list ✓
  - Redis cleanup is working properly ✓
  - The issue is purely in the frontend React Query
  cache or polling logic

  The problem is likely:
  1. React Query Cache: The useRunningEvaluations hook
   caches the "running" query, and when an evaluation
  completes, this cache isn't invalidated
  2. No Cross-Query Invalidation: When useEvaluation
  sees the status change to "completed", it doesn't
  trigger useRunningEvaluations to refetch
  3. Polling Continues: The running evaluations list
  keeps polling every 2 seconds but might be serving
  stale cached data

  This explains why:
  - ExecutionMonitor updates correctly (it polls the
  specific evaluation)
  - Evaluations list stays wrong (cached running list
  not invalidated)
  - Page refresh fixes it (clears all caches)

  The fix would be to invalidate the running
  evaluations query when an evaluation completes. No
  backend changes needed!

> What tests can we do for those things

⏺ Here are the tests we can create for the frontend
  caching/polling issues:

  Frontend Caching/Polling Tests

  1. React Query Cache Invalidation Test

  // Test that running evaluations cache is 
  invalidated when status changes
  - Mock the API responses
  - Submit evaluation (appears in running list)
  - Simulate status change to "completed"
  - Verify
  queryClient.invalidateQueries(['evaluations',
  'running']) is called
  - Verify the running list refetches and updates

  2. Cross-Hook Communication Test

  // Test that useEvaluation completing triggers 
  useRunningEvaluations refresh
  - Mount both hooks in test
  - Mock evaluation transitioning from running →
  completed
  - Verify useRunningEvaluations refetches
  automatically
  - Check no stale data remains in cache

  3. Polling Behavior Test

  // Test polling doesn't serve stale cached data
  - Mock API returning evaluation as running
  - Start polling (2 second interval)
  - Change mock to return empty running list
  - Verify next poll reflects the change (not cached)
  - Test staleTime and cacheTime settings

  4. Cache Key Isolation Test

  // Test that different query keys don't interfere
  - Query for running evaluations
  - Query for all evaluations
  - Complete an evaluation
  - Verify both queries update independently
  - Test no cache key collisions

  5. Manual Refetch Test

  // Test manual refetch bypasses cache
  - Mock stale data in cache
  - Call refetch() on useRunningEvaluations
  - Verify fresh data is fetched from API
  - Verify UI updates with fresh data

  6. Component Integration Test

  // Test RunningEvaluations + ExecutionMonitor 
  together
  - Render both components
  - Mock evaluation completing in ExecutionMonitor
  - Verify RunningEvaluations removes it from list
  - Test without page refresh

  7. React Query DevTools Test

  // Test cache state in React Query DevTools
  - Enable DevTools in test
  - Submit evaluation
  - Check cache state for ['evaluations', 'running']
  - Complete evaluation
  - Verify cache state updates
  - Check for stale queries

  8. Network Request Test

  // Test actual network requests (not cache)
  - Use MSW to mock API
  - Count requests to /api/evaluations?status=running
  - Complete an evaluation
  - Verify new request is made (not serving from
  cache)
  - Check request happens within polling interval

  9. Optimistic Update Test

  // Test immediate UI updates before server confirms
  - Submit evaluation
  - Optimistically add to running list
  - Complete evaluation
  - Optimistically remove from running list
  - Verify no flicker when server confirms

  10. Error Recovery Test

  // Test cache behavior during network errors
  - Mock network failure
  - Verify cache serves stale data appropriately
  - Restore network
  - Verify fresh data fetched on recovery
  - Test no infinite error loops

  Implementation Example

  Here's how we'd implement the cache invalidation
  test:

  // 
  tests/frontend/hooks/useRunningEvaluations.test.tsx
  import { renderHook, waitFor } from
  '@testing-library/react'
  import { QueryClient, QueryClientProvider } from
  '@tanstack/react-query'
  import { useRunningEvaluations } from
  '@/hooks/useRunningEvaluations'
  import { useEvaluation } from
  '@/hooks/useEvaluation'

  describe('React Query Cache Invalidation', () => {
    it('should invalidate running cache when 
  evaluation completes', async () => {
      const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false } }
      })

      // Mock API responses
      global.fetch = jest.fn()
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            evaluations: [{ eval_id: 'test-1', status:
   'running' }]
          })
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            evaluations: [] // Empty after completion
          })
        })

      const wrapper = ({ children }) => (
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      )

      // Render hook
      const { result } = renderHook(() =>
  useRunningEvaluations(), { wrapper })

      // Wait for initial fetch
      await waitFor(() => {
        expect(result.current.data?.evaluations).toHav
  eLength(1)
      })

      // Spy on invalidateQueries
      const invalidateSpy = jest.spyOn(queryClient,
  'invalidateQueries')

      // Simulate evaluation completion (would 
  normally come from useEvaluation)
      queryClient.setQueryData(['evaluation',
  'test-1'], {
        eval_id: 'test-1',
        status: 'completed'
      })

      // Trigger invalidation (this is what we need to
   add to the code)
      queryClient.invalidateQueries(['evaluations',
  'running'])

      // Verify invalidation was called
      expect(invalidateSpy).toHaveBeenCalledWith(['eva
  luations', 'running'])

      // Wait for refetch
      await waitFor(() => {
        expect(result.current.data?.evaluations).toHav
  eLength(0)
      })
    })
  })

  These tests would help us identify and fix the
  caching issues without touching the backend!