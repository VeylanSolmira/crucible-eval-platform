"""
Service Registry - Maintains service endpoints for microservices architecture

NOTE: This is for FUTURE use when the platform is split into microservices.
Currently, the platform runs as a monolith and doesn't use these endpoints.
The ports match those in docker-compose.yml.example.
"""

SERVICES = {
    'execution-engine': 'http://localhost:8001',
    'api-gateway': 'http://localhost:8000',
    'monitoring': 'http://localhost:8002',
    'storage': 'http://localhost:8003',
    'queue': 'http://localhost:8004',
    'web-frontend': 'http://localhost:8080',
    'event-bus': 'http://localhost:8005',
    'security-scanner': 'http://localhost:8006',
}

def get_service_url(service_name: str) -> str:
    """Get service URL by name"""
    return SERVICES.get(service_name, 'http://localhost:8000')
