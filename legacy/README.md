# Legacy Code Reference

This directory contains legacy code that has been superseded by the current microservices architecture but is kept for reference purposes:

## Contents

- `docker-compose.celery.yml.legacy` - Original Celery configuration before being integrated into main docker-compose.yml
- `requirements.txt` - Monolithic platform requirements before service separation
- `lambda/` - AWS Lambda implementation reference for serverless architecture

## Status

These files are NOT used in the current platform and serve only as:
1. Historical reference for architecture evolution
2. Example patterns for potential future serverless migration
3. Documentation of past design decisions

## Migration Timeline

- **Day 7**: After Celery migration is complete, queue-service and queue-worker will join this directory
- **Future**: This directory may be removed once all architectural decisions are well-documented

## Note

Do not import or reference any code from this directory in the active platform.