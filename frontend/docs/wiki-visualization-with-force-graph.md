# Wiki Visualization with React-Force-Graph

## Overview

React-force-graph enables powerful interactive visualizations for the Crucible documentation system, transforming wiki-style documents into explorable knowledge graphs.

## Package Information

- **Package Size**: ~111MB total
  - `react-force-graph`: 20MB
  - `three.js`: 31MB
  - D3 and force-related dependencies: ~60MB
- **Technologies**: Three.js (WebGL), D3-force (physics simulation)

## Core Features

### 1. Interactive Knowledge Graph

- **Visual network** of all documentation pages as nodes
- **Wiki links** shown as edges/connections between nodes
- **Clusters** form naturally around related topics (e.g., security docs cluster together)
- **Force-directed layout** - nodes repel each other but connected nodes attract

### 2. Navigation Features

- **Click nodes** to navigate to that document
- **Hover** to see document title, description, backlink count
- **Zoom and pan** to explore large documentation sets
- **Search highlighting** - matching nodes glow or enlarge
- **Keyboard navigation** for accessibility

### 3. Visual Insights

- **Node sizing** by importance (number of backlinks)
- **Edge thickness** by reference frequency
- **Color coding** by document type/category
- **Orphaned pages** appear disconnected
- **Hub documents** become visually obvious

### 4. Crucible/METR-Specific Configuration

```javascript
// Example visualization config for security platform
const graphConfig = {
  nodeGroups: {
    security: { color: '#ff4444', icon: '🔒' },
    architecture: { color: '#4444ff', icon: '🏗️' },
    api: { color: '#44ff44', icon: '🔌' },
    deployment: { color: '#ff44ff', icon: '🚀' },
    evaluation: { color: '#ffaa44', icon: '⚡' },
  },
  specialNodes: {
    'threat-model': { size: 20, pulseAnimation: true },
    'security-guide': { size: 18, glowEffect: true },
    'container-isolation': { size: 16, borderHighlight: true },
  },
  linkStyles: {
    'security-critical': { color: '#ff0000', width: 3 },
    prerequisite: { color: '#0000ff', dashed: true },
  },
}
```

### 5. AI Safety Research Applications

- Visualize **concept dependencies** in AI safety topics
- Show **prerequisite chains** for understanding complex topics
- Identify **knowledge gaps** in documentation
- Track **cross-references** between security measures
- Map **threat model relationships**

### 6. Advanced Visualization Features

- **3D mode** for complex relationships
- **VR support** (via three.js) for immersive exploration
- **Time-based animations** showing documentation evolution
- **Collision detection** preventing node overlap
- **Physics simulation** for natural clustering
- **Hierarchical layouts** for showing document structure

## Use Cases in Crucible Platform

### Security Audit Visualization

- See all security-related docs and their interconnections
- Identify which security measures reference each other
- Find isolated security docs that should be linked
- Visualize attack surface through document relationships

### Onboarding Path Visualization

- Show the learning path from "Getting Started" through advanced topics
- Highlight prerequisite relationships
- Suggest next documents based on current reading
- Track progress through documentation

### Documentation Health Metrics

- **Orphaned pages**: No incoming or outgoing links
- **Over-connected pages**: May need splitting into subtopics
- **Missing connections**: Documents that should reference each other
- **Circular dependencies**: Identify confusing reference loops

### Example Implementation

```typescript
import ForceGraph2D from 'react-force-graph-2d';

function WikiGraph({ documents, wikiLinks }) {
  const graphData = {
    nodes: documents.map(doc => ({
      id: doc.slug,
      name: doc.title,
      group: doc.category,
      backlinks: doc.backlinks.length,
      val: doc.backlinks.length + 1 // Node size
    })),
    links: wikiLinks.map(link => ({
      source: link.from,
      target: link.to,
      value: link.weight || 1
    }))
  };

  return (
    <ForceGraph2D
      graphData={graphData}
      nodeLabel="name"
      nodeAutoColorBy="group"
      nodeVal="val"
      onNodeClick={(node) => router.push(`/docs/${node.id}`)}
      nodeCanvasObject={(node, ctx, globalScale) => {
        // Custom node rendering with icons
        if (node.group === 'security') {
          ctx.fillText('🔒', node.x, node.y);
        }
      }}
    />
  );
}
```

## Performance Considerations

- Efficient for up to ~1000 nodes (documents)
- WebGL acceleration for smooth interactions
- Lazy loading for large graphs
- Configurable physics simulation accuracy

## Future Enhancements

1. **AI-Powered Insights**
   - Suggest missing connections using embeddings
   - Auto-categorize documents
   - Identify documentation gaps

2. **Collaborative Features**
   - Real-time multi-user exploration
   - Annotation and commenting on graph
   - Saved graph views/bookmarks

3. **Integration with Evaluation Platform**
   - Visualize evaluation dependencies
   - Show security control relationships
   - Map container isolation strategies

## Why This Matters for METR

The visualization transforms documentation from a linear experience into an explorable knowledge space, particularly valuable for:

- Understanding complex security architectures
- Identifying evaluation scenario relationships
- Training new team members on platform architecture
- Auditing security control completeness
- Planning documentation improvements

The 111MB investment provides significant value through enhanced documentation discovery, better understanding of system relationships, and improved platform security through visual analysis.
