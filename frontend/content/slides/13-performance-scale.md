---
title: 'Performance & Scale'
duration: 2
tags: ['performance', 'benchmarks']
---

## Performance & Scale - Actual Production Metrics

### Load Test Results (Week 4)

| Concurrent Users | Total Evals | Success Rate | Avg Response Time | Notes |
| ---------------- | ----------- | ------------ | ----------------- | ----- |
| 5                | 10          | 100%         | 15.7s             | Perfect |
| 10               | 20          | 100%         | 73.2s             | Perfect |
| 20               | 50          | 100%         | 176.8s            | Perfect |
| 50               | 100         | 98%*         | 185.6s            | 2 race conditions |

*Race condition fixed with state machine implementation

### Key Performance Metrics

- **API Response**: < 100ms (p99)
- **Submission Latency**: 24-161ms
- **Execution Time**: 0.8-1.2s (simple Python)
- **Queue Time**: 10-52s (depends on load)
- **Rate Limit**: 10 req/s (nginx)
- **Executor Pool**: 3 concurrent

### Resource Usage (Under Load)

| Service | CPU (idle) | CPU (load) | Memory |
| ------- | ---------- | ---------- | ------ |
| API     | 3-4%       | 10-15%     | 90MB   |
| Celery  | 7-8%       | 15-20%     | 165MB  |
| Executor| 1-3%       | 20-40%     | 50MB   |
