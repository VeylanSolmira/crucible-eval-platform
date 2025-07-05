# Frontend Testing Setup

## Test Dependencies to Install

```bash
npm install --save-dev \
  jest \
  jest-environment-jsdom \
  @testing-library/react \
  @testing-library/jest-dom \
  @testing-library/user-event \
  @types/jest \
  babel-jest \
  msw
```

## Add Test Scripts to package.json

Add these scripts to the `scripts` section:

```json
{
  "scripts": {
    "test": "jest",
    "test:watch": "jest --watch",
    "test:coverage": "jest --coverage"
  }
}
```

## Running Tests

```bash
# Run all tests
npm test

# Run tests in watch mode (re-runs on file changes)
npm run test:watch

# Run tests with coverage report
npm run test:coverage

# Run specific test file
npm test useEvaluation.test.tsx

# Run tests matching pattern
npm test -- --testNamePattern="cache invalidation"
```

## Test Structure

```
frontend/
├── __tests__/
│   ├── setup.ts                          # Jest setup file
│   ├── hooks/
│   │   ├── useEvaluation.test.tsx        # Hook-specific tests
│   │   ├── crossHookCommunication.test.tsx
│   │   └── networkRequestMonitoring.test.tsx
│   └── components/
│       └── evaluationStatusIntegration.test.tsx
├── jest.config.js                        # Jest configuration
└── TESTING_SETUP.md                      # This file
```

## Test Priorities

1. **Cache Invalidation Test** - Verifies our fix for the status update bug
2. **Cross-Hook Communication** - Tests useEvaluation triggers useRunningEvaluations refresh
3. **Network Monitoring** - Ensures no request flooding (429 errors)
4. **Component Integration** - Tests UI components update correctly

## Writing Tests

Each test file has TODO comments explaining what to implement. Key patterns:

### Mocking API Responses
```typescript
global.fetch = jest.fn().mockResolvedValueOnce({
  ok: true,
  json: async () => ({ status: 'running' })
})
```

### Testing Hook Updates
```typescript
const { result, rerender } = renderHook(() => useEvaluation('test-id'), { wrapper })
await waitFor(() => {
  expect(result.current.data?.status).toBe('completed')
})
```

### Monitoring Cache Invalidations
```typescript
const invalidateSpy = jest.spyOn(queryClient, 'invalidateQueries')
// ... trigger status change ...
expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['evaluations', 'running'] })
```

## Next Steps

1. Install dependencies
2. Run `npm test` to verify setup
3. Implement TODOs in test files
4. Add more tests as needed