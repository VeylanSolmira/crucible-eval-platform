# Type Separation Architecture Proposal

## Problem Statement

Currently, TypeScript gets shared domain types (like EvaluationStatus) through the OpenAPI spec, creating a 45-minute process for simple type changes. This violates the principle that shared types should be independently consumable by each codebase.

## Proposed Architecture

### 1. Type Categories

**Shared Domain Types** (`/shared/types/`)
- Core business concepts used across services
- Examples: EvaluationStatus, Event contracts
- Source: YAML files
- Consumers: All services read YAML directly

**API Contract Types** 
- Request/Response models owned by the API
- Examples: EvaluationRequest, EvaluationResponse
- Source: Python Pydantic models
- Consumers: Frontend via OpenAPI

### 2. Generation Flow

```
Shared YAML → Python generator → /shared/generated/python/
            → TypeScript generator → /shared/generated/typescript/

API Python → FastAPI → OpenAPI → /frontend/types/generated/api.ts
```

### 3. Import Strategy

**Frontend imports:**
```typescript
// Shared domain types - from YAML
import { EvaluationStatus, isTerminalStatus } from '@/shared/generated/typescript/evaluation-status'

// API contract types - from OpenAPI
import type { EvaluationRequest, EvaluationResponse } from '@/types/generated/api'
```

**Python imports:**
```python
# Shared domain types - from YAML
from shared.generated.python import EvaluationStatus

# API types defined locally
from .models import EvaluationRequest, EvaluationResponse
```

## Implementation Steps

### Phase 1: Create TypeScript Generator (Immediate)

1. Complete `/shared/scripts/generate-typescript-types.js`
   - Read all YAML files in `/shared/types/`
   - Generate TypeScript with full metadata
   - Output to `/shared/generated/typescript/`

2. Update frontend to use shared types
   - Add path alias in tsconfig: `"@/shared/*": ["../shared/*"]`
   - Update imports to use shared types
   - Remove hardcoded terminal state arrays

### Phase 2: Clean OpenAPI Generation (Future)

1. Configure OpenAPI generation to exclude shared domain types
   - Use OpenAPI `$ref` to external schemas
   - Or post-process to remove duplicates

2. Update frontend type imports
   - Shared types from `@/shared/generated/typescript/`
   - API types from `@/types/generated/api`

### Phase 3: Automation (Future)

1. Add watch mode to generators
2. Create unified generation command
3. Add pre-commit hooks

## Benefits

1. **Fast type changes**: Edit YAML → Run generators → Done (2 minutes vs 45)
2. **True separation**: Frontend doesn't depend on Python/API for domain types
3. **Type safety**: Full metadata (terminal states) preserved
4. **Clear ownership**: Obvious which types are shared vs API-specific

## Risks & Mitigations

**Risk**: Import confusion between shared and API types
**Mitigation**: Clear naming conventions and import paths

**Risk**: Type version mismatch
**Mitigation**: Generate timestamp/version in files

**Risk**: Breaking existing code
**Mitigation**: Gradual migration, keep old imports working initially

## Success Criteria

1. Adding a new evaluation status takes < 5 minutes
2. TypeScript has full access to type metadata (terminal states)
3. No manual updates required in TypeScript code
4. Clear separation between shared and API types