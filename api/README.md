# API Gateway Service

## Overview

The API Gateway Service is the primary entry point for all client requests to the Crucible platform. It handles request routing, authentication (planned), rate limiting, and orchestrates communication between various microservices.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│   Clients   │────▶│  API Gateway │────▶│  Microservices  │
│  (Frontend) │     │   (FastAPI)  │     │                 │
└─────────────┘     └──────────────┘     ├─────────────────┤
                            │            │  Queue Service  │
                            │            │ Storage Service │
                            │            │ Celery Workers  │
                            │            │   Executors     │
                            │            └─────────────────┘
                            │
                    ┌───────▼────────┐
                    │  Redis Events  │
                    └────────────────┘
```

## Key Features

- **Request Routing**: Routes evaluation requests to appropriate queue systems
- **Traffic Splitting**: Supports gradual migration between queue systems (legacy ↔ Celery)
- **WebSocket Support**: Real-time updates for evaluation status
- **OpenAPI Generation**: Auto-generates API specification
- **Health Monitoring**: Tracks health of all downstream services
- **Event Publishing**: Publishes events to Redis for distributed processing

## API Endpoints

### Core Evaluation Endpoints

- `POST /api/eval` - Submit code for evaluation
- `POST /api/eval-batch` - Submit multiple evaluations
- `GET /api/eval-status/{eval_id}` - Get evaluation status
- `GET /api/evaluations` - List evaluation history
- `POST /api/eval/{eval_id}/cancel` - Cancel a running evaluation (Celery only)
- `POST /api/eval/{eval_id}/kill` - Kill a running container
- `PATCH /api/eval/{eval_id}/status` - Admin endpoint to update status

### Platform Status Endpoints

- `GET /health` - Gateway health check
- `GET /api/status` - Overall platform status
- `GET /api/queue-status` - Queue system status
- `GET /api/celery-status` - Celery cluster status
- `GET /api/statistics` - Aggregated platform statistics

### Documentation Endpoints

- `GET /` - API root with endpoint listing
- `GET /docs` - Interactive API documentation (Swagger UI)
- `GET /redoc` - Alternative API documentation (ReDoc)
- `GET /api/openapi.yaml` - OpenAPI specification

### WebSocket Endpoints

- `WS /ws` - Real-time status updates

## Configuration

Environment variables:

```bash
# Service URLs
QUEUE_SERVICE_URL=http://queue:8081
STORAGE_SERVICE_URL=http://storage-service:8082
REDIS_URL=redis://redis:6379

# Database
DATABASE_URL=postgresql://crucible:password@postgres:5432/crucible

# Security
INTERNAL_API_KEY=dev-internal-api-key

# Celery Configuration
CELERY_ENABLED=true|false          # Enable Celery integration
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_PERCENTAGE=0.5              # Traffic split percentage (0.0-1.0)

# Other
LOG_LEVEL=INFO
ENABLE_CACHING=false
```

## Traffic Splitting

The API gateway implements a sophisticated traffic splitting mechanism for gradual migration:

```python
# 50/50 split between legacy queue and Celery
use_celery = (
    os.getenv('CELERY_ENABLED', 'false').lower() == 'true' and 
    random.random() < float(os.getenv('CELERY_PERCENTAGE', '0.5'))
)
```

### Migration Path
1. `CELERY_PERCENTAGE=0.1` - 10% to Celery (testing)
2. `CELERY_PERCENTAGE=0.5` - 50% to Celery (current)
3. `CELERY_PERCENTAGE=0.9` - 90% to Celery (validation)
4. `CELERY_PERCENTAGE=1.0` - 100% to Celery (full migration)

## Development

### Running Locally

```bash
# Install dependencies
cd api
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Run the service
python microservices_gateway.py
```

### Docker Build

```bash
docker build -f api/Dockerfile -t crucible-api-service .
```

### Testing

```bash
# Run unit tests
pytest tests/

# Test specific endpoint
curl -X POST http://localhost:8080/api/eval \
  -H "Content-Type: application/json" \
  -d '{"code": "print(\"Hello World\")", "language": "python"}'
```

## Service Communication

### Downstream Services

1. **Queue Service** (`http://queue:8081`)
   - Submit tasks to legacy queue
   - Get queue status

2. **Storage Service** (`http://storage-service:8082`)
   - Retrieve evaluation results
   - Get evaluation history
   - Update evaluation status

3. **Executor Services** (`http://executor-{n}:8083`)
   - Kill running containers (via storage service lookup)

