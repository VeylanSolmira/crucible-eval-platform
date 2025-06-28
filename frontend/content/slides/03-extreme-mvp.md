---
title: "Chapter 1: The Extreme MVP"
duration: 2
tags: ["mvp", "beginning"]
---

## Chapter 1: The Extreme MVP
### Problem: Need to evaluate AI code somehow

**`extreme_mvp.py` - 97 lines of terror**

```python
def handle_evaluation(self, code: str):
    result = subprocess.run(
        ['python', '-c', code],  # EXECUTES ANYTHING!
        capture_output=True,
        text=True,
        timeout=30
    )
    return {'output': result.stdout, 'error': result.stderr}
```

**Why we started here:**
- Fastest path to working demo
- Understand the core problem
- "Make it work, then make it safe"