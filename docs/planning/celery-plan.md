 Based on what we've built so far, here are the
  next steps for Celery integration:

  Next Steps for Celery Integration

  1. Test Basic Celery Setup (First Priority)

  # Start the Celery stack
  docker-compose -f docker-compose.yml -f
  docker-compose.celery.yml up -d

  # Check if services are running
  docker ps | grep celery

  # Test with the test script
  cd celery-worker
  python test_celery.py

  2. Fix Any Issues with Current Setup

  - Ensure Celery worker can connect to Redis
  - Verify Flower dashboard is accessible at
  http://localhost:5555
  - Check logs: docker logs 
  crucible-celery-worker

  3. Integrate celery_client.py into API

  We need to modify the API service to actually
  use the celery_client.py:

  # In api/microservices_gateway.py, add at top:
  from app.celery_client import
  submit_evaluation_to_celery, get_celery_status

  # In the evaluate endpoint (around line 287), 
  add:
  # After the queue service call succeeds
  celery_task_id = submit_evaluation_to_celery(
      eval_id=eval_id,
      code=request.code,
      language=request.language,
      priority=False
  )

  if celery_task_id:
      logger.info(f"Dual-write successful: 
  {eval_id} submitted to both systems")

  4. Update Docker Compose for API

  Add Celery environment variables to
  api-service:
  # In docker-compose.yml
  api-service:
    environment:
      - CELERY_ENABLED=true
      -
  CELERY_BROKER_URL=redis://celery-redis:6379/0

  5. Create Mock Executor for Testing

  Since Celery worker expects to call executor
  service, create a simple mock:
  # celery-worker/mock_executor.py
  from fastapi import FastAPI
  app = FastAPI()

  @app.post("/execute")
  async def execute(request: dict):
      return {
          "output": f"Mock execution of: 
  {request.get('code', '')[:50]}...",
          "error": "",
          "execution_time": 0.1
      }

  6. Test End-to-End Flow

  # Submit a test evaluation
  curl -X POST http://localhost:8000/api/eval \
    -H "Content-Type: application/json" \
    -d '{"code": "print(\"Hello from Celery!\")",
   "language": "python"}'

  # Check Flower dashboard to see task
  # Check logs to verify dual-write

  7. Add Monitoring Endpoints

  # Add to api/microservices_gateway.py
  @app.get("/api/celery-status")
  async def celery_status():
      """Get Celery integration status"""
      return get_celery_status()

  8. Implement Comparison Testing

  Create a script to submit same tasks to both
  systems and compare:
  - Execution time
  - Success rate
  - Result consistency

  9. Production Readiness

  - Add Celery to main docker-compose.yml (not
  just overlay)
  - Configure proper resource limits
  - Set up log rotation
  - Add health checks

  10. Documentation Updates

  - Update README with Celery setup instructions
  - Document the dual-write pattern
  - Add troubleshooting guide

  Immediate Action Items

  1. Start Celery services and verify they're 
  running
  2. Run test_celery.py to ensure basic 
  functionality
  3. Add the import and dual-write code to 
  microservices_gateway.py
  4. Test an actual evaluation through the API

  The key is to start small - just get one
  evaluation flowing through both systems
  successfully, then build from there.