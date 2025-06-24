# AI-Human Code Generation Patterns: Lessons Learned

## The Problem

When an AI assistant generates large blocks of code in one shot, several issues emerge:

### 1. Error Rate Correlation
**Observation**: Error probability seems to increase with code size

- **Small changes (1-20 lines)**: Usually correct, easy to verify
- **Medium changes (50-100 lines)**: May contain subtle bugs, harder to review
- **Large rewrites (200+ lines)**: Higher chance of:
  - Missing imports
  - Incorrect assumptions about existing code
  - Inconsistent error handling
  - Lost context from original implementation

### 2. Human Review Burden
**The Cognitive Load Problem**:
```
10-line change: 30 seconds to review
100-line change: 10 minutes to review (not linear!)
500-line rewrite: May never be fully reviewed
```

The human often just runs it and hopes for the best, defeating the purpose of human-in-the-loop.

### 3. Lost Learning Opportunities
When jumping from A to Z without showing B through Y:
- Human doesn't learn the refactoring patterns
- Reasoning for architectural decisions is obscured
- Hard to maintain or modify later

## Proposed Patterns

### Pattern 1: Incremental Transformation
```
Better:
1. "Let me first extract the interface" (20 lines)
2. "Now let's add the HTTP layer" (30 lines)
3. "Next, we separate the concerns" (40 lines)

Worse:
1. "Here's the complete microservices architecture" (300 lines)
```

### Pattern 2: Explicit Checkpoints
```python
# CHECKPOINT: Working monolithic version
git commit -m "Pre-refactoring checkpoint"

# Small change 1
# Small change 2
# Small change 3

# CHECKPOINT: Working microservices version
git commit -m "Post-refactoring checkpoint"
```

### Pattern 3: Show Don't Tell
Instead of:
- "I'll modularize this" → [300 lines of new code]

Better:
- "First, I'll extract the queue interface"
- [Show 20 lines]
- "This preserves the existing logic while adding HTTP"
- "Next, I'll separate the worker..."

### Pattern 4: Error Introduction Points
When making large changes, explicitly note risk areas:
```python
# RISK: This assumes Docker socket is mounted at /var/run/docker.sock
# RISK: This changes the threading model from the original
# RISK: This requires new environment variables
```

## The Speed vs Quality Trade-off

### Fast Development (Large Chunks)
✅ Rapid prototyping
✅ Less back-and-forth
✅ Can see the "end state" quickly
❌ Higher error rate
❌ Harder to review
❌ Learning opportunity lost
❌ Difficult to rollback

### Incremental Development (Small Steps)
✅ Each step reviewable
✅ Errors caught early
✅ Human learns patterns
✅ Easy to rollback
❌ Much slower
❌ More interaction overhead
❌ Can lose sight of bigger picture

## Recommendations

### For Exploration/Prototyping
- Large chunks are fine
- Document checkpoints before/after
- Plan to create "missing middle" for education

### For Production Changes
- Prefer incremental steps
- Each change should be reviewable in 2-3 minutes
- Include tests with each step

### For Learning/Documentation
- Always show the evolution
- Explain the "why" at each step
- Include failed approaches and why they failed

### For This Project Specifically
Given METR's focus on AI evaluation and platform engineering:

1. **Build fast** to demonstrate capabilities
2. **Document checkpoints** for the portfolio
3. **Create evolutionary narrative** for the presentation
4. **Show both approaches** as valid patterns

The key insight: **AI-assisted development is not just about the final code, but about creating an understandable evolution path that humans can learn from and maintain.**

## Meta-Learning

This very refactoring (monolith → microservices) is a perfect case study:
- We built a working monolith (good!)
- We jumped to microservices (too fast!)
- We recognized the gap (learning!)
- We documented both states (recovery!)
- We can show the evolution later (education!)

This meta-pattern itself is valuable for METR: How do we evaluate AI systems that help with complex engineering tasks? The quality isn't just in the final code, but in the explainability and maintainability of the path taken.