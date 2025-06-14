#!/bin/bash
# Rename extreme_mvp_frontier_events.py to app.py for clarity

echo "📝 Renaming extreme_mvp_frontier_events.py to app.py"
echo "=================================================="

cd src/core

# 1. Rename the file
echo "1. Renaming file..."
if [ -f "extreme_mvp_frontier_events.py" ]; then
    mv extreme_mvp_frontier_events.py app.py
    echo "   ✓ Renamed extreme_mvp_frontier_events.py → app.py"
else
    echo "   ❌ extreme_mvp_frontier_events.py not found"
    exit 1
fi

# 2. Update __main__.py
echo -e "\n2. Updating __main__.py..."
sed -i.bak 's/from \.extreme_mvp_frontier_events import main/from .app import main/' __main__.py
rm -f __main__.py.bak
echo "   ✓ Updated __main__.py"

# 3. Update pyproject.toml
echo -e "\n3. Updating pyproject.toml..."
cd ../..
sed -i.bak 's/src\.core\.extreme_mvp_frontier_events:main/src.core.app:main/' pyproject.toml
rm -f pyproject.toml.bak
echo "   ✓ Updated pyproject.toml"

# 4. Update documentation
echo -e "\n4. Updating documentation..."
find . -name "*.md" -type f -exec sed -i.bak 's/extreme_mvp_frontier_events\.py/app.py/g' {} \;
find . -name "*.md.bak" -type f -delete
echo "   ✓ Updated documentation references"

# 5. Create explanation file
echo -e "\n5. Creating architecture explanation..."
cat > src/core/ARCHITECTURE.md << 'EOF'
# Core Architecture: The "What" vs The "How"

## core.py - The "What" (Platform Library)

This file defines **WHAT** the platform is:
- **Classes & Interfaces**: The building blocks
- **Abstract Behavior**: What operations are possible
- **Component Contracts**: How pieces interact

Think of it as a library or framework:
```python
class EvaluationPlatform:
    """This is WHAT an evaluation platform is"""
    def submit_evaluation(self, code: str) -> str:
        """Platforms can evaluate code"""
        pass

class QueuedEvaluationPlatform(EvaluationPlatform):
    """This is WHAT a queued platform adds"""
    def __init__(self, engine, monitor, queue):
        """Platforms need these components"""
        pass
```

## app.py - The "How" (Concrete Application)

This file defines **HOW** to use the platform:
- **Configuration**: Which engines, what ports
- **User Interface**: CLI arguments, web server
- **Wiring**: Connecting all components
- **Business Logic**: Specific workflows

Think of it as the actual application:
```python
def main():
    """This is HOW we run the platform"""
    # Parse arguments (HOW users interact)
    args = parser.parse_args()
    
    # Choose engine (HOW we configure)
    if args.engine == "docker":
        engine = DockerEngine()
    
    # Create platform (HOW we instantiate)
    platform = QueuedEvaluationPlatform(engine, monitor, queue)
    
    # Start server (HOW we serve)
    frontend.start()
```

## Analogy

**core.py** is like a car's blueprint:
- Defines what a car is (wheels, engine, steering)
- Specifies how components connect
- Abstract - could be any car

**app.py** is like a specific car model:
- Tesla Model 3 with specific engine
- Red color, leather seats
- Starts with a button
- Concrete - this exact car

## Why This Split?

1. **Reusability**: core.py can be imported by other apps
2. **Testing**: Can test platform logic separately from UI
3. **Modularity**: Can swap implementations easily
4. **Clarity**: Business logic vs infrastructure
EOF
echo "   ✓ Created ARCHITECTURE.md"

echo -e "\n✅ Rename complete!"
echo -e "\nThe architecture is now clearer:"
echo "  - core.py: Platform classes (the library)"
echo "  - app.py: Application entry point (the program)"
echo -e "\nTo run:"
echo "  python -m src.core"