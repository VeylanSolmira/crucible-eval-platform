# Frontend Development Guidelines

## TypeScript Standards

### ZERO TYPE DEBT POLICY
We maintain strict TypeScript standards from day one to prevent technical debt accumulation.

### Rules:
1. **NO `any` types** - Every variable, parameter, and return value must be explicitly typed
2. **NO `@ts-ignore`** - Fix the issue, don't suppress it
3. **NO implicit anys** - Enable `noImplicitAny` in tsconfig
4. **Strict mode ON** - All strict checks enabled

### Type Guidelines:

#### 1. API Responses
```typescript
// ❌ BAD
const data = await response.json()

// ✅ GOOD
interface ApiResponse<T> {
  data?: T
  error?: string
  status: number
}

const response = await fetch('/api/eval')
const data: ApiResponse<EvaluationResult> = await response.json()
```

#### 2. Event Handlers
```typescript
// ❌ BAD
onChange={(e) => setValue(e.target.value)}

// ✅ GOOD
onChange={(e: React.ChangeEvent<HTMLInputElement>) => setValue(e.target.value)}
```

#### 3. Component Props
```typescript
// ❌ BAD
function Button({onClick, children}) { ... }

// ✅ GOOD
interface ButtonProps {
  onClick: () => void
  children: React.ReactNode
  disabled?: boolean
}

function Button({ onClick, children, disabled = false }: ButtonProps) { ... }
```

#### 4. State Types
```typescript
// ❌ BAD
const [data, setData] = useState(null)

// ✅ GOOD
const [data, setData] = useState<EvaluationResult | null>(null)
```

### Type Organization:
- `/types/api.ts` - API request/response types
- `/types/models.ts` - Domain models
- `/types/ui.ts` - UI component prop types
- Component-specific types stay with components

### Benefits:
1. **Catch errors at compile time** - Not in production
2. **Better IDE support** - Autocomplete and refactoring
3. **Self-documenting code** - Types serve as documentation
4. **Easier refactoring** - Compiler helps find all usages
5. **Team scalability** - New developers understand the codebase faster

## Next.js Best Practices

### App Router (v14+)
- Use App Router, not Pages Router
- Server Components by default
- 'use client' only when needed
- Metadata API for SEO

### Performance
- Image optimization with next/image
- Font optimization with next/font
- Static generation where possible
- API route caching

### Security
- Environment variables properly scoped
- NEXT_PUBLIC_ prefix for client variables
- Content Security Policy headers
- Input validation on all forms

## Component Guidelines

### Structure
```typescript
// 1. Imports
import { useState, useEffect } from 'react'
import type { ComponentProps } from '@/types/ui'

// 2. Types
interface Props extends ComponentProps {
  // ...
}

// 3. Component
export function Component({ prop1, prop2 }: Props) {
  // 4. State
  const [state, setState] = useState<StateType>(initial)
  
  // 5. Effects
  useEffect(() => {
    // ...
  }, [deps])
  
  // 6. Handlers
  const handleClick = () => {
    // ...
  }
  
  // 7. Render
  return <div>...</div>
}
```

### Naming Conventions
- Components: PascalCase
- Files: kebab-case
- Types/Interfaces: PascalCase
- Functions: camelCase
- Constants: UPPER_SNAKE_CASE

## Testing Strategy
- Unit tests for utilities
- Component tests with React Testing Library
- E2E tests for critical flows
- Type tests with tsd

## Remember
**Every line of code is an opportunity to add type safety. Take it.**