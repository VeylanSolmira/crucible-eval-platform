# Question Formats for Technical Documentation

This guide shows different ways to embed self-study questions in technical documentation for learning and interview preparation.

## 1. Quick Check Questions
Use for immediate comprehension checks after explaining a concept.

```markdown
> 🤔 **Quick Check**: Which principle would be most important when evaluating a model that might attempt network access? Why?

<details>
<summary>💡 Answer</summary>

Defense in Depth would be most critical. A model attempting network access could try to exfiltrate data...
</details>
```

## 2. Self-Assessment Checklists
Great for testing understanding of multiple related concepts.

```markdown
---
**🎯 Self-Assessment Questions:**
- [ ] Can you explain why WebSockets are better than polling for this use case?
- [ ] What would happen if 10,000 clients connected simultaneously?
- [ ] How would you implement authentication for WebSocket connections?
---
```

## 3. Scenario-Based Questions
Perfect for testing applied knowledge and problem-solving.

```markdown
> 💭 **Scenario**: Your manager says "A major AI lab wants to use our platform and expects 50,000 concurrent users..."
> 
> *Think about: CDN strategies, WebSocket scaling, state management...*
> 
> <details>
> <summary>📋 Possible Solutions</summary>
> 
> 1. **WebSocket Scaling**: Implement Socket.io with Redis adapter...
> 2. **CDN**: Use CloudFront/Fastly for static assets...
> </details>
```

## 4. Pre-Reading Prompts
Activate prior knowledge before diving into details.

```markdown
> 📝 **Interview Prep**: Before reading each component section, try to list 3 things you'd expect to see in that component's design.
```

## 5. Code Review Questions
Embedded in code examples to test understanding.

```python
# 🤔 Question: What happens if the WebSocket connection drops during this loop?
async for update in subscription:
    await websocket.send_json(update)
# Hint: Consider error handling, reconnection logic, and message queuing
```

## 6. Design Decision Challenges
Test understanding of trade-offs.

```markdown
**❓ Design Challenge**: We chose React over server-side rendering frameworks. In what scenario would SSR have been the better choice? Consider:
- Team size and experience
- Project timeline
- Performance requirements
- Ecosystem needs
```

## 7. Inline Thinking Prompts
Subtle prompts that encourage reflection without breaking flow.

```markdown
We use gVisor for container isolation (← why not just Docker's default runtime?), which provides...
```

## 8. Interview Role-Play
Practice explaining concepts as in an interview.

```markdown
**🎤 Interview Practice**: 
"Explain this architecture to someone who knows backend development but has never worked with Kubernetes."

*Key points to cover:*
- Start with the problem it solves
- Use analogies (containers = shipping containers)
- Draw parallels to concepts they know
- Avoid jargon or explain it clearly
```

## 9. Research Prompts
Encourage deeper exploration.

```markdown
> 🔍 **Dig Deeper**: Research how Netflix handles WebSocket connections at scale. What patterns could we adopt?
```

## 10. Comparison Tables with Questions

| Approach | Our Choice | Alternative | 
|----------|------------|-------------|
| Frontend | React | Vue.js |
| **Why?** | *[Fill in]* | *[Fill in]* |
| **Best for** | *[Fill in]* | *[Fill in]* |

## Best Practices for Question Placement

1. **After Key Concepts**: Place comprehension checks after explaining important principles
2. **Before Deep Dives**: Use pre-reading prompts before detailed sections
3. **In Transition Sections**: Add scenario questions between major topics
4. **Throughout Code**: Embed questions in code comments
5. **End of Sections**: Comprehensive self-assessment at section ends

## Question Difficulty Progression

1. **Level 1 - Recall**: "What does API stand for?"
2. **Level 2 - Comprehension**: "Why do we use WebSockets instead of polling?"
3. **Level 3 - Application**: "How would you modify this for 10x scale?"
4. **Level 4 - Analysis**: "What are the trade-offs of our approach?"
5. **Level 5 - Synthesis**: "Design an alternative architecture that prioritizes cost over performance"

## Tips for Writing Good Questions

- **Be Specific**: Vague questions lead to vague thinking
- **Provide Context**: Include enough information to answer meaningfully
- **Vary Difficulty**: Mix easy wins with challenging problems
- **Include Hints**: Guide thinking without giving away answers
- **Real Scenarios**: Use actual problems you might face
- **Time Estimates**: Add "5-min think" or "20-min exercise" labels