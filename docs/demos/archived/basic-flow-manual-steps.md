# Basic Flow Demo - Manual Steps

## Pre-Demo Setup (5 minutes before)
- [x] Open browser to https://crucible.veylan.dev
- [x] Clear any previous evaluations (or use incognito)
- [x] Have this checklist open on a second monitor/phone
- [x] Test submit one "Hello World" to warm up containers

## Demo Steps

### 1. Open the Platform (5 seconds)
- [ ] Navigate to https://crucible.veylan.dev
- [ ] Let page fully load
- [ ] Say: "Here's our evaluation platform running in production"

### 2. Show the Interface (10 seconds)
- [ ] Point to Monaco editor
- [ ] Say: "Professional code editor with syntax highlighting"
- [ ] Point to right panel
- [ ] Say: "Real-time execution monitoring"

### 3. Write Simple Code (15 seconds)
- [ ] Click in editor
- [ ] Type slowly and clearly:
```python
print("Hello from METR Evaluation Platform!")
print("Running in a secure Docker container")
print("Current time:", __import__('datetime').datetime.now())
```
- [ ] Say: "Let me run a simple Python evaluation"

### 4. Submit Code (5 seconds)
- [ ] Click "Run Code" button
- [ ] Say: "Submitting to our evaluation queue..."

### 5. Watch Execution (20 seconds)
- [ ] Point to status as it changes
- [ ] Say each status: "Pending... Provisioning container... Running..."
- [ ] Point to timer
- [ ] Say: "Execution time tracking"
- [ ] Point to output when it appears
- [ ] Say: "And here's our output, captured from the isolated container"

### 6. Highlight Key Features (15 seconds)
- [ ] Point to evaluation ID
- [ ] Say: "Unique ID for tracking"
- [ ] Point to execution time
- [ ] Say: "Completed in under 2 seconds"
- [ ] Point to Docker container info
- [ ] Say: "Each evaluation runs in its own secure container"

### 7. Close Strong (5 seconds)
- [ ] Say: "That's the basic flow - simple, fast, and secure"
- [ ] Pause for questions

## Total Time: ~75 seconds

## Troubleshooting

### If submission is slow:
- Say: "Each evaluation creates a fresh container for security isolation"
- Mention: "Container creation adds ~1-2 seconds but ensures complete isolation"
- Can discuss: "Trade-off between security and speed - we chose security"

### If something fails:
- Say: "Let me show you our error handling" 
- Submit code with syntax error: `print(`
- Show how errors are displayed clearly

### If asked about the code:
- Explain Docker isolation
- Mention gVisor for kernel-level security
- Reference the 10x security improvement from socket proxy

## Next Demo
- Say: "Now let me show you how it handles concurrent load..."
- Proceed to Concurrent Load demo