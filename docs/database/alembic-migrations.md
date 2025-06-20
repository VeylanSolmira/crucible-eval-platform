# Database Migrations with Alembic

## What is Alembic?

Alembic is a database migration tool for SQLAlchemy - essentially **version control for your database schema**. Created by the same author as SQLAlchemy, it tracks and applies incremental changes to your database structure over time.

## Why We Need Database Migrations

### The Problem Without Migrations

```python
# Day 1: Initial model
class Evaluation(Base):
    id = Column(String)
    status = Column(String)

# Day 30: Need to add a field
class Evaluation(Base):
    id = Column(String)
    status = Column(String)
    runtime_ms = Column(Integer)  # NEW FIELD!
```

**What happens to the existing production database?**
- SQLAlchemy's `create_all()` won't add the new column to existing tables
- Manual `ALTER TABLE` commands needed for each environment
- Different developers end up with different schemas
- No record of what changed when or why
- Risk of data loss from manual SQL errors

### How Alembic Solves This

```bash
# Generate a migration when model changes
alembic revision --autogenerate -m "Add runtime_ms to evaluations"

# Creates: migrations/versions/abc123_add_runtime_ms_to_evaluations.py
```

```python
"""Add runtime_ms to evaluations

Revision ID: abc123
Revises: def456
Create Date: 2024-01-15 10:30:00.123456

"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Alembic generates the SQL for you
    op.add_column('evaluations', 
        sa.Column('runtime_ms', sa.Integer(), nullable=True)
    )

def downgrade():
    # And knows how to undo it
    op.drop_column('evaluations', 'runtime_ms')
```

## Key Benefits

### 1. **Version Control for Database**
```bash
migrations/
  versions/
    001_initial_schema.py
    002_add_runtime_ms.py
    003_add_worker_id.py
    004_create_metrics_table.py
```
Each change is tracked in git alongside your code.

### 2. **Team Synchronization**
```bash
# Developer A adds a field
git pull
alembic upgrade head  # Their database now matches

# Developer B adds a different field
alembic revision --autogenerate -m "Add memory_used_mb"
git commit && git push
```

### 3. **Safe Production Deployments**
```bash
# In production
alembic current  # Shows: abc123 (3 revisions behind)
alembic upgrade head  # Applies only the 3 new migrations
```

### 4. **Rollback Capability**
```bash
# Oops, that migration broke something
alembic downgrade -1  # Go back one version

# Or go to specific version
alembic downgrade abc123
```

### 5. **Migration History**
```bash
alembic history
# Shows:
# def456 -> abc123 (head), Add runtime_ms to evaluations
# ghi789 -> def456, Add worker_id field
# base -> ghi789, Initial schema
```

## Common Alembic Commands

```bash
# Initialize Alembic in your project
alembic init storage/database/migrations

# Create a migration manually
alembic revision -m "Add user table"

# Auto-generate migration from model changes
alembic revision --autogenerate -m "Add metrics table"

# Apply all migrations
alembic upgrade head

# Apply next migration
alembic upgrade +1

# Rollback last migration
alembic downgrade -1

# View current version
alembic current

# View history
alembic history --verbose
```

## Real-World Workflow

### 1. **Initial Setup**
```bash
# First time setup
alembic init storage/database/migrations
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head
```

### 2. **Adding a Feature**
```python
# 1. Modify your model
class Evaluation(Base):
    # ... existing fields ...
    cpu_usage_percent = Column(Float)  # NEW

# 2. Generate migration
alembic revision --autogenerate -m "Track CPU usage"

# 3. Review generated migration (IMPORTANT!)
# 4. Apply migration
alembic upgrade head

# 5. Commit both model and migration
git add storage/database/models.py
git add migrations/versions/123_track_cpu_usage.py
git commit -m "Add CPU usage tracking"
```

### 3. **Deployment Process**
```yaml
# In your deployment script
steps:
  - name: Apply database migrations
    run: alembic upgrade head
    
  - name: Deploy new code
    run: docker-compose up -d
```

## Best Practices

### 1. **Always Review Auto-generated Migrations**
```python
# Alembic might generate:
op.drop_table('important_data')  # DANGER!

# Always review before applying!
```

### 2. **Test Migrations**
```bash
# Test upgrade and downgrade
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

### 3. **Name Migrations Descriptively**
```bash
# Bad
alembic revision -m "Update"

# Good
alembic revision -m "Add index on evaluations.created_at for performance"
```

### 4. **Handle Data Migrations Carefully**
```python
def upgrade():
    # Add column with default
    op.add_column('evaluations',
        sa.Column('status', sa.String(), nullable=False, server_default='pending')
    )
    
    # Then migrate existing data
    op.execute("UPDATE evaluations SET status = 'completed' WHERE result IS NOT NULL")
    
    # Then remove default
    op.alter_column('evaluations', 'status', server_default=None)
```

## Without Alembic (Manual Approach)

```sql
-- schema_v1.sql
CREATE TABLE evaluations (...);

-- schema_v2.sql  
ALTER TABLE evaluations ADD COLUMN runtime_ms INTEGER;

-- schema_v3.sql
ALTER TABLE evaluations ADD COLUMN worker_id VARCHAR(100);

-- Which ones have been applied? In what order? 🤷
```

**Problems:**
- No automatic tracking
- Easy to miss a script
- No rollback capability
- No connection to code changes

## Summary

Alembic is essential for any production SQLAlchemy application because it:
- Tracks all schema changes in version control
- Ensures all environments have the same schema
- Provides safe upgrade/rollback mechanisms
- Documents the evolution of your database
- Prevents manual SQL errors

It's like Git for your database structure - you wouldn't code without version control, so why manage your database without it?