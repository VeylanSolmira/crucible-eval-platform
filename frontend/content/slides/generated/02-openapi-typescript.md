---
title: "OpenAPI + TypeScript Integration"
order: 2
tags: ["typescript", "openapi", "api"]
---

# OpenAPI + TypeScript Integration

## The Problem

Without type safety between frontend and backend:

```typescript
// Frontend code - we're just guessing!
const response = await fetch('/api/eval-status/123')
const data = await response.json()

// Will this work? Who knows!
console.log(data.result.output)  // Maybe it's data.output?
```

---

## The Solution

With OpenAPI + TypeScript:

```typescript
// TypeScript knows EXACTLY what the API returns
const { data } = await apiClient.getEvaluationStatus('123')
if (data) {
  console.log(data.output)   // ✅ TypeScript knows this exists
  console.log(data.resultado) // ❌ Type error!
}
```

---

## How It Works

1. **Backend exposes OpenAPI spec**
   - Available at: `/api/openapi.json`
   - Auto-generated from FastAPI

2. **Frontend generates types**
   ```bash
   npm run generate-types
   ```

3. **Use type-safe client**
   ```typescript
   import { apiClient } from '@/lib/api/client'
   ```

---

## Benefits

- **Catch errors at build time**
- **IDE auto-completion**
- **Refactoring safety**
- **Living documentation**
- **API contract enforcement**