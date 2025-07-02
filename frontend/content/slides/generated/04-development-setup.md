---
title: 'Development Setup'
order: 4
tags: ['setup', 'development', 'docker']
---

# Development Setup

## Prerequisites

- Node.js 20+
- Docker & Docker Compose
- Git

---

## Quick Start

```bash
# Clone the repository
git clone <repo-url>
cd metr-eval-platform

# Start backend services
docker-compose up -d

# Install frontend dependencies
cd frontend
npm install

# Generate types from API
npm run generate-types

# Start development server
npm run dev
```

---

## Common Commands

```bash
# Development
npm run dev          # Start dev server
npm run build:local  # Build with type generation
npm run lint         # Run linter
npm run type-check   # Check TypeScript

# Type Generation
npm run generate-types  # Update from API
```

---

## Docker Development

```bash
# Build all services
docker-compose build

# Start all services
docker-compose up

# View logs
docker-compose logs -f frontend
```
