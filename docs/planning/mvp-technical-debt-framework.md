# MVP Technical Debt Decision Framework

## Core Principle: Reversible vs Irreversible Decisions

**Key insight:** Not all technical debt is equal. Some decisions are easy to change later, others create lasting architectural constraints.

## The Framework: TRACE

### T - Time to Feedback
**Question:** How quickly do we need user validation?
- If users are waiting → Choose simpler option
- If still in stealth → Maybe invest in "right" solution

### R - Reversibility Cost
**Question:** How expensive is it to change later?
```
Low Cost (Choose Simple):          High Cost (Think Harder):
- Queue technology (SQS→Celery)    - Database schema
- Monitoring tools                 - API contracts
- Internal libraries              - Authentication method
```

### A - Abstraction Possibility
**Question:** Can we hide this decision behind an interface?
```python
# Good abstraction makes changes easier
class QueueService:
    def send_task(self, task): 
        # SQS today, Celery tomorrow
        pass
```

### C - Core vs Peripheral
**Question:** Is this central to our value proposition?
- **Core:** Evaluation isolation (invest more)
- **Peripheral:** Notification system (keep simple)

### E - Expertise Required
**Question:** Do we have the skills to maintain the complex solution?
- Team knows Celery well → Maybe start there
- Team learning Celery → Start with SQS

## Applying to SQS vs Celery Decision

### Analysis:
- **T (Time):** Need feedback fast → SQS ✓
- **R (Reversibility):** Queue switch is medium cost → SQS acceptable
- **A (Abstraction):** Can abstract queue interface → SQS ✓
- **C (Core):** Queue is infrastructure, not core → SQS ✓
- **E (Expertise):** Team can learn Celery later → SQS ✓

**Decision: SQS is the right MVP choice**

## When to Migrate (The Triggers)

### Pain Triggers (Reactive)
1. **Feature Impossibility** - "We literally can't build X with SQS"
2. **Operational Pain** - "We're spending hours working around SQS limits"
3. **Performance Wall** - "SQS latency is blocking us"

### Growth Triggers (Proactive)
1. **Roadmap Certainty** - "Next 3 features all need Celery"
2. **Team Readiness** - "We now have Celery expertise"
3. **Stability Window** - "Core platform is stable, good time to migrate"

## Managing the Transition

### 1. Abstract Early
```python
# Start with this on day 1
from abc import ABC, abstractmethod

class TaskQueue(ABC):
    @abstractmethod
    def submit_evaluation(self, eval_id: str, config: dict): pass
    
    @abstractmethod
    def get_task_status(self, task_id: str): pass
```

### 2. Document Assumptions
```python
# queues/sqs.py
class SQSQueue(TaskQueue):
    """
    SQS implementation of TaskQueue
    
    Limitations:
    - No task chaining
    - Status tracked in DB, not queue
    - Max message size 256KB
    
    Migration notes:
    - Task status will move to Celery backend
    - Message format compatible with Celery
    """
```

### 3. Migration Milestones
```
Phase 1: Run both in parallel (feature flag)
Phase 2: New tasks to Celery, old in SQS  
Phase 3: Migrate existing queues
Phase 4: Decommission SQS
```

## The Art of "Good Enough"

### Good MVP Debt
- **Conscious** - "We know SQS has limits"
- **Documented** - "Here's what we'll need to change"
- **Isolated** - "Only the queue module needs updating"
- **Monitored** - "We'll track when we hit limits"

### Bad MVP Debt
- **Accidental** - "Oh, we hardcoded SQS everywhere"
- **Hidden** - "New dev doesn't know the tradeoffs"
- **Sprawling** - "Changing queues requires 20 file updates"
- **Surprising** - "We hit the limit with no warning"

## Real-World Example: METR Queue Decision

**MVP Goal:** Get researcher feedback on UI/workflow
**Technical Need:** Reliable task processing

**SQS gives us:**
- ✅ Working platform in 2 weeks
- ✅ Researchers can submit evaluations
- ✅ We learn actual usage patterns
- ❌ Can't do complex workflows (yet)

**Key Insight:** We can learn if researchers even WANT complex workflows before building them.

## The Senior Developer Mindset

1. **Make reversible decisions quickly**
2. **Make irreversible decisions carefully**
3. **Create abstractions that enable change**
4. **Document why, not just what**
5. **Set up monitors for trigger conditions**

