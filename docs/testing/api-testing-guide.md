# API Testing Guide

## Environment Setup

### Docker Commands
- Use `docker compose` (not `docker-compose`) - it's the newer v2 syntax
- Port mapping:
  - Port 80: nginx (redirects to HTTPS)
  - Port 8000: nginx dev port (HTTP only, works for local testing)
  - Port 8082: storage service (direct access)
  - Port 5432: PostgreSQL
  - Port 6379: Redis
  - Port 5555: Flower (Celery monitoring)

### Service URLs
- API Gateway: `http://localhost:8000/api/`
- Storage Service: `http://localhost:8082/`
- Frontend: `http://localhost:8000/`

## Basic API Testing

### 1. Health Check
```bash
curl http://localhost:8000/health
```

### 2. Create Simple Evaluation
```bash
# Simple test without special characters
curl -X POST http://localhost:8000/api/eval \
  -H "Content-Type: application/json" \
  -d '{
    "code": "print(\"Hello World\")",
    "language": "python",
    "engine": "docker",
    "timeout": 30,
    "priority": false
  }'
```

### 3. Create Evaluation with Multi-line Code
```bash
# Using escaped newlines in JSON
curl -X POST http://localhost:8000/api/eval \
  -H "Content-Type: application/json" \
  -d '{
    "code": "print(\"Starting test\")\nfor i in range(3):\n    print(f\"Count: {i}\")\nprint(\"Done\")",
    "language": "python",
    "engine": "docker",
    "timeout": 30,
    "priority": true
  }'
```

### 4. Create Evaluation from File
```bash
# First create a JSON file
cat > /tmp/test-eval.json << 'EOF'
{
  "code": "import sys\nprint('Python version:', sys.version)\nfor i in range(5):\n    print(f'Number: {i}')",
  "language": "python",
  "engine": "docker",
  "timeout": 30,
  "priority": false
}
EOF

# Then send it
curl -X POST http://localhost:8000/api/eval \
  -H "Content-Type: application/json" \
  -d @/tmp/test-eval.json
```

### 5. Get Evaluation Details
```bash
# Replace eval_id with actual ID from creation response
EVAL_ID="eval_20250705_230905_19c35b09"
curl http://localhost:8000/api/eval/$EVAL_ID | python -m json.tool
```

### 6. Get Evaluation Status
```bash
curl http://localhost:8000/api/eval/$EVAL_ID/status
```

### 7. Get Evaluation Logs
```bash
curl http://localhost:8000/api/eval/$EVAL_ID/logs
```

## Batch Operations

### Create Multiple Evaluations
```bash
curl -X POST http://localhost:8000/api/eval-batch \
  -H "Content-Type: application/json" \
  -d '{
    "evaluations": [
      {
        "code": "print(\"First evaluation\")",
        "language": "python",
        "engine": "docker",
        "timeout": 30,
        "priority": false
      },
      {
        "code": "print(\"Second evaluation\")",
        "language": "python",
        "engine": "docker",
        "timeout": 30,
        "priority": true
      }
    ]
  }'
```

## Direct Storage Service Testing

### Get All Evaluations
```bash
curl http://localhost:8082/evaluations | python -m json.tool
```

### Get Specific Evaluation
```bash
curl http://localhost:8082/evaluations/$EVAL_ID | python -m json.tool
```

## Common Issues and Solutions

### JSON Escaping
- Use single quotes in Python code when using double quotes for JSON
- Or escape double quotes: `\"` 
- Or use a file with `@filename.json`

### Port Access
- If port 80 redirects to HTTPS, use port 8000 for HTTP testing
- Check if services are running: `docker compose ps`

### Service Health
```bash
# Check all services
docker compose ps

# Check specific service logs
docker compose logs storage-service
docker compose logs api-service

# Restart a service
docker compose restart storage-service
```

## Testing Checklist

After making changes:
1. Rebuild affected services: `docker compose build service-name`
2. Restart services: `docker compose restart service-name`
3. Check logs for errors: `docker compose logs -f service-name`
4. Test health endpoint first
5. Create a simple evaluation
6. Verify data is saved correctly

## Example Test Flow
```bash
# 1. Create evaluation
RESPONSE=$(curl -s -X POST http://localhost:8000/api/eval \
  -H "Content-Type: application/json" \
  -d '{"code": "print(\"Test\")", "language": "python", "engine": "docker", "timeout": 30, "priority": false}')

# 2. Extract eval_id
EVAL_ID=$(echo $RESPONSE | python -c "import sys, json; print(json.load(sys.stdin)['eval_id'])")

# 3. Wait for completion
sleep 3

# 4. Get full details
curl -s http://localhost:8000/api/eval/$EVAL_ID | python -m json.tool
```

## Verifying Code Storage

To check if code is being saved:
```bash
# Create evaluation and get ID
EVAL_ID="eval_..."  # Use actual ID

# Check if code field is present
curl -s http://localhost:8000/api/eval/$EVAL_ID | python -c "
import sys, json
data = json.load(sys.stdin)
print(f'Code field present: {\"code\" in data}')
print(f'Code is null: {data.get(\"code\") is None}')
if data.get('code'):
    print(f'Code length: {len(data[\"code\"])}')
"
```