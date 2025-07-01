"""
Database connection and session management.
"""

import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Get database URL from environment
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql+asyncpg://crucible:changeme@localhost:5432/crucible'
)

# Convert postgresql:// to postgresql+asyncpg:// if needed
if DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://', 1)

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=os.environ.get('SQL_ECHO', 'false').lower() == 'true',
    pool_pre_ping=True,  # Verify connections before using
    pool_size=10,
    max_overflow=20
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session.
    
    Usage in FastAPI:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """
    Initialize database tables.
    
    Should be called on application startup.
    """
    from .models import Base
    
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        
        
async def close_db():
    """
    Close database connections.
    
    Should be called on application shutdown.
    """
    await engine.dispose()