## Questions to Ask in Design Reviews

1. "How hard is this to change in 6 months?"
2. "What would trigger us to revisit this?"
3. "Can we abstract this decision?"
4. "What are we optimizing for - speed or correctness?"
5. "What do we need to learn before committing?"

## Conclusion

The goal isn't to avoid technical debt - it's to take on the *right* debt that:
- Gets you to user feedback faster
- Doesn't paint you into corners
- Has a clear payment plan
- Is visible to the whole team

For METR: SQS is good MVP debt. It's conscious, isolated, and reversible.

## Exploratory: How AI-Assisted Coding Changes the Game

### The Shifting Landscape

With AI coding assistants (Copilot, Cursor, Claude), the traditional cost-benefit analysis of technical decisions is changing:

**What's Different:**
1. **Migration is 10x faster** - AI can refactor SQS→Celery in hours, not days
2. **Boilerplate is free** - Abstractions and interfaces cost almost nothing
3. **Documentation writes itself** - AI maintains migration guides
4. **Parallel experimentation** - Can try multiple approaches simultaneously

### New MVP Philosophy: "Ship to Learn"

**Traditional approach:**
```
Think → Design → Build carefully → Ship → Learn
(2 months)
```

**AI-assisted approach:**
```
Build rapidly → Ship → Learn → Rebuild → Ship again
(2 weeks)        (1 week)     (3 days)
```

### Implications for Technical Decisions

#### 1. Even More Reversible
```python
# AI makes this refactor trivial
# Old: 2 days of careful work
# New: 30 minutes with AI assistance
def migrate_sqs_to_celery():
    """AI can handle all the mechanical changes"""
    pass
```

#### 2. Extreme MVP Becomes Viable
- **Before:** "SQS is simple enough for MVP"
- **Now:** "Even hardcoded arrays might be fine - AI will migrate it"

```python
# This might actually be okay for v0.1 now
EVAL_QUEUE = []  # TODO: AI will convert to SQS next week
```

#### 3. Focus Shifts to Learning
- **Less time:** Worrying about technical debt
- **More time:** Getting user feedback
- **Key skill:** Knowing what questions to ask users

### Counter-Arguments: What Still Matters

1. **Architectural Decisions Still Sticky**
   - AI helps with code, not with understanding domain complexity
   - Wrong abstractions are still costly

2. **Data Migrations Remain Hard**
   - AI can write scripts, but can't undo data corruption
   - Schema decisions still need care

3. **Human Understanding Required**
   - Team needs to understand the system
   - AI-generated complexity can obscure logic

### New Framework Additions for AI Era

#### TRACE-AI Extension

**F - Fungibility**
- How easily can AI swap this component?
- High fungibility → Choose simplest option

**Examples:**
- ✅ High: Queue systems, ORMs, UI frameworks
- ⚠️ Medium: Authentication systems, API designs
- ❌ Low: Data models, security architecture

### Practical Recommendations

1. **Ship embarrassingly simple MVPs**
   ```python
   # Week 1: Just use a database table as a queue
   # Week 2: AI migrates to SQS
   # Month 2: AI migrates to Celery
   ```

2. **Invest in interfaces, not implementations**
   ```python
   # Spend time here
   class EvaluationQueue(Protocol):
       def submit(self, task: Task) -> str: ...
   
   # Let AI write these
   class ArrayQueue: ...  # Day 1
   class SQSQueue: ...    # Day 3
   class CeleryQueue: ... # Day 30
   ```

3. **Document intentions, not code**
   ```python
   # This matters
   """We need a queue that won't lose tasks if system crashes"""
   
   # AI can maintain this
   """SQS client with exponential backoff and DLQ support..."""
   ```

### The Paradox

AI makes changing code so cheap that the "right" technical decision might be:
1. **Choose the absolute simplest thing**
2. **Ship immediately**
3. **Learn from users**
4. **Let AI rebuild it properly**

But this requires:
- Confidence in AI tools
- Good test coverage
- Clear boundaries
- Strong product vision

### For METR Specifically

Given AI assistance:
- **Week 1:** Maybe even skip SQS - use PostgreSQL as queue
- **Week 2:** Get user feedback on workflow
- **Week 3:** AI migrates to SQS based on learnings
- **Month 2:** AI adds Celery when complexity demands it

The question becomes: "What's the simplest thing that could possibly teach us something?"