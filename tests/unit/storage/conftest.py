import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from storage.database.models import Base


@pytest.fixture
def pg_session():
    """PostgreSQL test database session."""
    # Use test database URL or skip
    db_url = os.getenv("TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/test_crucible")
    
    engine = create_engine(db_url)
    Base.metadata.drop_all(engine)  # Clean slate
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    yield session
    
    session.close()
    Base.metadata.drop_all(engine)  # Cleanup