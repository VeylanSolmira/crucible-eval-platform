# Wiki-Style Knowledge Graph for Crucible Platform

## Why This is High-Value for AI Safety

The wiki approach is particularly valuable for AI safety evaluation platforms because:

1. **Security Concepts are Interconnected**
   - Container escape relates to privilege escalation
   - Network policies connect to defense-in-depth
   - Resource limits tie into DoS prevention

2. **Learning Acceleration**
   - See how concepts relate visually
   - Discover knowledge gaps quickly
   - Build mental models faster

3. **Cross-Project Integration**
   - Link to AI Safety Research Compiler
   - Connect evaluation strategies
   - Build unified knowledge base

## Implementation Priority (Revised)

### Phase 1: Core Wiki Features (High Priority - Week 1)

#### 1. Cross-Reference System
```typescript
// lib/wiki/cross-references.ts
export class WikiProcessor {
  // Convert [[Page Name]] to links
  processWikiLinks(content: string): string {
    return content.replace(
      /\[\[([^\]]+)\]\]/g,
      (match, pageName) => {
        const slug = this.pageNameToSlug(pageName)
        return `[${pageName}](/docs/${slug})`
      }
    )
  }
  
  // Extract all outgoing links
  extractReferences(content: string): string[] {
    const matches = content.matchAll(/\[\[([^\]]+)\]\]/g)
    return Array.from(matches).map(m => m[1])
  }
}
```

#### 2. Backlinks System
```typescript
// For each document, track what links to it
interface BacklinkIndex {
  [docSlug: string]: {
    title: string
    references: Array<{
      fromDoc: string
      fromTitle: string
      context: string // Surrounding text
    }>
  }
}

// Show at bottom of each doc
<BacklinksSection references={backlinks[currentDoc.slug]} />
```

#### 3. Topic Extraction
```typescript
// Auto-generate topics from content
export function extractTopics(doc: Doc): Topic[] {
  const topics: Topic[] = []
  
  // From frontmatter tags
  if (doc.tags) {
    topics.push(...doc.tags.map(tag => ({
      name: tag,
      source: 'explicit',
      weight: 1.0
    })))
  }
  
  // From headings (## Security → topic: "security")
  const headings = doc.content.match(/^#{2,3}\s+(.+)$/gm) || []
  headings.forEach(heading => {
    const topic = heading.replace(/^#+\s+/, '').toLowerCase()
    if (SECURITY_CONCEPTS.includes(topic)) {
      topics.push({
        name: topic,
        source: 'heading',
        weight: 0.8
      })
    }
  })
  
  // From known security terms in content
  SECURITY_PATTERNS.forEach(pattern => {
    if (doc.content.match(pattern.regex)) {
      topics.push({
        name: pattern.topic,
        source: 'content',
        weight: 0.6
      })
    }
  })
  
  return topics
}
```

### Phase 2: AI Safety Integration (Week 2)

#### Security Concept Ontology
```typescript
// Domain-specific knowledge graph for AI safety
const AI_SAFETY_ONTOLOGY = {
  'evaluation-security': {
    concepts: ['sandboxing', 'resource-limits', 'network-isolation'],
    risks: ['model-exfiltration', 'compute-abuse', 'data-poisoning'],
    mitigations: ['container-security', 'monitoring', 'access-control']
  },
  'autonomous-replication': {
    concepts: ['self-modification', 'persistence', 'lateral-movement'],
    detection: ['behavioral-analysis', 'syscall-monitoring', 'network-anomaly'],
    prevention: ['capability-restriction', 'isolation', 'kill-switches']
  },
  'adversarial-evaluation': {
    concepts: ['red-teaming', 'penetration-testing', 'fuzzing'],
    targets: ['model-robustness', 'system-security', 'defense-validation'],
    tools: ['attack-scenarios', 'payload-generation', 'exploit-frameworks']
  }
}
```

#### Cross-Project Linking
```yaml
# In frontmatter
---
title: Container Security for AI Evaluation
external_links:
  - project: ai-safety-compiler
    page: evaluation-sandboxes
    relationship: implements
  - project: metr-guidelines
    page: security-requirements
    relationship: references
---
```

### Phase 3: Knowledge Graph Visualization (Week 3)

#### Interactive Graph Component
```tsx
// components/KnowledgeGraph.tsx
import { ForceGraph2D } from 'react-force-graph-2d'

export function KnowledgeGraph({ docs, topics, links }) {
  const graphData = {
    nodes: [
      ...docs.map(d => ({
        id: d.slug,
        type: 'document',
        label: d.title,
        group: d.category
      })),
      ...topics.map(t => ({
        id: `topic:${t.name}`,
        type: 'topic',
        label: t.name,
        size: t.documentCount
      }))
    ],
    links: [
      ...links.map(l => ({
        source: l.from,
        target: l.to,
        type: l.type // 'reference', 'implements', 'related'
      }))
    ]
  }
  
  return (
    <ForceGraph2D
      graphData={graphData}
      nodeColor={node => 
        node.type === 'document' ? '#3b82f6' : '#10b981'
      }
      onNodeClick={(node) => {
        if (node.type === 'document') {
          navigate(`/docs/${node.id}`)
        } else {
          navigate(`/docs/topics/${node.label}`)
        }
      }}
    />
  )
}
```