4. **Celery** (via Redis broker)
   - Submit tasks to Celery queue
   - Get Celery task status
   - Cancel Celery tasks

### Event Publishing

The API publishes events to Redis channels for distributed processing:

- `evaluation:queued` - New evaluation submitted
- `evaluation:failed` - Evaluation failed to queue
- `evaluation:completed` - Evaluation completed
- `evaluation:cancelled` - Evaluation cancelled

## Error Handling

The API implements comprehensive error handling:

1. **Service Unavailable (503)**: When downstream services are unreachable
2. **Not Found (404)**: When evaluation doesn't exist
3. **Bad Gateway (502)**: When downstream service returns error
4. **Validation Errors (422)**: When request data is invalid

### Startup Grace Period

During the first 2 minutes after startup, the API retries connections to downstream services more frequently to handle service initialization order.

## Monitoring

### Health Checks

The API continuously monitors downstream services:
- Queue service health
- Storage service health
- Redis connectivity
- Executor availability

### Metrics

Track key metrics:
- Request count by endpoint
- Response times
- Error rates
- Queue depths
- Traffic split ratios

## Security

### Current Implementation
- Internal API key for service-to-service communication
- CORS configuration
- Request validation

### Planned Features
- JWT authentication
- Rate limiting per user
- API key management
- Request signing

## Deployment

### Docker Compose

```yaml
api-service:
  build:
    context: .
    dockerfile: api/Dockerfile
  environment:
    - CELERY_ENABLED=true
    - CELERY_PERCENTAGE=0.5
    - QUEUE_SERVICE_URL=http://queue:8081
    - STORAGE_SERVICE_URL=http://storage-service:8082
  depends_on:
    - queue
    - storage-service
    - redis
  ports:
    - "8080:8080"
```

### Production Considerations

1. **Load Balancing**: Deploy multiple instances behind a load balancer
2. **Caching**: Enable Redis caching for frequently accessed data
3. **Logging**: Configure structured logging for observability
4. **Tracing**: Implement distributed tracing for request flow
5. **Circuit Breakers**: Add circuit breakers for downstream services

## Troubleshooting

### Common Issues

1. **"Storage service unavailable"**
   - Check if storage-service is running
   - Verify STORAGE_SERVICE_URL is correct
   - Check network connectivity

2. **"Failed to submit to Celery"**
   - Verify Redis is running
   - Check CELERY_BROKER_URL
   - Ensure Celery workers are running

3. **WebSocket disconnections**
   - Check client network stability
   - Verify nginx WebSocket configuration
   - Check for proxy timeouts

### Debug Mode

Enable debug logging:
```bash
LOG_LEVEL=DEBUG python microservices_gateway.py
```

## API Examples

### Submit Evaluation

```bash
curl -X POST http://localhost:8080/api/eval \
  -H "Content-Type: application/json" \
  -d '{
    "code": "import time\nprint(\"Starting...\")\ntime.sleep(2)\nprint(\"Done!\")",
    "language": "python",
    "timeout": 30,
    "priority": false
  }'
```

Response:
```json
{
  "eval_id": "eval_20240701_120000_abc123",
  "status": "queued",
  "message": "Evaluation queued successfully",
  "queue_position": 0
}
```

### Get Evaluation Status

```bash
curl http://localhost:8080/api/eval-status/eval_20240701_120000_abc123
```

Response:
```json
{
  "eval_id": "eval_20240701_120000_abc123",
  "status": "completed",
  "created_at": "2024-07-01T12:00:00Z",
  "completed_at": "2024-07-01T12:00:05Z",
  "output": "Starting...\nDone!\n",
  "error": "",
  "success": true
}
```

### Cancel Celery Task

```bash
curl -X POST http://localhost:8080/api/eval/eval_20240701_120000_abc123/cancel?terminate=true
```

Response:
```json
{
  "eval_id": "eval_20240701_120000_abc123",
  "status": "cancelled",
  "message": "Task forcefully terminated"
}
```

## Future Enhancements

1. **Authentication & Authorization**
   - JWT token validation
   - Role-based access control
   - API key management

2. **Advanced Traffic Management**
   - A/B testing framework
   - Canary deployments
   - Feature flags

3. **Performance Optimization**
   - Response caching
   - Request batching
   - Connection pooling

4. **Enhanced Monitoring**
   - Prometheus metrics
   - OpenTelemetry tracing
   - Custom dashboards

## Contributing

1. Follow FastAPI best practices
2. Add tests for new endpoints
3. Update OpenAPI spec
4. Document configuration changes
5. Consider backward compatibility

## License

See main project LICENSE file.