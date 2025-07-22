import pytest
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from storage.models.models import Base


@pytest.fixture
def pg_session():
    """PostgreSQL test database session."""
    # Use test database URL from environment
    db_url = os.getenv("TEST_DATABASE_URL")
    
    engine = create_engine(db_url)
    Base.metadata.drop_all(engine)  # Clean slate
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    yield session
    
    session.close()
    Base.metadata.drop_all(engine)  # Cleanup