## Use Cases for AI Safety Learning

### 1. Security Vulnerability Chains
Show how vulnerabilities connect:
```
Container Escape → Privilege Escalation → Data Exfiltration
     ↓                    ↓                      ↓
[Mitigation]        [Detection]           [Prevention]
```

### 2. Evaluation Strategy Paths
```
Threat Model → Test Scenarios → Implementation → Results
     ↓              ↓                ↓              ↓
[STRIDE]     [Adversarial]    [Sandbox]     [Metrics]
```

### 3. Learning Paths
Generated from the graph:
- **Beginner**: Start with "Platform Overview" → "Basic Security" → "First Evaluation"
- **Security Focus**: "Threat Model" → "Container Security" → "Network Isolation"
- **AI Safety**: "Evaluation Goals" → "Adversarial Testing" → "Safety Metrics"

## Integration with AI Safety Research Compiler

### Shared Taxonomy
```typescript
// shared/ai-safety-taxonomy.ts
export const AI_SAFETY_TAXONOMY = {
  'capability-evaluation': [
    'coding-ability',
    'reasoning-depth',
    'tool-use',
    'self-modification'
  ],
  'safety-properties': [
    'alignment',
    'robustness',
    'interpretability',
    'controllability'
  ],
  'risk-categories': [
    'deception',
    'power-seeking',
    'misuse',
    'accidents'
  ]
}
```

### Bidirectional Links
- Crucible docs can reference AI Safety Compiler research
- Research findings can link to Crucible implementation
- Shared knowledge graph between projects

## Benefits for Learning

1. **See the Big Picture**
   - How does container security relate to AI safety?
   - What evaluation strategies exist?
   - Where are the knowledge gaps?

2. **Discover Connections**
   - "I didn't know network policies affected this!"
   - "Oh, this relates to that paper I read"
   - "This implementation solves that theoretical problem"

3. **Build Mental Models**
   - Visual representation aids memory
   - Spatial organization of concepts
   - Progressive disclosure of complexity

## Implementation Checklist

### Week 1 - Core Wiki
- [ ] Wiki link processor ([[Page]] → link)
- [ ] Backlinks index builder
- [ ] Topic extraction from content
- [ ] Basic topic pages

### Week 2 - AI Safety Features  
- [ ] Security concept ontology
- [ ] Cross-project linking
- [ ] Learning path generation
- [ ] Related concepts sidebar

### Week 3 - Visualization
- [ ] Interactive knowledge graph
- [ ] Topic clustering
- [ ] Relationship types
- [ ] Graph-based navigation

## Future Vision

### AI-Assisted Features
1. **Concept Explanation**
   - "Explain container escape in context of AI evaluation"
   - Generate examples relevant to current page

2. **Gap Analysis**
   - "What security concepts am I missing?"
   - "What should I learn next?"

3. **Research Integration**
   - Pull in relevant papers
   - Link to implementations
   - Track concept evolution

This wiki approach transforms documentation from static files into a living knowledge base that accelerates learning and enables discovery of security insights relevant to AI safety evaluation.

## Wiki-Style Documentation Features

  Great suggestion! I've added comprehensive plans for
   wiki-style features to the documentation system:

  🔍 Search Capabilities

  1. Basic Search (already has UI placeholder)
    - Simple substring matching
    - Instant results
  2. Enhanced Search (next phase)
    - Full-text search with FlexSearch
    - Fuzzy matching for typos
    - Search within sections
    - Boost title/heading matches
  3. Advanced Search (future)
    - Semantic search
    - Filter by tags/type/date
    - Search history

  🏷️ Topic Generation

  1. Auto-Generated Topic Pages
    - Extract topics from tags and content
    - Create /docs/topics/docker style pages
    - Show all related documents
    - Topic hierarchy (Docker → Containers → Security)
  2. Tag Taxonomy
  architecture/
    ├── microservices/
    ├── security/
    └── scalability/
  deployment/
    ├── kubernetes/
    └── docker/

  🔗 Wiki-Style Cross-References

  1. Automatic Linking
    - [[Docker Security]] → auto-link to that page
    - Similar to Obsidian/Notion
  2. Backlinks
    - "Referenced by" section on each page
    - Build knowledge graph
  3. Related Articles
    - Based on shared tags
    - Similar content analysis

  📊 Knowledge Graph

  - Visual representation of how docs connect
  - Interactive exploration
  - Find knowledge gaps

  🎯 Implementation Priority

  1. Quick wins (1-2 days): Basic search, tag
  extraction
  2. Medium-term (1 week): Search index, topic pages
  3. Long-term: AI features, knowledge graph

  The wiki approach makes the documentation feel more
  like a living knowledge base rather than static
  files. It's perfect for a platform with complex
  architecture where concepts interconnect!