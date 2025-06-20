"""
Server implementations for the API.

This module contains different server implementations:
- flask_server: Flask-based server with hot reloading
- fastapi_server: FastAPI-based async server
"""

# Import server apps for easy access
try:
    from .flask_server import app as flask_app
except ImportError:
    flask_app = None
    
try:
    from .fastapi_server import app as fastapi_app
except ImportError:
    fastapi_app = None

__all__ = ['flask_app', 'fastapi_app']