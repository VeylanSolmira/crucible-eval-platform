# Multi-stage build for Next.js frontend with type generation

# Stage 1: Docs Preprocessor
FROM node:20-alpine AS docs-processor
WORKDIR /app
# Copy package files and install deps needed for markdown processing
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
# Copy scripts and docs
COPY frontend/scripts ./scripts
COPY docs/ ./docs/
COPY infrastructure/**/*.md ./infrastructure/
# Run preprocessing
RUN npm install gray-matter && node scripts/preprocess-docs.js

# Stage 2: Shared Types Generator
FROM node:20-alpine AS shared-types-generator
WORKDIR /app
# Copy package files for js-yaml dependency
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
# Copy shared types and scripts
COPY shared/types ./shared/types
COPY shared/scripts ./shared/scripts
# Generate TypeScript types from YAML
RUN NODE_PATH=./node_modules node shared/scripts/generate-typescript-types.js

# Stage 3: Builder
FROM node:20-alpine AS builder
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ .

# Copy documentation from root directory
COPY docs/ ./docs/

# Copy only markdown files from infrastructure, preserving paths
COPY infrastructure/**/*.md ./infrastructure/

# Create types directory
RUN mkdir -p ./types/generated

# Copy OpenAPI specs where generate-types.js expects them (../api/openapi.yaml from /app)
# These files must be generated before building this Dockerfile by running:
#   ./scripts/generate-all-openapi-specs.sh
# This script is automatically called by:
#   - start-platform.sh (local development)
#   - .github/workflows/deploy-compose.yml (CI/CD via generate-openapi-spec workflow)
# The specs are generated from the Python FastAPI apps without running the services
COPY api/openapi.yaml /api/openapi.yaml
COPY storage_service/openapi.yaml /storage_service/openapi.yaml
# COPY executor-service/openapi.yaml /executor-service/openapi.yaml # Deprecated - executor-service removed

# Copy shared generated types from shared-types-generator stage
COPY --from=shared-types-generator /app/shared/generated/typescript ./shared/generated/typescript

# Copy preprocessed docs cache from docs-processor stage
COPY --from=docs-processor /app/.docs-cache ./.docs-cache

# Ensure lib/templates directory is included
# (This is already copied by COPY frontend/ . but let's be explicit)
RUN ls -la lib/templates || echo "Templates directory missing!"

ENV NEXT_TELEMETRY_DISABLED 1
# Increase timeout and reduce parallelism for docs build
ENV NEXT_STATIC_PAGE_GENERATION_TIMEOUT=240
# Reduce concurrent builds to prevent resource exhaustion
ENV NEXT_EXPERIMENTAL_WORKER_THREADS=false
ENV NEXT_EXPERIMENTAL_CPUS=2
ARG API_URL
ENV API_URL=${API_URL}
RUN npm run build

# Stage 4: Runner
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV production
ENV NEXT_TELEMETRY_DISABLED 1

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
ENV PORT 3000

CMD ["node", "server.js"]