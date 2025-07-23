# Multi-stage build for Next.js frontend with type generation

# Base stage with dependencies - reused by other stages
FROM node:20-alpine AS deps
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
# Use cache mount for npm cache
RUN --mount=type=cache,target=/root/.npm \
    npm ci --prefer-offline --no-audit

# Stage 1: Docs Preprocessor (uses deps)
FROM deps AS docs-processor
WORKDIR /app
# Copy scripts and docs
COPY frontend/scripts ./scripts
COPY docs/ ./docs/
COPY infrastructure/**/*.md ./infrastructure/
# Run preprocessing (gray-matter should be in package.json)
RUN node scripts/preprocess-docs.js

# Stage 2: Shared Types Generator (uses deps)
FROM deps AS shared-types-generator
WORKDIR /app
# Copy shared types and scripts
COPY shared/types ./shared/types
COPY shared/scripts ./shared/scripts
# Generate TypeScript types from YAML
RUN NODE_PATH=./node_modules node shared/scripts/generate-typescript-types.js

# Stage 2.5: OpenAPI specs (separate stage for better caching)
FROM alpine AS openapi-specs
WORKDIR /specs
COPY api/openapi.yaml /specs/api-openapi.yaml
COPY storage_service/openapi.yaml /specs/storage-openapi.yaml

# Stage 3: Builder (uses deps)
FROM deps AS builder
WORKDIR /app
COPY frontend/ .

# Copy documentation from root directory
COPY docs/ ./docs/

# Copy only markdown files from infrastructure, preserving paths
COPY infrastructure/**/*.md ./infrastructure/

# Create types directory
RUN mkdir -p ./types/generated

# Copy OpenAPI specs from the separate stage
# This way, if OpenAPI content hasn't changed, Docker reuses the cached layer
COPY --from=openapi-specs /specs/api-openapi.yaml /api/openapi.yaml
COPY --from=openapi-specs /specs/storage-openapi.yaml /storage_service/openapi.yaml

# Copy shared generated types from shared-types-generator stage
COPY --from=shared-types-generator /app/shared/generated/typescript ./shared/generated/typescript

# Copy preprocessed docs cache from docs-processor stage
COPY --from=docs-processor /app/.docs-cache ./.docs-cache

# Ensure lib/templates directory is included
# (This is already copied by COPY frontend/ . but let's be explicit)
RUN ls -la lib/templates || echo "Templates directory missing!"

ENV NEXT_TELEMETRY_DISABLED=1
# Increase timeout and reduce parallelism for docs build
ENV NEXT_STATIC_PAGE_GENERATION_TIMEOUT=240
# Reduce concurrent builds to prevent resource exhaustion
ENV NEXT_EXPERIMENTAL_WORKER_THREADS=false
ENV NEXT_EXPERIMENTAL_CPUS=2
ARG API_URL
ENV API_URL=${API_URL}
# Use cache mount for Next.js cache
RUN --mount=type=cache,target=/app/.next/cache \
    npm run build

# Stage 4: Runner
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Copy lib/templates for runtime access
COPY --from=builder --chown=nextjs:nodejs /app/lib/templates ./lib/templates

# Copy docs for runtime access
COPY --from=builder --chown=nextjs:nodejs /app/docs ./docs

# Copy infrastructure markdown files for runtime access
COPY --from=builder --chown=nextjs:nodejs /app/infrastructure ./infrastructure

USER nextjs
EXPOSE 3000
ENV PORT=3000

CMD ["node", "server.js"]