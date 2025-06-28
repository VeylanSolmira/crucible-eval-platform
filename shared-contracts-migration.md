# Shared Contracts Migration Checklist

## Overview
This checklist tracks the migration to shared contracts across all services in the metr-eval-platform. The goal is to establish a single source of truth for types, statuses, and constants used across the distributed system.

## Contract Categories

### DEFINITELY SHARED/CORE ✅
These are fundamental domain concepts that MUST be consistent across all services:
- **EvaluationStatus enum** - The core state machine (queued, running, completed, failed)
- **Event names/channels** - Inter-service communication contracts
- **Event payload schemas** - What data flows between services
- **Resource limits** - Security-critical constraints (memory, CPU, output size)
- **Base error format** - Consistent error structure for debugging
- **Evaluation ID format** - How we identify evaluations everywhere

### DEFINITELY SERVICE-OWNED ❌
These should remain within individual services:
- **Service health check details** - Each service's internal health metrics
- **Internal configuration** - Service-specific settings
- **Implementation details** - How each service accomplishes its work
- **Service-specific error messages** - Detailed internal errors
- **Database models** - Storage service owns the schema
- **Docker implementation** - Executor service owns container details

### AMBIGUOUS/NEEDS ANALYSIS 🤔
These could go either way and need discussion:
- **EvaluationRequest full model** - Core fields shared, extensions service-specific?
- **Timeout values** - System-wide policy or service-configurable?
- **QueueStatusResponse** - Queue internals or system-wide visibility?
- **Language/Engine enums** - Shared for validation or executor-owned?
- **Retry policies** - System-wide or per-service?
- **API response formats** - Standardize or let services decide?

## Migration Focus: SHARED/CORE Only
We'll focus on the definitely shared items first, then revisit ambiguous items.

## Streamlined Implementation Plan for CORE Contracts

### Step 1: Create Shared Structure
- [x] Create `/shared/` directory
- [x] Create `/shared/types/` directory  
- [x] Create `/shared/constants/` directory
- [x] Create `/shared/docker/` directory
- [x] Create `/shared/generated/` directory
- [x] Move `base.Dockerfile` to `/shared/docker/`

### Step 2: Define Core Contracts
- [x] Create `shared/types/evaluation-status.yaml` with status enum
- [x] Create `shared/types/event-contracts.yaml` with event schemas
- [x] Create `shared/constants/limits.yaml` with security limits
- [x] Create `shared/constants/events.yaml` with channel names

### Step 3: Update Python Services to Use Enum
Focus on status enum first (highest impact):
- [x] Update `api/microservices_gateway.py` - Add enum, update models
- [x] Export new OpenAPI spec: `python api/scripts/export-openapi-spec.py`
- [x] Regenerate frontend types: `cd frontend && npm run generate-types`
- [x] Update frontend polling to use generated enum values

### Step 4: Verify Fix
- [x] Test evaluation submission
- [x] Verify status transitions work
- [x] Confirm execution time is back to ~3 seconds

