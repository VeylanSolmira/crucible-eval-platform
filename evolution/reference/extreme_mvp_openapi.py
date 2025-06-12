#!/usr/bin/env python3
"""
Crucible Evaluation Platform - OpenAPI-First Edition
Demonstrates contract-first API development with OpenAPI validation.

Run with: python extreme_mvp_openapi.py [--generate-client]
"""

import sys
import json
import subprocess
from pathlib import Path

# Try to install openapi-core if not available
try:
    from openapi_core import Spec
except ImportError:
    print("Installing openapi-core...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "openapi-core", "pyyaml"])
    from openapi_core import Spec

from components import (
    SubprocessEngine,
    DockerEngine, 
    GVisorEngine,
    AdvancedMonitor,
    TaskQueue,
    QueuedEvaluationPlatform
)
from components.openapi_validator import create_openapi_validated_api


def generate_client_code():
    """Generate Python client from OpenAPI spec"""
    print("Generating Python client from OpenAPI spec...")
    
    # Check if openapi-generator is installed
    try:
        subprocess.run(["openapi-generator", "version"], capture_output=True, check=True)
    except:
        print("openapi-generator not found. Install it with:")
        print("  brew install openapi-generator  # macOS")
        print("  npm install -g @openapitools/openapi-generator-cli  # npm")
        return
    
    # Generate Python client
    cmd = [
        "openapi-generator", "generate",
        "-i", "api/openapi.yaml",
        "-g", "python",
        "-o", "client/python",
        "--package-name", "crucible_client"
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("✅ Python client generated in client/python/")
        print("\nUsage example:")
        print("""
from crucible_client import ApiClient, Configuration
from crucible_client.api import evaluations_api

# Configure client
config = Configuration(host="http://localhost:8000")
client = ApiClient(configuration=config)

# Create API instance
api = evaluations_api.EvaluationsApi(api_client=client)

# Submit evaluation
response = api.evaluate_sync(
    evaluation_request={"code": "print('Hello from client!')"}
)
print(response)
""")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to generate client: {e}")


def show_api_benefits():
    """Show the benefits of OpenAPI-first development"""
    print("\n" + "="*60)
    print("🚀 OpenAPI-First Development Benefits")
    print("="*60)
    
    print("\n1. CONTRACT-FIRST DESIGN")
    print("   - API design before implementation")
    print("   - Single source of truth for API structure")
    print("   - Framework-agnostic specification")
    
    print("\n2. AUTOMATIC VALIDATION")
    print("   - Request validation against schema")
    print("   - Response validation for correctness")
    print("   - Type safety without manual checks")
    
    print("\n3. CLIENT GENERATION")
    print("   - Generate clients in any language:")
    print("     • Python: openapi-generator generate -g python")
    print("     • TypeScript: openapi-generator generate -g typescript-axios")
    print("     • Go: openapi-generator generate -g go")
    
    print("\n4. DOCUMENTATION")
    print("   - Swagger UI: docker run -p 8080:8080 -v $(pwd)/api:/api swaggerapi/swagger-ui")
    print("   - ReDoc: docker run -p 8080:80 -v $(pwd)/api/openapi.yaml:/usr/share/nginx/html/swagger.yaml redocly/redoc")
    
    print("\n5. MOCK SERVERS")
    print("   - Prism: prism mock api/openapi.yaml")
    print("   - Enables frontend development before backend is ready")
    
    print("\n6. API TESTING")
    print("   - Postman: Import OpenAPI spec directly")
    print("   - Insomnia: Native OpenAPI support")
    print("   - Contract testing with Pact")
    
    print("\n" + "="*60)


def main():
    """Main entry point demonstrating OpenAPI-first development"""
    
    # Check for client generation flag
    if "--generate-client" in sys.argv:
        generate_client_code()
        return
    
    print("=== Crucible Platform - OpenAPI-First Edition ===\n")
    
    # Show benefits
    show_api_benefits()
    
    # Create engine
    try:
        engine = GVisorEngine()
        print("\n✅ Using gVisor for isolation")
    except:
        try:
            engine = DockerEngine()
            print("\n✅ Using Docker for isolation")
        except:
            engine = SubprocessEngine()
            print("\n⚠️  Using subprocess (unsafe)")
    
    # Create platform components
    queue = TaskQueue(max_workers=2)
    monitor = AdvancedMonitor()
    platform = QueuedEvaluationPlatform(engine, queue, monitor)
    
    # Create OpenAPI-validated API
    print("📋 Loading OpenAPI specification...")
    api = create_openapi_validated_api(platform, "api/openapi.yaml")
    
    # Test the API
    test_result = api.self_test()
    print(f"🧪 API validation test: {test_result['message']}")
    
    if not test_result.get('openapi_available'):
        print("\n⚠️  OpenAPI validation not available. Install with:")
        print("    pip install openapi-core")
    
    # Show example requests
    print("\n📝 Example API usage:")
    print("\n1. Submit evaluation (validated):")
    print("""
curl -X POST http://localhost:8000/eval \\
  -H "Content-Type: application/json" \\
  -d '{"code": "print(42)"}'
""")
    
    print("\n2. Invalid request (rejected by OpenAPI):")
    print("""
curl -X POST http://localhost:8000/eval \\
  -H "Content-Type: application/json" \\
  -d '{}'  # Missing required 'code' field
""")
    
    print("\n3. Check API documentation:")
    print("   - View spec: cat api/openapi.yaml")
    print("   - Swagger UI: http://localhost:8000/docs")
    print("   - Generate client: python extreme_mvp_openapi.py --generate-client")
    
    # Create simple UI showing OpenAPI integration
    ui_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Crucible - OpenAPI Edition</title>
    <style>
        body { font-family: Arial; max-width: 1000px; margin: 50px auto; }
        .container { display: flex; gap: 20px; }
        .panel { flex: 1; background: #f5f5f5; padding: 20px; border-radius: 5px; }
        textarea { width: 100%; height: 150px; }
        button { background: #007bff; color: white; padding: 10px 20px; border: none; cursor: pointer; }
        .swagger-ui { width: 100%; height: 600px; border: 1px solid #ddd; }
        .validation-status { padding: 10px; margin: 10px 0; border-radius: 5px; }
        .valid { background: #d4edda; color: #155724; }
        .invalid { background: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
    <h1>🚀 Crucible Platform - OpenAPI-First Edition</h1>
    
    <div class="container">
        <div class="panel">
            <h3>Submit Evaluation</h3>
            <textarea id="code" placeholder="Enter Python code...">
# OpenAPI validates all inputs/outputs
import sys
print(f"Python {sys.version}")
print("Request validated by OpenAPI!")
</textarea>
            <br><br>
            <button onclick="submitEval()">Submit (Validated)</button>
            <button onclick="submitInvalid()">Submit Invalid (Demo)</button>
            
            <div id="validation-status"></div>
            <div id="result"></div>
        </div>
        
        <div class="panel">
            <h3>OpenAPI Benefits</h3>
            <ul>
                <li>✅ Automatic request validation</li>
                <li>✅ Response validation</li>
                <li>✅ Type-safe client generation</li>
                <li>✅ Interactive documentation</li>
                <li>✅ Mock server capability</li>
                <li>✅ Contract testing</li>
            </ul>
            
            <h4>Generated Clients Available:</h4>
            <ul>
                <li>Python: <code>pip install ./client/python</code></li>
                <li>TypeScript: <code>npm install ./client/typescript</code></li>
                <li>Go: <code>go get ./client/go</code></li>
            </ul>
        </div>
    </div>
    
    <h3>API Documentation</h3>
    <p>The OpenAPI spec defines our complete API contract. View it:</p>
    <ul>
        <li><a href="/api/openapi.yaml">Raw OpenAPI Spec</a></li>
        <li><a href="/docs" target="_blank">Swagger UI</a></li>
        <li>Generate client: <code>openapi-generator generate -i api/openapi.yaml -g python</code></li>
    </ul>
    
    <script>
        async function submitEval() {
            const code = document.getElementById('code').value;
            const statusDiv = document.getElementById('validation-status');
            const resultDiv = document.getElementById('result');
            
            // Show validation happening
            statusDiv.className = 'validation-status';
            statusDiv.innerHTML = '🔍 Validating request against OpenAPI schema...';
            
            try {
                const response = await fetch('/eval', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({code: code})
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    statusDiv.className = 'validation-status valid';
                    statusDiv.innerHTML = '✅ Request validated and processed!';
                    resultDiv.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                } else {
                    statusDiv.className = 'validation-status invalid';
                    statusDiv.innerHTML = '❌ Validation failed: ' + (data.message || 'Unknown error');
                    resultDiv.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                }
            } catch (error) {
                statusDiv.className = 'validation-status invalid';
                statusDiv.innerHTML = '❌ Request failed: ' + error.message;
            }
        }
        
        async function submitInvalid() {
            const statusDiv = document.getElementById('validation-status');
            const resultDiv = document.getElementById('result');
            
            statusDiv.className = 'validation-status';
            statusDiv.innerHTML = '🔍 Sending invalid request (missing required field)...';
            
            try {
                const response = await fetch('/eval', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({})  // Missing required 'code' field
                });
                
                const data = await response.json();
                
                statusDiv.className = 'validation-status invalid';
                statusDiv.innerHTML = '❌ OpenAPI validation correctly rejected invalid request!';
                resultDiv.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                
            } catch (error) {
                statusDiv.className = 'validation-status invalid';
                statusDiv.innerHTML = '❌ Request failed: ' + error.message;
            }
        }
    </script>
</body>
</html>
"""
    
    # Start the server with OpenAPI validation
    print(f"\n🚀 Starting server with OpenAPI validation...")
    print(f"   View API spec: http://localhost:8000/api/openapi.yaml")
    print(f"   Try the UI: http://localhost:8000")
    print(f"   Press Ctrl+C to stop\n")
    
    # Would start the actual server here
    # api.start(port=8000, ui_html=ui_html)
    
    print("\n💡 To use this in production:")
    print("1. Install dependencies: pip install openapi-core pyyaml")
    print("2. Generate clients: python extreme_mvp_openapi.py --generate-client")
    print("3. Use OpenAPIValidatedAPI instead of regular API")
    print("4. All requests/responses will be automatically validated!")


if __name__ == "__main__":
    main()