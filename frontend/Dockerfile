# Multi-stage build for Next.js frontend with type generation

# Stage 1: Type Generator
FROM node:20-alpine AS type-generator
WORKDIR /app

# Install openapi-typescript globally
RUN npm install -g openapi-typescript@7.8.0

# Copy OpenAPI spec from API service
# In production, this would come from a published spec
COPY api/openapi.yaml ./openapi.yaml

# Generate TypeScript types
RUN openapi-typescript openapi.yaml -o types/generated/api.ts

# Stage 2: Dependencies
FROM node:20-alpine AS deps
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --only=production

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
# Run preprocessing
RUN npm install gray-matter && node scripts/preprocess-docs.js

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

# Copy generated types from type-generator stage
COPY --from=type-generator /app/types/generated ./types/generated

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