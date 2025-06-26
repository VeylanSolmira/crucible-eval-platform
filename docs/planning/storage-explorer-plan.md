# Storage Explorer Implementation Plan

## Overview
Build a researcher-friendly storage explorer as part of the Research Monitoring Layer.

## Phase 1: Storage Service API Extensions

### New Endpoints
```python
# Storage overview - aggregated view across all backends
GET /storage/overview
Response: {
  "backends": {
    "database": {
      "type": "postgresql",
      "status": "healthy",
      "metrics": {
        "evaluations": 1234,
        "events": 4567,
        "size_bytes": 15728640,
        "oldest_record": "2024-01-01T00:00:00Z"
      }
    },
    "redis": {
      "type": "redis",
      "status": "healthy", 
      "metrics": {
        "keys": 89,
        "memory_used_bytes": 524288,
        "hit_rate": 0.92,
        "ttl_stats": {"<60s": 45, "60s-300s": 20, ">300s": 24}
      }
    },
    "file": {
      "type": "filesystem",
      "status": "healthy",
      "metrics": {
        "files": 156,
        "total_size_bytes": 1073741824,
        "directories": 12,
        "largest_file": "eval_123_output.txt"
      }
    },
    "memory": {
      "type": "in-memory",
      "status": "healthy",
      "metrics": {
        "cached_evaluations": 12,
        "cache_size_bytes": 131072,
        "eviction_count": 3
      }
    }
  },
  "summary": {
    "total_evaluations": 1234,
    "total_storage_bytes": 1089994752,
    "active_backends": 4
  }
}

# Backend-specific details
GET /storage/{backend}/details
- /storage/database/details - Table sizes, row counts
- /storage/redis/details - Key patterns, memory breakdown  
- /storage/file/details - Directory tree, file listing
- /storage/memory/details - Cache contents

# Enhanced evaluation endpoint with all artifacts
GET /evaluations/{id}/complete
Response: {
  "evaluation": { /* core data */ },
  "events": [ /* all events */ ],
  "storage_locations": {
    "metadata": "database",
    "output": "file:///data/outputs/eval_123.txt",
    "cache": "redis://pending:eval_123"
  },
  "related_evaluations": [ /* same batch */ ],
  "execution_timeline": [ /* detailed timeline */ ]
}
```

## Phase 2: Frontend Pages

### 1. Storage Overview Dashboard (`/storage`)
```typescript
// Main dashboard showing all backends
StorageOverview
├── BackendCard (PostgreSQL)
│   ├── Summary stats (collapsed)
│   └── Detailed table (expanded)
├── BackendCard (Redis) 
│   ├── Summary stats (collapsed)
│   └── Key browser (expanded)
├── BackendCard (File System)
│   ├── Summary stats (collapsed)
│   └── File tree (expanded)
└── BackendCard (Memory)
    ├── Summary stats (collapsed)
    └── Cache contents (expanded)
```

### 2. Backend Detail Pages (`/storage/{backend}`)
```typescript
// Deep dive into specific backend
DatabaseDetail
├── Tables overview
├── Recent evaluations
├── Query performance
└── Growth trends

RedisDetail
├── Key patterns
├── Memory usage by type
├── TTL distribution
└── Hot keys

FileSystemDetail
├── Directory browser
├── Large files list
├── Storage trends
└── Cleanup candidates
```

### 3. Evaluation Detail Page (`/evaluation/{id}`)
```typescript
// Complete evaluation view
EvaluationDetail
├── Core Information
│   ├── Code
│   ├── Status
│   └── Timing
├── Execution Timeline
│   ├── Queued event
│   ├── Started event
│   ├── Progress events
│   └── Completed event
├── Storage Artifacts
│   ├── Database record
│   ├── Output file
│   ├── Redis cache
│   └── Event history
└── Related Evaluations
    └── Same batch submissions
```

## Phase 3: UI Components

### Reusable Components
```typescript
// Collapsible backend card
interface BackendCardProps {
  backend: 'database' | 'redis' | 'file' | 'memory'
  summary: BackendSummary
  onExpand: () => void
}

// Clickable evaluation row
interface EvaluationRowProps {
  evaluation: Evaluation
  onClick: () => void
  showStorage?: boolean
}

// Storage location badge
interface StorageLocationProps {
  location: string // "database", "file:///path", "redis://key"
  size?: number
}

// Event timeline
interface EventTimelineProps {
  events: Event[]
  interactive?: boolean
}
```

## Phase 4: Integration Points

### 1. Cross-Navigation
- Click evaluation in storage view → go to evaluation detail
- Click storage location in evaluation → go to that backend view
- Breadcrumb navigation throughout

### 2. Real-time Updates
- WebSocket subscriptions for live data
- Auto-refresh for active evaluations
- Event stream integration

### 3. Future Ops Integration
```typescript
// Prepare for ops monitoring integration
<BackendCard backend="database">
  {/* Our research view */}
  <EvaluationTable />
  
  {/* Future: Link to ops monitoring */}
  <Button variant="outline" className="mt-4">
    View Database Metrics in Grafana →
  </Button>
</BackendCard>
```

## Implementation Order

1. **Day 1 Morning**: Storage service API endpoints
   - `/storage/overview`
   - `/storage/{backend}/details`
   - `/evaluations/{id}/complete`

2. **Day 1 Afternoon**: Basic storage dashboard
   - Overview page with cards
   - Collapsible/expandable UI
   - Basic backend summaries

3. **Day 2 Morning**: Evaluation detail page
   - Complete evaluation view
   - Event timeline
   - Storage artifacts section

4. **Day 2 Afternoon**: Polish & navigation
   - Click-through navigation
   - Real-time updates
   - Loading states

## Success Metrics

- Researchers can see where all their data lives
- One-click navigation to any artifact
- Clear understanding of data lifecycle
- Foundation for future monitoring integration

## Technical Decisions

1. **Next.js App Router** for pages
2. **React Query** for data fetching (or continue with current approach)
3. **Tailwind** for consistent styling
4. **Shadcn/ui** components for UI
5. **Recharts** for simple visualizations

## Future Enhancements

- Export capabilities (CSV, JSON)
- Search across all backends
- Data retention visualization
- Cost analysis (storage costs)
- Grafana embedding
- Jaeger trace integration