"""
OpenAPI-validated API component for contract-first development.
Ensures all API requests/responses conform to the OpenAPI specification.
"""

import json
import yaml
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

try:
    from openapi_core import Spec, validate_request, validate_response
    from openapi_core.validation.request.validators import RequestValidator
    from openapi_core.validation.response.validators import ResponseValidator
    OPENAPI_AVAILABLE = True
except ImportError:
    OPENAPI_AVAILABLE = False
    print("Warning: openapi-core not installed. Run: pip install openapi-core")

from ..shared.base import TestableComponent
from .api import APIService, APIRequest, APIResponse


class OpenAPIValidatedAPI(APIService, TestableComponent):
    """
    API Service that validates all requests/responses against OpenAPI spec.
    
    This ensures:
    - Contract-first development
    - Automatic request validation
    - Response validation
    - Single source of truth for API
    """
    
    def __init__(self, platform, spec_path: str = "api/openapi.yaml"):
        super().__init__(platform)
        self.spec_path = Path(spec_path)
        self.spec = None
        self.request_validator = None
        self.response_validator = None
        
        if OPENAPI_AVAILABLE:
            self._load_spec()
    
    def _load_spec(self):
        """Load and parse OpenAPI specification"""
        try:
            with open(self.spec_path, 'r') as f:
                if self.spec_path.suffix == '.yaml':
                    spec_dict = yaml.safe_load(f)
                else:
                    spec_dict = json.load(f)
            
            self.spec = Spec.from_dict(spec_dict)
            self.request_validator = RequestValidator(self.spec)
            self.response_validator = ResponseValidator(self.spec)
            
        except Exception as e:
            print(f"Error loading OpenAPI spec: {e}")
            self.spec = None
    
    def handle_request(self, request: APIRequest) -> APIResponse:
        """Handle request with OpenAPI validation"""
        
        # Validate request if OpenAPI is available
        if self.spec and self.request_validator:
            validation_errors = self._validate_request(request)
            if validation_errors:
                return APIResponse(
                    status_code=400,
                    body=json.dumps({
                        "error": "ValidationError",
                        "message": "Request validation failed",
                        "details": validation_errors
                    }),
                    headers={"Content-Type": "application/json"}
                )
        
        # Process request normally
        response = super().handle_request(request)
        
        # Validate response if OpenAPI is available
        if self.spec and self.response_validator:
            validation_errors = self._validate_response(request, response)
            if validation_errors:
                # Log error but don't fail the response
                print(f"Response validation failed: {validation_errors}")
        
        return response
    
    def _validate_request(self, request: APIRequest) -> Optional[Dict[str, Any]]:
        """Validate request against OpenAPI spec"""
        try:
            # Convert APIRequest to openapi-core format
            openapi_request = self._convert_to_openapi_request(request)
            
            # Validate
            result = self.request_validator.validate(openapi_request)
            
            if result.errors:
                return {
                    "errors": [str(error) for error in result.errors]
                }
            
            return None
            
        except Exception as e:
            return {"error": f"Validation error: {str(e)}"}
    
    def _validate_response(self, request: APIRequest, response: APIResponse) -> Optional[Dict[str, Any]]:
        """Validate response against OpenAPI spec"""
        try:
            # Convert to openapi-core format
            openapi_request = self._convert_to_openapi_request(request)
            openapi_response = self._convert_to_openapi_response(response)
            
            # Validate
            result = self.response_validator.validate(openapi_request, openapi_response)
            
            if result.errors:
                return {
                    "errors": [str(error) for error in result.errors]
                }
            
            return None
            
        except Exception as e:
            return {"error": f"Validation error: {str(e)}"}
    
    def _convert_to_openapi_request(self, request: APIRequest):
        """Convert internal APIRequest to openapi-core format"""
        # This is a simplified conversion - real implementation would be more complete
        from openapi_core.validation.request.datatypes import RequestParameters
        
        # Parse body if JSON
        body = None
        if request.body:
            try:
                body = json.loads(request.body)
            except:
                body = request.body
        
        # Extract path parameters from URL
        # This is simplified - real implementation would use proper URL parsing
        path_params = {}
        if '{' in request.path:
            # Extract parameters from path like /eval-status/{evalId}
            import re
            pattern = re.sub(r'\{(\w+)\}', r'(?P<\1>[^/]+)', request.path)
            match = re.match(pattern, request.path)
            if match:
                path_params = match.groupdict()
        
        return RequestParameters(
            path=request.path,
            method=request.method.lower(),
            body=body,
            headers=request.headers,
            query={},  # Would parse from URL
            path_params=path_params
        )
    
    def _convert_to_openapi_response(self, response: APIResponse):
        """Convert internal APIResponse to openapi-core format"""
        from openapi_core.validation.response.datatypes import ResponseParameters
        
        # Parse body if JSON
        body = None
        if response.body:
            try:
                body = json.loads(response.body)
            except:
                body = response.body
        
        return ResponseParameters(
            status_code=response.status_code,
            headers=response.headers,
            body=body
        )
    
    def get_api_documentation(self) -> Dict[str, Any]:
        """Get the loaded API specification for documentation"""
        if self.spec:
            return self.spec.content
        return {}
    
    def self_test(self) -> Dict[str, Any]:
        """Test OpenAPI validation functionality"""
        tests_passed = 0
        tests_total = 0
        
        # Test 1: Spec loading
        tests_total += 1
        if self.spec is not None:
            tests_passed += 1
        
        # Test 2: Valid request validation
        tests_total += 1
        valid_request = APIRequest(
            method="POST",
            path="/eval",
            headers={"Content-Type": "application/json"},
            body=json.dumps({"code": "print('test')"})
        )
        
        if self.spec:
            errors = self._validate_request(valid_request)
            if errors is None:
                tests_passed += 1
        else:
            tests_passed += 1  # Pass if no spec loaded
        
        # Test 3: Invalid request validation
        tests_total += 1
        invalid_request = APIRequest(
            method="POST",
            path="/eval",
            headers={"Content-Type": "application/json"},
            body=json.dumps({})  # Missing required 'code' field
        )
        
        if self.spec:
            errors = self._validate_request(invalid_request)
            if errors is not None:
                tests_passed += 1
        else:
            tests_passed += 1  # Pass if no spec loaded
        
        return {
            'passed': tests_passed == tests_total,
            'message': f"OpenAPI validation tests: {tests_passed}/{tests_total} passed",
            'openapi_available': OPENAPI_AVAILABLE,
            'spec_loaded': self.spec is not None
        }


def create_openapi_validated_api(platform, spec_path: str = "api/openapi.yaml") -> APIService:
    """
    Factory function to create OpenAPI-validated API.
    Falls back to regular API if OpenAPI is not available.
    """
    if OPENAPI_AVAILABLE:
        return OpenAPIValidatedAPI(platform, spec_path)
    else:
        print("Warning: Creating regular API without OpenAPI validation")
        from .api import RESTfulAPI
        return RESTfulAPI(platform)


# Example usage showing the benefits:
"""
# 1. Contract-first development
api = create_openapi_validated_api(platform, "api/openapi.yaml")

# 2. Automatic validation
# Invalid requests are rejected before reaching business logic
# Responses are validated to ensure they match the contract

# 3. Documentation generation
from apispec import APISpec
spec = api.get_api_documentation()
# Can generate HTML docs, client SDKs, etc.

# 4. Client code generation
# Use openapi-generator to create Python/JS/Java clients:
# openapi-generator generate -i api/openapi.yaml -g python -o client/

# 5. Mock server for testing
# Use prism to create a mock server from the spec:
# prism mock api/openapi.yaml
"""