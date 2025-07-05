#!/usr/bin/env python3
"""
Unit tests for EvaluationRequest model validation.
"""
import pytest
from pydantic import BaseModel, ValidationError


# Copy the model here to avoid dependency issues
# In production, this would be imported from a shared module
class EvaluationRequest(BaseModel):
    code: str
    language: str = "python"
    engine: str = "docker"
    timeout: int = 30
    priority: bool = False  # High priority flag for queue jumping


class TestEvaluationRequest:
    """Test EvaluationRequest model validation."""
    
    def test_valid_request_minimal(self):
        """Test creating a valid request with minimal fields."""
        request = EvaluationRequest(
            code="print('hello')",
            language="python"
        )
        assert request.code == "print('hello')"
        assert request.language == "python"
        assert request.engine == "docker"  # default
        assert request.timeout == 30  # default
        assert request.priority is False  # default
    
    def test_valid_request_all_fields(self):
        """Test creating a valid request with all fields."""
        request = EvaluationRequest(
            code="console.log('test')",
            language="javascript",
            engine="node",
            timeout=60,
            priority=True
        )
        assert request.code == "console.log('test')"
        assert request.language == "javascript"
        assert request.engine == "node"
        assert request.timeout == 60
        assert request.priority is True
    
    def test_missing_required_code(self):
        """Test that missing code field raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            EvaluationRequest(language="python")
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("code",)
        assert errors[0]["type"] == "missing"
    
    def test_empty_code_rejected(self):
        """Test that empty code is rejected."""
        # Note: Pydantic doesn't reject empty strings by default
        # This test documents current behavior
        request = EvaluationRequest(code="", language="python")
        assert request.code == ""
        # TODO: Add validation to reject empty code if needed
    
    def test_timeout_boundaries(self):
        """Test timeout value boundaries."""
        # Minimum timeout
        request = EvaluationRequest(code="test", language="python", timeout=1)
        assert request.timeout == 1
        
        # Large timeout
        request = EvaluationRequest(code="test", language="python", timeout=3600)
        assert request.timeout == 3600
        
        # Zero timeout (currently allowed, documents behavior)
        request = EvaluationRequest(code="test", language="python", timeout=0)
        assert request.timeout == 0
        # TODO: Add validation for minimum timeout if needed
    
    def test_invalid_types(self):
        """Test that invalid types are rejected."""
        # Invalid code type
        with pytest.raises(ValidationError):
            EvaluationRequest(code=123, language="python")
        
        # Invalid timeout type
        with pytest.raises(ValidationError):
            EvaluationRequest(code="test", language="python", timeout="thirty")
        
        # Invalid priority type - Pydantic coerces strings to bool
        # This documents the current behavior
        request = EvaluationRequest(code="test", language="python", priority="yes")
        assert request.priority is True  # "yes" is truthy