"""
Service Registry - Maintains service endpoints for microservices architecture

NOTE: This is for FUTURE use when the platform is split into microservices.
Currently, the platform runs as a monolith and doesn't use these endpoints.
The ports match those in docker-compose.yml.example.
"""
import os

# Use environment variable for service host configuration
# This allows flexible deployment without revealing container status
SERVICE_HOST = os.environ.get('SERVICE_HOST', 'localhost')

SERVICES = {
    'execution-engine': f'http://{SERVICE_HOST}:8001',
    'api-gateway': f'http://{SERVICE_HOST}:8000',
    'monitoring': f'http://{SERVICE_HOST}:8002',
    'storage': f'http://{SERVICE_HOST}:8003',
    'queue': f'http://{SERVICE_HOST}:8004',
    'web-frontend': f'http://{SERVICE_HOST}:8080',
    'event-bus': f'http://{SERVICE_HOST}:8005',
    'security-scanner': f'http://{SERVICE_HOST}:8006',
}

def get_service_url(service_name: str) -> str:
    """Get service URL by name"""
    return SERVICES.get(service_name, 'http://localhost:8000')