### Step 5: Expand to Other Services ✅ COMPLETED
Once working in API/Frontend:
- [x] Apply pattern to queue-service
- [x] Apply pattern to storage-service
- [x] Apply pattern to executor-service (returns execution results, not evaluation statuses)
- [x] Apply pattern to storage-worker
- [x] Apply pattern to queue-worker (routes executor results, doesn't use evaluation statuses)

## Phase 1: Discovery & Inventory

### Status Values Inventory
- [ ] Search all Python files for status assignments/comparisons
  - [ ] `grep -r "status.*=" --include="*.py" .`
  - [ ] `grep -r "status.*==" --include="*.py" .`
  - [ ] Document every unique status value found
- [ ] Search all TypeScript files for status checks
  - [ ] `grep -r "status" --include="*.ts" --include="*.tsx" frontend/`
  - [ ] Document all status string literals
- [ ] Search database migrations for status columns
  - [ ] Check `storage/database/models.py`
  - [ ] Check migration files
- [ ] Create final list of canonical status values

### Event Types Inventory
- [ ] Redis pub/sub channels used
  - [ ] Search for `publish(` in Python files
  - [ ] Search for `subscribe(` in Python files
- [ ] Event names/types
  - [ ] Document all event string literals
  - [ ] Map which services publish each event
  - [ ] Map which services subscribe to each event
- [ ] Event payload structures
  - [ ] Document the data structure for each event type

### Shared Data Models Inventory
- [ ] EvaluationRequest variations
  - [ ] Compare across all services
  - [ ] Note any differences
- [ ] Response models
  - [ ] EvaluationResponse
  - [ ] EvaluationStatusResponse
  - [ ] QueueStatusResponse
- [ ] Error formats
  - [ ] HTTPException responses
  - [ ] Service-specific errors
- [ ] Health check formats
  - [ ] Compare health endpoints across services

### Constants Inventory
- [ ] Timeouts
  - [ ] Container execution timeout
  - [ ] API request timeouts
  - [ ] Queue polling intervals
- [ ] Resource limits
  - [ ] Memory limits (containers, services)
  - [ ] CPU limits
  - [ ] Output size limits
- [ ] Retry logic
  - [ ] Retry counts
  - [ ] Backoff strategies
- [ ] Service URLs and ports

## Phase 2: Design Shared Contracts

### Create Folder Structure
- [ ] Create `/shared/` directory
- [ ] Create `/shared/types/` directory
- [ ] Create `/shared/generated/` directory
- [ ] Create `/shared/constants/` directory
- [ ] Create `/shared/docker/` directory
- [ ] Update `.gitignore` for generated files
  - [ ] Add `/shared/generated/`
- [ ] Move `base.Dockerfile` to `/shared/docker/`

### Design OpenAPI Shared Schemas (CORE ONLY)
- [ ] ✅ Create `shared/types/evaluation-status.yaml`
  ```yaml
  components:
    schemas:
      EvaluationStatus:
        type: string
        enum: [queued, running, completed, failed]
  ```
- [ ] ✅ Create `shared/types/event-models.yaml`
  - [ ] EvaluationCompletedEvent
  - [ ] EvaluationFailedEvent
  - [ ] EvaluationQueuedEvent
  - [ ] EvaluationStartedEvent
- [ ] ✅ Create `shared/types/core-models.yaml`
  - [ ] EvaluationId (format specification)
  - [ ] BaseError (consistent error structure)
- [ ] 🤔 Create `shared/types/evaluation-models.yaml` (PARTIAL)
  - [ ] Core fields only (id, status, timestamps)
  - [ ] Skip service-specific fields
- [ ] ❌ ~~Create `shared/types/common-types.yaml`~~ (SERVICE-OWNED)
  - [ ] Language enum → Executor service owns
  - [ ] ExecutionEngine enum → Executor service owns
- [ ] ❌ ~~Create `shared/types/health-models.yaml`~~ (SERVICE-OWNED)
  - [ ] Each service defines its own health response

### Design Constants Structure (CORE ONLY)
- [ ] ✅ Create `shared/constants/limits.yaml` (SECURITY-CRITICAL)
  ```yaml
  execution:
    max_timeout_seconds: 300
    max_memory_mb: 512
    max_output_size_bytes: 1048576
    max_cpu_cores: 0.5
  ```
- [ ] ✅ Create `shared/constants/events.yaml` (INTER-SERVICE CONTRACTS)
  ```yaml
  channels:
    evaluation_queued: "evaluation:queued"
    evaluation_started: "evaluation:started"  
    evaluation_completed: "evaluation:completed"
    evaluation_failed: "evaluation:failed"
  ```
- [ ] 🤔 ~~Create `shared/constants/timeouts.yaml`~~ (POSSIBLY SERVICE-SPECIFIC)

## Phase 3: Update Build Infrastructure

### Update Dockerfiles
- [ ] Update `docker-compose.yml`
  - [ ] Update base service build context to `./shared/docker`
  - [ ] Add shared volume mapping for all services
- [ ] Update `api/Dockerfile`
  - [ ] Add COPY command for shared types
  - [ ] Update FROM reference if needed
- [ ] Update `queue-service/Dockerfile`
- [ ] Update `queue-worker/Dockerfile`
- [ ] Update `executor-service/Dockerfile`
- [ ] Update `storage-service/Dockerfile`
- [ ] Update `storage-worker/Dockerfile`
- [ ] Update `frontend/Dockerfile`

### Create Generation Scripts
- [ ] Create `shared/scripts/generate-python-types.sh`
  - [ ] Use datamodel-code-generator or similar
  - [ ] Output to `shared/generated/python/`
- [ ] Create `shared/scripts/generate-typescript-types.sh`
  - [ ] Use openapi-typescript
  - [ ] Output to `shared/generated/typescript/`
- [ ] Add generation commands to each service
  - [ ] Python services: Add to requirements.txt
  - [ ] Frontend: Add to package.json scripts

## Phase 4: Service Migration

### API Service (microservices_gateway.py)
- [ ] Update imports to use shared types
- [ ] Replace status string literals with enums
- [ ] Update OpenAPI spec generation
- [ ] Test service starts correctly
- [ ] Run integration tests

### Queue Service
- [ ] Update imports to use shared types
- [ ] Replace status string literals with enums
- [ ] Update queue status response
- [ ] Test service starts correctly

### Queue Worker
- [ ] Update imports to use shared types
- [ ] Update event publishing to use shared event names
- [ ] Replace status handling
- [ ] Test task routing

### Executor Service
- [ ] Update imports to use shared types
- [ ] Update execution status returns
- [ ] Test container execution

### Storage Service
- [ ] Update imports to use shared types
- [ ] Update database queries to use enums
- [ ] Test CRUD operations

### Storage Worker
- [ ] Update imports to use shared types
- [ ] Update event subscriptions
- [ ] Test event processing

## Phase 5: Frontend Migration

### Update Type Generation
- [ ] Update `frontend/package.json` generate-types script
- [ ] Point to shared OpenAPI schemas
- [ ] Regenerate all types
- [ ] Update imports in TypeScript files

### Update React Query Hooks
- [ ] Update `useEvaluation.ts`
  - [ ] Import generated status enum
  - [ ] Update status comparisons
  - [ ] Remove hardcoded strings
- [ ] Update all other hooks similarly

### Update Components
- [ ] Update status badges/displays
- [ ] Update conditional rendering based on status
- [ ] Search and replace all status string literals

## Phase 6: Testing & Validation

### End-to-End Testing
- [ ] Submit single evaluation
  - [ ] Verify status transitions: queued → running → completed
  - [ ] Check frontend updates in real-time
- [ ] Submit batch evaluation
  - [ ] Verify all evaluations process
  - [ ] Check status updates for each
- [ ] Test failure scenarios
  - [ ] Timeout handling
  - [ ] Error propagation

### Cross-Service Testing
- [ ] Verify event flow
  - [ ] API → Queue → Worker → Executor → Storage
- [ ] Check status consistency across services
- [ ] Verify error handling between services

### Performance Testing
- [ ] Measure execution time (should still be ~3 seconds)
- [ ] Verify polling efficiency
- [ ] Check for memory leaks

## Phase 7: Documentation

### Update API Documentation
- [ ] Regenerate OpenAPI spec with shared refs
- [ ] Update API endpoint documentation
- [ ] Document status values and transitions

### Developer Guide
- [ ] Document how to add new shared types
- [ ] Document type generation process
- [ ] Create troubleshooting guide

### Architecture Documentation
- [ ] Update system diagrams
- [ ] Document shared contracts pattern
- [ ] Create ADR (Architecture Decision Record)

## Phase 8: CI/CD Updates

### GitHub Actions
- [ ] Add shared type validation
- [ ] Add generation step to build pipeline
- [ ] Update deployment scripts

### Pre-commit Hooks
- [ ] Add check for hardcoded status strings
- [ ] Validate OpenAPI schemas
- [ ] Ensure generated types are up to date

## Phase 9: Cleanup

### Remove Old Code
- [ ] Remove local type definitions
- [ ] Remove hardcoded constants
- [ ] Clean up duplicate schemas

### Final Validation
- [ ] All services running
- [ ] All tests passing
- [ ] No hardcoded strings remaining
- [ ] Documentation complete

## Success Criteria
- [ ] Zero hardcoded status strings in codebase
- [ ] All services use shared contracts
- [ ] Frontend polls with correct statuses
- [ ] Execution time back to ~3 seconds
- [ ] All tests passing