#!/bin/bash
# Clean up web-frontend structure

echo "🧹 Cleaning up web-frontend structure"
echo "===================================="

cd src/web-frontend

# 1. Remove duplicate base.py
echo "Removing duplicate base.py..."
rm -f base.py
echo "  ✓ Removed base.py (duplicate of web_frontend.py)"

# 2. Remove empty folders or add README explaining their purpose
echo "Handling empty frontend type folders..."

# Create README files explaining the folder structure
cat > simple/README.md << 'EOF'
# Simple Frontend

This folder is reserved for simple frontend assets when the frontend is split into modules.

Future contents:
- `index.html` - Basic HTML template
- `style.css` - Minimal styling
- `app.js` - Vanilla JavaScript

Currently, all frontend implementations are in `../web_frontend.py`.
EOF

cat > advanced/README.md << 'EOF'
# Advanced Frontend

This folder is reserved for advanced frontend assets when the frontend is split into modules.

Future contents:
- `index.html` - Advanced HTML5 template
- `css/` - Modular CSS files
- `js/` - Modular JavaScript with modern features
- `assets/` - Images, fonts, etc.

Currently, all frontend implementations are in `../web_frontend.py`.
EOF

cat > react/README.md << 'EOF'
# React Frontend

This folder is reserved for a React-based frontend when migrating to full SPA.

Future structure:
```
react/
├── package.json
├── src/
│   ├── App.tsx
│   ├── components/
│   ├── services/
│   └── styles/
├── public/
└── build/
```

This would be a separate Node.js project that builds to static files served by nginx.

Currently, all frontend implementations are in `../web_frontend.py`.
EOF

echo "  ✓ Added README files to explain future structure"

# 3. Fix imports in web_frontend.py
echo "Fixing imports in web_frontend.py..."
sed -i.bak 's/from \.base import TestableComponent/from ..shared.base import TestableComponent/' web_frontend.py
sed -i.bak 's/from \.api import APIRequest, HTTPMethod/# APIRequest and HTTPMethod are defined locally/' web_frontend.py
rm web_frontend.py.bak

# 4. Update __init__.py
echo "Updating __init__.py..."
cat > __init__.py << 'EOF'
"""Web frontend module - provides various frontend implementations"""

from .web_frontend import (
    WebFrontendService,
    SimpleHTTPFrontend,
    AdvancedHTMLFrontend,
    FlaskFrontend,
    FastAPIFrontend,
    ReactFrontend,
    FrontendConfig,
    FrontendType,
    create_frontend
)

__all__ = [
    'WebFrontendService',
    'SimpleHTTPFrontend',
    'AdvancedHTMLFrontend',
    'FlaskFrontend',
    'FastAPIFrontend',
    'ReactFrontend',
    'FrontendConfig',
    'FrontendType',
    'create_frontend'
]
EOF

echo ""
echo "✅ Web-frontend cleanup complete!"
echo ""
echo "Summary:"
echo "  - Removed duplicate base.py"
echo "  - Added README files to empty folders explaining future use"
echo "  - Fixed imports in web_frontend.py"
echo "  - Updated __init__.py exports"
echo ""
echo "The frontend type folders (simple/, advanced/, react/) are kept as"
echo "placeholders for future modularization when frontend assets are separated."