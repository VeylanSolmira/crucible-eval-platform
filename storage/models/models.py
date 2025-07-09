"""
SQLAlchemy models for Crucible Platform.
"""

from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    BigInteger,
    Float,
    DateTime,
    ForeignKey,
    Index,
    JSON,
    func,
    Boolean,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

Base = declarative_base()


class Evaluation(Base):
    """Main evaluation record."""

    __tablename__ = "evaluations"

    # Core fields
    id = Column(String(64), primary_key=True)  # eval_id (UUID or hash)
    code_hash = Column(String(64), nullable=False)  # SHA256 of code
    status = Column(String(20), nullable=False, index=True)  # queued, running, completed, failed

    # Timestamps (all UTC)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    queued_at = Column(DateTime(timezone=True))
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    # Execution details
    engine = Column(String(50))  # docker, gvisor, k8s
    worker_id = Column(String(100))  # Which worker processed it
    runtime_ms = Column(Integer)
    memory_used_mb = Column(Integer)
    exit_code = Column(Integer)

    # Output storage - clear separation between inline and external storage
    output = Column(Text)  # Full output when small, preview when large
    output_truncated = Column(Boolean, default=False)  # True if output was truncated
    output_size = Column(BigInteger)  # Total output size in bytes
    output_location = Column(String(255))  # S3/filesystem path for full output

    # Error storage - same pattern as output
    error = Column(Text)  # Full error when small, preview when large
    error_truncated = Column(Boolean, default=False)  # True if error was truncated
    error_size = Column(BigInteger)  # Total error size in bytes
    error_location = Column(String(255))  # S3/filesystem path for full error

    # Code storage - for very large code submissions
    code_location = Column(String(255))  # S3/filesystem path if code is too large

    # Metadata JSON field for flexibility
    eval_metadata = Column(
        "metadata", JSON
    )  # PostgreSQL JSON type - stores additional evaluation data

    # Relationships
    events = relationship(
        "EvaluationEvent", back_populates="evaluation", cascade="all, delete-orphan"
    )
    metrics = relationship(
        "EvaluationMetric", back_populates="evaluation", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Evaluation(id='{self.id}', status='{self.status}')>"


class EvaluationEvent(Base):
    """Event log for evaluation lifecycle."""

    __tablename__ = "evaluation_events"

    id = Column(Integer, primary_key=True)  # Using Integer for SQLite compatibility
    evaluation_id = Column(
        String(64), ForeignKey("evaluations.id", ondelete="CASCADE"), nullable=False
    )
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    event_type = Column(String(50), nullable=False)  # submitted, queued, started, etc
    message = Column(Text)
    event_metadata = Column("metadata", JSON)  # Flexible event data (using JSON for SQLite compatibility)

    # Relationship
    evaluation = relationship("Evaluation", back_populates="events")

    # Indexes for performance
    __table_args__ = (
        Index("idx_events_eval_time", "evaluation_id", "timestamp"),
        Index("idx_events_type", "event_type"),
    )

    def __repr__(self):
        return f"<EvaluationEvent(type='{self.event_type}', eval='{self.evaluation_id}')>"


class EvaluationMetric(Base):
    """Numeric metrics for graphing and analysis."""

    __tablename__ = "evaluation_metrics"

    id = Column(Integer, primary_key=True)  # Using Integer for SQLite compatibility
    evaluation_id = Column(
        String(64), ForeignKey("evaluations.id", ondelete="CASCADE"), nullable=False
    )
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    unit = Column(String(50))  # seconds, bytes, percent, etc

    # Relationship
    evaluation = relationship("Evaluation", back_populates="metrics")

    # Indexes for performance
    __table_args__ = (
        Index("idx_metrics_name_time", "metric_name", "timestamp"),
        Index("idx_metrics_eval", "evaluation_id"),
    )

    def __repr__(self):
        return f"<EvaluationMetric(name='{self.metric_name}', value={self.metric_value})>"
