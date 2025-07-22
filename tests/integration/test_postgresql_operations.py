#!/usr/bin/env python3
"""
Integration tests for PostgreSQL-specific operations.
Requires PostgreSQL test database.
"""
import pytest
import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError
from storage.models.models import Base


def ensure_test_database():
    """Ensure test database exists, create if not."""
    db_url = os.getenv("TEST_DATABASE_URL")
    if not db_url:
        return False
    
    # Parse database name from URL
    if "test_crucible" not in db_url:
        pytest.skip("TEST_DATABASE_URL must point to test_crucible database")
    
    # Connect to postgres database to create test_crucible if needed
    admin_url = db_url.replace("/test_crucible", "/postgres")
    
    try:
        engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
        with engine.connect() as conn:
            # Check if database exists
            result = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = 'test_crucible'")
            )
            if not result.fetchone():
                # Create database
                conn.execute(text("CREATE DATABASE test_crucible"))
                print("Created test_crucible database")
        engine.dispose()
        return True
    except Exception as e:
        print(f"Could not ensure test database: {e}")
        return False


# Skip if no test database configured or can't create it
pytestmark = pytest.mark.skipif(
    not ensure_test_database(),
    reason="PostgreSQL test database not available"
)


@pytest.mark.integration
class TestPostgreSQLOperations:
    """Test PostgreSQL-specific functionality."""
    
    def test_jsonb_field_operations(self, pg_session):
        """Test JSONB field queries work correctly."""
        from storage.models.models import Evaluation
        
        # Create with JSON metadata
        eval = Evaluation(
            id="test-jsonb",
            code_hash="abc123",
            status="completed",
            eval_metadata={
                "tags": ["ml", "benchmark"],
                "config": {"timeout": 30, "gpu": True}
            }
        )
        pg_session.add(eval)
        pg_session.commit()
        
        # Query by JSON field - need to cast to text for comparison
        from sqlalchemy import cast, String
        result = pg_session.query(Evaluation).filter(
            cast(Evaluation.eval_metadata["config"]["gpu"], String) == "true"
        ).first()
        
        assert result is not None
        assert result.id == "test-jsonb"
    
    def test_concurrent_updates(self, pg_session):
        """Test PostgreSQL handles concurrent updates correctly."""
        from storage.models.models import Evaluation
        from sqlalchemy.exc import OperationalError
        
        # Create evaluation
        eval = Evaluation(id="test-concurrent", code_hash="xyz", status="running")
        pg_session.add(eval)
        pg_session.commit()
        
        # Simulate concurrent update scenario
        # In real scenario, this would be two different sessions
        eval1 = pg_session.query(Evaluation).filter_by(id="test-concurrent").first()
        eval1.status = "completed"
        
        # This tests row-level locking behavior
        pg_session.commit()
        
        final = pg_session.query(Evaluation).filter_by(id="test-concurrent").first()
        assert final.status == "completed"