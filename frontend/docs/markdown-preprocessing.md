# Markdown Documentation Preprocessing

## Overview

To improve build performance when dealing with many documentation files, we've implemented a preprocessing stage that parses markdown files during the Docker build process rather than at runtime during Next.js page generation.

## Problem

Next.js was timing out when building documentation pages:
```
Failed to build /docs/[...slug]/page: /docs/toast-component (attempt 1 of 3)
because it took more than 60 seconds. Retrying again shortly.
```

This occurred because:
- Each markdown file was being read and parsed during page generation
- Gray-matter parsing and frontmatter extraction happened on every build
- Multiple documentation pages were processed in parallel, consuming resources

## Solution

We added a dedicated preprocessing stage to the Docker build that:

1. **Parses all markdown files once** during the Docker build
2. **Caches the parsed content** as JSON
3. **Reuses the cache** during Next.js build

### Docker Changes

Added a new stage in `frontend/Dockerfile`:

```dockerfile
# Stage 2.5: Docs Preprocessor
FROM node:20-alpine AS docs-processor
WORKDIR /app
# Copy package files and install deps needed for markdown processing
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
# Copy scripts and docs
COPY frontend/scripts ./scripts
COPY docs/ ./docs/
COPY infrastructure/**/*.md ./infrastructure/
# Create preprocessing script if it doesn't exist
RUN mkdir -p scripts && cat > scripts/preprocess-docs.js << 'EOF'
const fs = require('fs');
const path = require('path');
const matter = require('gray-matter');
const crypto = require('crypto');

const docsDir = './docs';
const cacheDir = './.docs-cache';

// Create cache directory
if (!fs.existsSync(cacheDir)) {
  fs.mkdirSync(cacheDir, { recursive: true });
}

// Process all markdown files
function processMarkdownFiles(dir) {
  const files = fs.readdirSync(dir);
  const processed = {};
  
  files.forEach(file => {
    const filePath = path.join(dir, file);
    const stat = fs.statSync(filePath);
    
    if (stat.isDirectory()) {
      Object.assign(processed, processMarkdownFiles(filePath));
    } else if (file.endsWith('.md') || file.endsWith('.mdx')) {
      const content = fs.readFileSync(filePath, 'utf8');
      const { data, content: body } = matter(content);
      
      // Generate hash for caching
      const hash = crypto.createHash('md5').update(content).digest('hex');
      
      // Store processed data
      const relativePath = path.relative(docsDir, filePath);
      processed[relativePath] = {
        frontmatter: data,
        content: body,
        hash: hash,
        path: relativePath
      };
    }
  });
  
  return processed;
}

console.log('Preprocessing documentation files...');
const startTime = Date.now();

const processedDocs = processMarkdownFiles(docsDir);
fs.writeFileSync(
  path.join(cacheDir, 'processed-docs.json'),
  JSON.stringify(processedDocs, null, 2)
);

const endTime = Date.now();
console.log(`Preprocessed ${Object.keys(processedDocs).length} docs in ${endTime - startTime}ms`);
EOF
# Run preprocessing
RUN npm install gray-matter && node scripts/preprocess-docs.js
```

Then in the builder stage, we copy the preprocessed cache:

```dockerfile
# Copy preprocessed docs cache from docs-processor stage
COPY --from=docs-processor /app/.docs-cache ./.docs-cache

# Also increased the timeout as a safety measure
ENV NEXT_STATIC_PAGE_GENERATION_TIMEOUT=120
```

### Code Changes

Updated `frontend/lib/docs.ts` to use the preprocessed cache:

