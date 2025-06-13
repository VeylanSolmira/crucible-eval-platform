#!/bin/bash
# Rename main.py files to main.py.example to clarify they're not active code

echo "📝 Renaming main.py files to .example"
echo "===================================="

# Function to rename and add header comment
rename_main_py() {
    local dir=$1
    local service_name=$2
    
    if [ -f "$dir/main.py" ]; then
        echo "  - Renaming $dir/main.py"
        
        # Add explanatory header
        cat > "$dir/main.py.example" << EOF
"""
EXAMPLE: How $service_name could work as a standalone microservice

This file shows how to wrap the $service_name in a REST API for
microservice deployment. Currently, this component is used directly 
by the monolithic platform.

To use this example:
1. Install dependencies: pip install fastapi uvicorn
2. Rename to main.py
3. Run: uvicorn main:app --reload
4. Access API at: http://localhost:8000/docs

Note: The monolithic platform (src/platform/) doesn't use this file.
"""

EOF
        # Append original content
        cat "$dir/main.py" >> "$dir/main.py.example"
        
        # Remove original
        rm "$dir/main.py"
    fi
}

# Rename all main.py files
rename_main_py "src/execution-engine" "execution-engine"
rename_main_py "src/event-bus" "event-bus"
rename_main_py "src/monitoring" "monitoring"
rename_main_py "src/storage" "storage"
rename_main_py "src/queue" "queue"
rename_main_py "src/security-scanner" "security-scanner"
rename_main_py "src/web-frontend" "web-frontend"

# Also check future-services
if [ -d "src/future-services" ]; then
    echo "  Checking future-services..."
    rename_main_py "src/future-services/api-gateway" "api-gateway"
fi

echo ""
echo "✅ Renamed all main.py files to main.py.example"
echo ""
echo "These files now clearly indicate they are examples"
echo "of future microservice implementation, not active code."
echo ""
echo "The actual platform runs from:"
echo "  cd src/platform"
echo "  python extreme_mvp_frontier_events.py"