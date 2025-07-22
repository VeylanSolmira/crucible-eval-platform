# Archive Directory

This directory contains code that is no longer actively used in the platform but is kept for historical reference or potential future use.

## Structure

### `/celery-worker/`
- **executor_router.py** - Legacy executor routing system that used HTTP health/capacity checks. Replaced by `executor_pool.py` with Redis-based atomic allocation.
- **task_management.py** - Task management utilities (cancel, status, etc.) that were never integrated. Similar functionality exists in `api/celery_client.py`.
- **celerybeat-schedule** - Database file from Celery Beat, which is not currently running. Would be needed if we enable scheduled tasks.

## Why Archive Instead of Delete?

1. **Historical Context** - Shows the evolution of the architecture
2. **Potential Reuse** - Some code (like health checks) might be useful later
3. **Git History** - While git preserves history, having an archive makes it easier to browse
4. **Documentation** - Serves as reference for alternative implementations

## Guidelines

- Files should only be moved here after confirming they're not imported/used anywhere
- Add a note here explaining what each file did and why it was archived
- Consider fully deleting files after 6+ months if never referenced