```typescript
// Preprocessed docs cache
interface ProcessedDoc {
  frontmatter: any;
  content: string;
  hash: string;
  path: string;
}

let docsCache: Record<string, ProcessedDoc> | null = null;

// Load preprocessed docs if available
function loadDocsCache(): Record<string, ProcessedDoc> {
  if (docsCache) return docsCache;
  
  const cacheFile = path.join(process.cwd(), '.docs-cache', 'processed-docs.json');
  
  try {
    if (fs.existsSync(cacheFile)) {
      console.log('[Docs] Using preprocessed documentation cache');
      docsCache = JSON.parse(fs.readFileSync(cacheFile, 'utf8'));
      return docsCache!;
    }
  } catch (error) {
    console.warn('[Docs] Failed to load preprocessed cache, falling back to runtime processing');
  }
  
  // Fallback to empty cache
  docsCache = {};
  return docsCache;
}
```

The `getDocBySlug` function now checks the cache first:

```typescript
export async function getDocBySlug(slug: string[]): Promise<Doc | null> {
  const filePath = slugToFilePath(slug)
  
  if (!filePath) {
    return null
  }
  
  // Check cache first
  const cache = loadDocsCache();
  const relativePath = path.relative(path.join(process.cwd(), 'docs'), filePath);
  const cachedDoc = cache[relativePath];
  
  if (cachedDoc) {
    // Use cached content
    data = cachedDoc.frontmatter;
    content = cachedDoc.content;
    // ... rest of processing
  } else {
    // Fallback to reading from filesystem
    const fileContent = fs.readFileSync(filePath, 'utf-8')
    const parsed = matter(fileContent)
    // ... rest of processing
  }
}
```

## Benefits

1. **Faster builds**: Markdown parsing happens once during Docker build, not during Next.js build
2. **Better caching**: If docs haven't changed, Docker reuses the cached preprocessing layer
3. **Reduced timeouts**: Less work during page generation means fewer timeouts
4. **Graceful fallback**: If cache isn't available, the system falls back to runtime processing

## How It Works

1. During Docker build, the `docs-processor` stage runs
2. It reads all markdown files and extracts frontmatter using gray-matter
3. Results are saved to `.docs-cache/processed-docs.json`
4. The main build stage copies this cache
5. At runtime, `lib/docs.ts` checks for the cache and uses it if available
6. If specific docs aren't in cache, it falls back to filesystem reading

## Files Modified

- `frontend/Dockerfile` - Added docs preprocessing stage, increased timeouts, reduced parallelism
- `frontend/lib/docs.ts` - Added cache loading and usage
- `frontend/scripts/preprocess-docs.js` - Script to preprocess markdown files
- `frontend/next.config.js` - Added timeout and parallelism settings
- `frontend/app/docs/[...slug]/page.tsx` - Limited pre-building to critical docs only

## Additional Optimizations Applied

1. **Increased timeouts**: Set to 240 seconds (4 minutes) to handle slow builds
2. **Reduced parallelism**: Limited to 2 CPUs to prevent resource exhaustion
3. **Selective pre-building**: Only pre-builds critical docs at build time (in both development and production):
   - `quickstart`
   - `README`
   - `architecture/overview`
   - `getting-started`
   
   All other docs are built on-demand when first accessed (Incremental Static Regeneration)

## Future Improvements

1. Cache additional computed values (reading time, last modified dates)
2. Support for MDX preprocessing
3. Incremental cache updates for changed files only
4. Move preprocessing script to a dedicated file instead of embedding in Dockerfile

## How to Revert

The TypeScript changes are very easy to undo if needed. The implementation is isolated and non-breaking:

### To fully revert:

1. **Remove the cache-related code** from `lib/docs.ts` (lines 6-35) - the interface and `loadDocsCache` function
2. **Revert `getDocBySlug`** to its original form - just remove the cache checking logic and restore the original implementation

### Partial revert option:

You can also:
1. Keep the Docker preprocessing stage (still helps with build layer caching)
2. But remove the TypeScript integration (so it doesn't use the cache at runtime)

This way you'd still get Docker build benefits without changing the runtime behavior.

### Why reverting is safe:

The changes are designed to be:
- **Non-invasive**: The cache is only checked if it exists
- **Backward compatible**: Falls back to original behavior if no cache
- **Easy to remove**: All cache logic is in one place
- **No data migration**: No database or persistent state changes