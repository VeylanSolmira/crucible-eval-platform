# Crucible Platform Evolution - Quick Start Guide

Run through the evolution of abstractions by trying each version:

## 1. Extreme MVP - Feel the Danger

```bash
python extreme_mvp.py
```
- Open http://localhost:8000
- Try running: `import os; print(os.listdir('/'))`
- Notice you can read your actual filesystem! 😱

## 2. Docker Version - Feel the Safety (and Pain)

```bash
# First version (no abstractions)
python extreme_mvp_docker.py
```
- Same dangerous code now runs in Docker
- Try reading /etc/passwd - you'll see the container's file, not yours
- Look at the code - notice how much was copied from extreme_mvp.py

## 3. First Abstraction - ExecutionEngine

```bash
# With abstraction
python extreme_mvp_docker_v2.py           # Docker (safe)
python extreme_mvp_docker_v2.py --unsafe  # Subprocess (dangerous)
```
- Same code, different engines!
- Look how ExecutionEngine abstraction eliminates duplication

## 4. Real-time Monitoring

```bash
python extreme_mvp_monitoring.py
```
- Watch execution progress in real-time
- Try code with delays: `import time; time.sleep(2); print("Done!")`

## 5. Monitoring Pain

```bash
python extreme_mvp_monitoring_v2.py
```
- Same features but messy code
- Look at the source - monitoring is mixed everywhere
- Global state, emit_event() calls scattered around

## 6. Clean Architecture

```bash
python extreme_mvp_monitoring_v3.py
```
- Two clean abstractions: ExecutionEngine + MonitoringService
- Each component has one job
- Easy to swap implementations

## 7. Concurrent Evaluations with Queue

```bash
python extreme_mvp_queue.py
```
- Multiple workers processing evaluations concurrently
- Task queue prevents overload
- Try "Submit 5 Evaluations" button to see concurrent processing!
- Watch the queue status update in real-time

## 8. Testing as First-Class Citizen

```bash
python extreme_mvp_testable.py
```
- Every component must be testable
- Platform runs self-tests on startup
- Safety features are verified to work
- Click "Run Full Test Suite" to see comprehensive testing

## Evolution Comparison

| Version | Abstractions | Lines | Key Learning |
|---------|-------------|-------|--------------|
| extreme_mvp.py | None | 156 | Start simple |
| extreme_mvp_docker.py | None | 228 | Copy-paste pain |
| extreme_mvp_docker_v2.py | ExecutionEngine | 320 | First abstraction |
| extreme_mvp_monitoring.py | None | 341 | Features without abstraction |
| extreme_mvp_monitoring_v2.py | ExecutionEngine | 416 | Monitoring pain emerges |
| extreme_mvp_monitoring_v3.py | ExecutionEngine + MonitoringService | 490 | Clean separation |
| extreme_mvp_queue.py | ExecutionEngine + MonitoringService + TaskQueue | 571 | Concurrent processing |
| extreme_mvp_testable.py | All above + TestableComponent | 565 | Testing required |

## Try This Experiment

Run the same code on each version:

```python
import os
import time

print("Starting evaluation...")
time.sleep(1)

print("Checking environment:")
print(f"Platform: {os.uname().sysname}")
print(f"Working directory: {os.getcwd()}")

try:
    with open('/etc/passwd', 'r') as f:
        print("Can read /etc/passwd!")
except:
    print("Cannot read /etc/passwd (good!)")

print("Evaluation complete!")
```

Notice how:
- Behavior changes between subprocess and Docker
- Monitoring improves in later versions
- The platform becomes more sophisticated while staying simple

## Key Takeaway

Good abstractions aren't designed upfront - they emerge from the pain of not having them. This natural evolution creates cleaner, more maintainable code than trying to predict all future needs.