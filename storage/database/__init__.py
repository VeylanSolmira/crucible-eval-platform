"""
PostgreSQL database storage backend.

Handles structured data storage for:
- Evaluation metadata
- Execution history
- Platform analytics
"""

try:
    from .models import Evaluation, EvaluationEvent, EvaluationMetric
    from .connection import get_db, init_db
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    # Define dummy classes to prevent import errors
    class Evaluation:
        pass
    class EvaluationEvent:
        pass
    class EvaluationMetric:
        pass
    def get_db():
        raise RuntimeError("SQLAlchemy not installed")
    def init_db():
        raise RuntimeError("SQLAlchemy not installed")

__all__ = ['Evaluation', 'EvaluationEvent', 'EvaluationMetric', 'get_db', 'init_db', 'SQLALCHEMY_AVAILABLE']