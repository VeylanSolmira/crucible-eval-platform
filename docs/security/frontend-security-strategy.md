# Frontend Security Strategy

## Overview
This document outlines our frontend security approach, balancing modern security features with broad accessibility for AI safety researchers.

## ECMAScript Target Decision

### Chosen Target: ES2020
We target ES2020 for the following security and compatibility reasons:

**Security Features Gained:**
- Optional chaining (`?.`) - Prevents runtime errors from null/undefined access
- Nullish coalescing (`??`) - Explicit handling of null/undefined vs falsy values
- BigInt - Prevents integer overflow in cryptographic operations
- Promise.allSettled() - Better error handling in concurrent operations
- Dynamic imports - Lazy loading reduces attack surface

**Compatibility:**
- 92% global browser support
- Includes all browsers from 2021 onwards
- Covers enterprise and institutional environments

### TypeScript Configuration

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "strictFunctionTypes": true,
    "strictBindCallApply": true,
    "strictPropertyInitialization": true,
    "noImplicitThis": true,
    "useUnknownInCatchVariables": true,
    "alwaysStrict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitOverride": true,
    "allowUnreachableCode": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "forceConsistentCasingInFileNames": true,
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [
      {
        "name": "next"
      }
    ],
    "paths": {
      "@/*": ["./*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

### Security-Specific Compiler Options Explained

1. **`strictNullChecks`**: Forces explicit handling of null/undefined
   ```typescript
   // Prevents: Cannot read property 'x' of undefined
   const value = data?.property?.nested ?? defaultValue;
   ```

2. **`noUncheckedIndexedAccess`**: Makes array/object access return T | undefined
   ```typescript
   const arr = [1, 2, 3];
   const item = arr[10]; // Type is: number | undefined
   if (item !== undefined) {
     // Safe to use item
   }
   ```

3. **`useUnknownInCatchVariables`**: Catch variables are `unknown` not `any`
   ```typescript
   try {
     riskyOperation();
   } catch (e) {
     // e is 'unknown', must be validated
     if (e instanceof Error) {
       console.error(e.message);
     }
   }
   ```

4. **`exactOptionalPropertyTypes`**: Distinguishes undefined from missing
   ```typescript
   interface Config {
     timeout?: number; // Can be undefined OR missing
   }
   // Prevents passing { timeout: undefined } when expecting missing property
   ```

## Browser Compatibility Strategy

### Browserslist Configuration

Create `.browserslistrc`:
```
# Browsers we support
last 2 years        # All browsers updated in last 2 years
not dead           # Exclude browsers with no updates
> 0.5%             # Used by more than 0.5% of users
not op_mini all    # Opera Mini doesn't support modern JS
```

This configuration is used by:
- Babel (for transpilation)
- Autoprefixer (for CSS)
- ESLint (for compatibility warnings)

### What This Covers (as of 2024):
- Chrome 100+ (Feb 2022)
- Firefox 98+ (Mar 2022)
- Safari 15.4+ (Mar 2022)
- Edge 100+ (Mar 2022)
- Samsung Internet 17+ (Apr 2022)

### Polyfills Explained

**What is a polyfill?**
A polyfill is JavaScript code that implements newer features for older browsers.

**Example:**
```javascript
// ES2022 feature: Array.prototype.at()
const arr = [1, 2, 3];
const last = arr.at(-1); // Gets last element

// Polyfill for older browsers:
if (!Array.prototype.at) {
  Array.prototype.at = function(index) {
    if (index < 0) index = this.length + index;
    return this[index];
  };
}
```

**How we use polyfills:**
```javascript
// In your app entry point:
import 'core-js/stable';  // Polyfills for stable features
import 'regenerator-runtime/runtime'; // Async/await for older browsers

// Or selective polyfills:
import 'core-js/features/array/at';
import 'core-js/features/string/replace-all';
```

**Next.js automatic polyfilling:**
```javascript
// next.config.js
module.exports = {
  experimental: {
    // Next.js only includes polyfills for features you actually use
    // This keeps bundle size small
    optimizeCss: true,
    legacyBrowsers: false, // Set true if you need IE11 support
  },
};
```

## Security Features by ECMAScript Version

### Features We Get with ES2020:
1. **Optional Chaining** - Prevents property access errors
2. **Nullish Coalescing** - Explicit null handling
3. **BigInt** - Safe large number operations
4. **Dynamic Import** - Lazy load code (smaller attack surface)
5. **globalThis** - Consistent global access

### Features We Polyfill from ES2021+:
1. **String.replaceAll()** - Safer than regex replace
2. **Promise.any()** - Better concurrent error handling
3. **Logical Assignment** - Clearer intention
4. **Array.at()** - Safe negative indexing

### Features We Use via TypeScript (Compile-Time):
1. **Private Fields (#)** - Compiled to WeakMaps for older browsers
2. **Type Guards** - Runtime type checking
3. **Const Assertions** - Immutable types

## Implementation Examples

### Safe Data Access Pattern
```typescript
// utils/safe-access.ts
export function safeGet<T>(
  obj: unknown,
  path: string[],
  defaultValue: T
): T {
  try {
    let current: any = obj;
    for (const key of path) {
      current = current?.[key];
      if (current === undefined) {
        return defaultValue;
      }
    }
    return current as T;
  } catch {
    return defaultValue;
  }
}

// Usage:
const timeout = safeGet(config, ['api', 'timeout'], 5000);
```

### Input Validation Pattern
```typescript
// utils/validation.ts
import { z } from 'zod';

export const EvaluationSchema = z.object({
  code: z.string().min(1).max(100000),
  language: z.enum(['python', 'javascript']),
  timeout: z.number().min(1).max(300),
  memoryLimit: z.number().min(128).max(4096),
});

export function validateInput<T>(
  schema: z.ZodSchema<T>,
  data: unknown
): T | null {
  try {
    return schema.parse(data);
  } catch (error) {
    console.error('Validation failed:', error);
    return null;
  }
}
```

### XSS Prevention Pattern
```typescript
// utils/sanitize.ts
import DOMPurify from 'isomorphic-dompurify';

export function sanitizeHTML(dirty: string): string {
  return DOMPurify.sanitize(dirty, {
    ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'code', 'pre'],
    ALLOWED_ATTR: [],
  });
}

export function sanitizeText(text: string): string {
  return text
    .replace(/[<>]/g, '') // Remove potential HTML
    .trim()
    .slice(0, 10000); // Limit length
}
```

## Next Steps

1. Update tsconfig.json with our security-focused configuration
2. Add .browserslistrc for consistent browser targeting
3. Install necessary polyfills
4. Set up runtime validation with Zod
5. Configure Content Security Policy headers
6. Implement input sanitization utilities

## References

- [TypeScript Compiler Options](https://www.typescriptlang.org/tsconfig)
- [Browserslist](https://github.com/browserslist/browserslist)
- [Core-js Polyfills](https://github.com/zloirock/core-js)
- [MDN Browser Compatibility](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference)