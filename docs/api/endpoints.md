---
title: API Endpoints Reference
description: Complete reference for all Crucible Platform API endpoints
order: 1
---

# API Endpoints Reference

The Crucible Platform provides a RESTful API for code evaluation and platform management.

## Base URL

```
https://api.crucible-platform.com
```

For local development:
```
http://localhost/api
```

## Authentication

Most endpoints require authentication via API key or JWT token.

### API Key Authentication
```bash
curl -H "X-API-Key: your-api-key" https://api.crucible-platform.com/api/eval
```

### JWT Authentication
```bash
curl -H "Authorization: Bearer your-jwt-token" https://api.crucible-platform.com/api/eval
```

## Core Endpoints

### Submit Evaluation

Submit code for evaluation.

```http
POST /api/eval
```

#### Request Body

```json
{
  "code": "print('Hello, World!')",
  "language": "python",
  "engine": "docker",
  "timeout": 30
}
```

#### Response

```json
{
  "eval_id": "eval_20250629_123456_abc123",
  "status": "queued",
  "message": "Evaluation queued successfully",
  "queue_position": 5
}
```

#### Status Codes
- `200` - Evaluation submitted successfully
- `400` - Invalid request body
- `401` - Authentication required
- `429` - Rate limit exceeded
- `503` - Service unavailable

### Get Evaluation Status

Check the status of a submitted evaluation.

```http
GET /api/eval-status/{eval_id}
```

#### Response

```json
{
  "eval_id": "eval_20250629_123456_abc123",
  "status": "completed",
  "created_at": "2025-06-29T12:34:56Z",
  "completed_at": "2025-06-29T12:35:02Z",
  "output": "Hello, World!\n",
  "error": "",
  "success": true
}
```

#### Status Values
- `queued` - In queue, waiting for execution
- `running` - Currently executing
- `completed` - Successfully completed
- `failed` - Execution failed
- `timeout` - Execution timed out

### Batch Submit

Submit multiple evaluations in a single request.

```http
POST /api/eval-batch
```

#### Request Body

```json
{
  "evaluations": [
    {
      "code": "print('Test 1')",
      "language": "python",
      "timeout": 30
    },
    {
      "code": "print('Test 2')",
      "language": "python",
      "timeout": 30
    }
  ]
}
```

#### Response

```json
{
  "evaluations": [
    {
      "eval_id": "eval_20250629_123456_abc123",
      "status": "queued",
      "message": "Evaluation queued successfully"
    },
    {
      "eval_id": "eval_20250629_123457_def456",
      "status": "queued",
      "message": "Evaluation queued successfully"
    }
  ],
  "total": 2,
  "queued": 2,
  "failed": 0
}
```

### Get Evaluation Logs

Stream logs for a running or completed evaluation.

```http
GET /api/eval/{eval_id}/logs
```

#### Response

```json
{
  "eval_id": "eval_20250629_123456_abc123",
  "output": "Hello, World!\nProcessing...\nDone!",
  "error": "",
  "is_running": false,
  "exit_code": 0,
  "status": "completed"
}
```

### Kill Evaluation

Terminate a running evaluation.

```http
POST /api/eval/{eval_id}/kill
```

#### Response

```json
{
  "eval_id": "eval_20250629_123456_abc123",
  "killed": true,
  "message": "Evaluation terminated successfully"
}
```

## Platform Endpoints

### Queue Status

Get current queue statistics.

```http
GET /api/queue-status
```

#### Response

```json
{
  "queued": 15,
  "processing": 3,
  "queue_length": 18,
  "total_tasks": 1542
}
```

### Platform Status

Get overall platform health and statistics.

```http
GET /api/status
```

#### Response

```json
{
  "platform": "healthy",
  "mode": "microservices",
  "services": {
    "gateway": "healthy",
    "queue": "healthy",  
    "storage": "healthy",
    "executor": "healthy"
  },
  "queue": {
    "queued": 15,
    "processing": 3
  },
  "storage": {
    "total_evaluations": 10543,
    "by_status": {
      "completed": 9876,
      "failed": 567,
      "timeout": 100
    }
  },
  "version": "2.0.0"
}
```

### List Evaluations

Get evaluation history with pagination.

```http
GET /api/evaluations?limit=20&offset=0&status=completed
```

#### Query Parameters
- `limit` - Number of results to return (default: 100, max: 1000)
- `offset` - Number of results to skip (default: 0)
- `status` - Filter by status (optional)

#### Response

```json
{
  "evaluations": [
    {
      "eval_id": "eval_20250629_123456_abc123",
      "status": "completed",
      "created_at": "2025-06-29T12:34:56Z",
      "code_preview": "print('Hello, World!')...",
      "success": true
    }
  ],
  "count": 543,
  "limit": 20,
  "offset": 0,
  "has_more": true
}
```

## WebSocket Endpoints

### Real-time Updates

Connect via WebSocket for real-time evaluation updates.

```
ws://localhost/ws
```

#### Message Format

```json
{
  "type": "status_update",
  "eval_id": "eval_20250629_123456_abc123",
  "data": {
    "status": "running",
    "output": "Starting execution...\n"
  }
}
```

#### Event Types
- `status_update` - Evaluation status changed
- `output_chunk` - New output available
- `completed` - Evaluation finished
- `error` - Error occurred

## Error Handling

All error responses follow this format:

```json
{
  "error": "Validation error",
  "detail": "Code field is required",
  "status_code": 400
}
```

### Common Error Codes
- `400` - Bad Request (invalid input)
- `401` - Unauthorized (missing/invalid auth)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found (resource doesn't exist)
- `429` - Too Many Requests (rate limited)
- `500` - Internal Server Error
- `503` - Service Unavailable

## Rate Limiting

Default rate limits:
- Anonymous: 10 requests/minute
- Authenticated: 100 requests/minute
- Batch endpoints: 10 requests/minute

Rate limit headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1625012345
```

## Best Practices

1. **Use batch endpoints** for multiple evaluations
2. **Poll status endpoint** instead of logs for completion
3. **Handle rate limits** with exponential backoff
4. **Set appropriate timeouts** for your use case
5. **Use correlation IDs** for request tracking

## OpenAPI Specification

Full OpenAPI 3.0 specification available at:
```
GET /api/openapi.yaml
```

Interactive documentation:
```
GET /docs
```