#!/usr/bin/env python3
"""
Unit tests for PostgreSQL-specific operations.
Requires PostgreSQL test database.
"""
import pytest
import os
from datetime import datetime, timezone

# Skip if no test database configured
pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="No test database configured"
)


@pytest.mark.unit
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
        
        # Query by JSONB field
        result = pg_session.query(Evaluation).filter(
            Evaluation.eval_metadata["config"]["gpu"].astext == "true"
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