---
title: 'Type Generation Strategy'
order: 3
tags: ['typescript', 'build', 'docker']
---

# Type Generation Strategy

## The Challenge

- Want fresh types from API during build
- Docker builds are isolated
- Local `npm run build` CAN access localhost:8080
- Docker `npm run build` CANNOT access the API

---

## Solution: Context-Aware Commands

```json
{
  "scripts": {
    "build": "next build", // For Docker
    "build:local": "npm run generate-types && next build",
    "build:ci": "npm run generate-types && next build"
  }
}
```

---

## Development Workflow

1. **API changes** → Backend developer updates endpoint
2. **Generate types** → `npm run generate-types`
3. **Type checking** → TypeScript catches mismatches
4. **Fix & ship** → Update frontend to match

---

## Best Practices

- Commit generated types
- CI verifies types match API
- Docker uses committed types
- Developers regenerate when needed
