#!/bin/bash
# Script to run database migrations

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Running database migrations...${NC}"

# Ensure DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    export DATABASE_URL="postgresql://crucible:changeme@localhost:5432/crucible"
    echo -e "${YELLOW}Using default DATABASE_URL: $DATABASE_URL${NC}"
fi

# Run migrations in the container
echo -e "${GREEN}Executing migrations in Docker container...${NC}"
docker compose exec -T crucible-platform bash -c "cd /app/storage/database/migrations && DATABASE_URL=$DATABASE_URL alembic $*"

echo -e "${GREEN}Migration complete!${NC}"