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
