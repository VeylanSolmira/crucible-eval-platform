# Unified Monitoring Strategy

## Overview
This document outlines how storage visualization fits into our broader monitoring architecture.

## Two-Layer Monitoring Approach

### Layer 1: Infrastructure Observability (Ops-Focused)
Traditional monitoring stack for platform health:

```yaml
Components:
  - Prometheus: Metrics collection
  - Grafana: Infrastructure dashboards
  - Loki/ELK: Log aggregation
  - Jaeger: Distributed tracing
  - AlertManager: Incident response

Metrics:
  - Service health (uptime, latency, errors)
  - Resource usage (CPU, memory, disk)
  - Queue depths and processing rates
  - Database connections and query performance
```

### Layer 2: Research Observability (User-Focused)
Domain-specific monitoring for AI safety researchers:

```yaml
Components:
  - Storage Explorer: Where data lives
  - Evaluation Timeline: Execution history
  - Artifact Browser: Outputs and logs
  - Event Stream: Real-time activity

Metrics:
  - Evaluation success rates
  - Code execution patterns
  - Storage distribution
  - Research workflow analytics
```

## Integration Points

### 1. Shared Data Sources
Both layers read from the same sources:
- PostgreSQL (evaluations, events)
- Redis (cache, pub/sub)
- File system (large outputs)
- Service APIs (real-time status)

### 2. Cross-Layer Navigation
```typescript
// Research view can drill down to ops metrics
<EvaluationDetail>
  <ResearchMetrics />
  <Button onClick={() => openGrafana(evalId)}>
    View Infrastructure Metrics →
  </Button>
</EvaluationDetail>

// Ops dashboards can link to research views
grafanaDashboard.addLink({
  title: "View Evaluation Details",
  url: `/evaluation/${evalId}`
})
```

### 3. Unified Event Stream
Single event pipeline feeds both layers:
```
Event Pipeline
├── Research Events (queued, completed, failed)
├── Storage Events (data written, cache hit/miss)
├── Infrastructure Events (service up/down, deploys)
└── Security Events (auth, rate limits)
```

## Implementation Approach

### Phase 1: Research Monitoring (Current Focus)
Build researcher-facing views:
1. Storage Explorer dashboard
2. Evaluation detail pages
3. Event timeline visualization
4. Basic metrics display

### Phase 2: Infrastructure Integration
Add ops monitoring:
1. Export Prometheus metrics
2. Create Grafana dashboards
3. Set up log aggregation
4. Configure alerting

### Phase 3: Unified Platform
Merge both layers:
1. Single sign-on across tools
2. Embedded dashboards
3. Cross-tool navigation
4. Unified search

## Benefits of This Approach

1. **Separation of Concerns**: Researchers don't see ops complexity
2. **Progressive Disclosure**: Start simple, drill down when needed
3. **Best of Both Worlds**: Custom UX + standard tools
4. **Clear Value Prop**: Shows understanding of different user needs
5. **Extensible**: Easy to add new monitoring dimensions

## Example: Storage Monitoring

### Research View (What We're Building)
```
Storage Overview
├── Total Evaluations: 1,234
├── Storage Distribution
│   ├── Database: 1,234 records (metadata)
│   ├── File System: 89 files (large outputs)
│   ├── Redis: 45 cached results
│   └── Memory: 12 active evaluations
└── [Click any card for details]
```

### Ops View (Standard Tools)
```
Grafana Dashboard
├── PostgreSQL Metrics
│   ├── Connection pool usage
│   ├── Query latency p95
│   └── Disk I/O patterns
├── Redis Metrics
│   ├── Memory usage
│   ├── Eviction rate
│   └── Command latency
└── [Alerts configured]
```

## Conclusion

The storage visualization we're building is the "research monitoring" layer that complements traditional ops monitoring. Together they form a complete observability platform that serves both researchers and operators effectively.

## Our Original Monitoring Vision
From our early discussions, we planned:
  Monitoring Layer
  ├── Metrics (Prometheus)
  ├── Logging (ELK/Loki)
  ├── Tracing (Jaeger/OpenTelemetry)
  ├── Dashboards (Grafana)
  └── Alerting (AlertManager)

  How Storage Viz Fits In

  What we're discussing now is essentially Domain-Specific Observability:

  Observability Stack
  ├── Infrastructure Monitoring (Ops Team)
  │   ├── System metrics (CPU, memory, disk)
  │   ├── Service health (uptime, latency)
  │   └── Traditional dashboards
  │
  └── Research Monitoring (Our Focus)
      ├── Evaluation lifecycle tracking
      ├── Storage artifact visibility  <-- What we're building
      ├── Data lineage visualization
      └── Research-specific metrics

## Discussion

Next thing I think I wanted to do was make 
  visible via the storage-service all the various storage data, so sections 
  for memory?, file, s3, redis, db, etc. What are your thoughts on this? 
  Maybe not all of that we'd want, but it might be useful to display it to 
  me at this phase and then that will help me understand better that will be
   useful. It would be nice if the data was present such that one could 
  'zoom' in or out of the data, like collapsible views of the tables, and 
  then maybe collapse the entire db view, etc. What do you think. This would
   'complete' at this stage of development, to my understanding, what the 
  researchers can see about all the artifacts created as part of their run. 
  I think it woudl be nice, too, to be able to click on the cards for events
   we're submitting and it goes to a page for that evaluation with all the 
  relevant data for that evaluation

✻ Thinking…

  The user wants to:
  1. First get a commit for the work we just did
  2. Then create a storage visualization feature that shows all the 
  different storage backends (memory, file, S3, redis, db)
  3. Make it collapsible/expandable for different views
  4. Make evaluation cards clickable to go to a detailed page
  5. This would complete the researcher view of all artifacts

  This is a great idea - it would help visualize where data is stored and 
  how the flexible storage manager works. Let me first do the commit, then 
  discuss the implementation approach.

⏺ Let me first create a commit for the improvements we just made:

⏺ Bash(git add api/microservices_gateway.py frontend/app/page.tsx
      docs/planning/week-3-metr-completion-plan.md)
  ⎿  (No content)

> So, you might want to create a few pages to support this

✻ Thinking…

  The user is already thinking ahead to the implementation - they're 
  suggesting we'll need multiple pages to support this storage visualization
   feature. Let me finish the commit first, then we can discuss the 
  multi-page approach.

⏺ Bash(git status --short)
  ⎿   D api/api.py                 
      D api/favicon.py
      D api/main.py.example
     … +40 lines (ctrl+r to expand)

> Tell me what your thinking is before implementing anything

✻ Thinking…

  The user wants me to discuss my thinking before implementing. They've 
  mentioned creating multiple pages to support the storage visualization 
  feature. Let me think through this:

  1. Storage visualization dashboard - showing all backends
  2. Individual evaluation detail page 
  3. Making cards clickable to navigate
  4. Collapsible views for different storage types

  I should discuss the architecture and approach before diving into code.

⏺ Let me first commit what we have, then I'll explain my thinking for the
  storage visualization feature:

⏺ Bash(git commit -m "Improve startup experience with smart health checks
      and 503 handling…)
  ⎿ [feature/frontend-researcher-ui 089fd94] Improve startup experience with
     smart health checks and 503 handling
     3 files changed, 160 insertions(+), 41 deletions(-)


✻ Thinking…

  Now let me explain my thinking for the storage visualization feature. The 
  user wants:
  1. Storage data visibility across all backends
  2. Collapsible/expandable views
  3. Clickable evaluation cards that navigate to detail pages
  4. Complete view of all artifacts for researchers

  I should think about:
  - What pages we need
  - What API endpoints we need
  - How to structure the UI
  - What data to show for each storage backend

⏺ My Thinking for Storage Visualization Feature

  Here's how I envision implementing this multi-backend storage
  visualization:

  1. Architecture Overview

  We'd create a storage explorer that shows where data lives across the
  different backends:
  - Memory: In-memory cache (temporary data)
  - Redis: Distributed cache & pub/sub events
  - PostgreSQL: Structured data & metadata
  - File System: Large outputs (>100KB)
  - S3: (Future) Long-term archive

  2. Page Structure

  I'm thinking three main pages:

  /storage             - Storage overview dashboard
  /storage/{backend}   - Detailed view of specific backend
  /evaluation/{id}     - Individual evaluation detail page

  3. API Endpoints Needed

  # Storage service additions:
  GET /storage/overview    - Summary of all backends
  GET /storage/memory      - Memory storage contents
  GET /storage/redis       - Redis keys and values
  GET /storage/database    - Database statistics
  GET /storage/file        - File system usage
  GET /evaluation/{id}/full - Complete data including events

  4. UI Components

  // Collapsible storage backend card
  <StorageBackendCard
    backend="database"
    summary={{evaluations: 150, events: 450, size: "15MB"}}
    expanded={false}
  >
    // Detailed table view when expanded
    <EvaluationTable />
  </StorageBackendCard>

  // Clickable evaluation card
  <EvaluationCard 
    evaluation={eval}
    onClick={() => router.push(`/evaluation/${eval.id}`)}
  />

  5. Data Visualization Ideas

  For each backend, show different relevant info:
  - Database: Tables, row counts, relationships
  - Redis: Key patterns, TTLs, memory usage
  - File System: Directory tree, file sizes
  - Memory: Cache hit rates, eviction stats

  6. Benefits

  This would:
  - Help researchers understand data persistence
  - Debug where data is stored
  - Monitor storage usage
  - Provide complete artifact visibility
  - Show the distributed nature of the system

  7. Implementation Approach

  Start simple:
  1. Add storage overview endpoint
  2. Create basic dashboard page
  3. Add collapsible cards for each backend
  4. Make evaluation cards clickable
  5. Build detailed evaluation page
  6. Add progressive enhancement (charts, etc.)

  What do you think about this approach? Should we focus on certain backends
   first, or build the full overview?

> This sounds very good on all fronts. What do you think is the relative 
  value of us implenting this direclty v. incorporating existing 
  tools/solutions/monitoring options

✻ Thinking…

  The user is asking about whether we should build a custom storage 
  visualization solution or use existing monitoring tools. This is a good 
  architectural question about build vs buy/integrate. Let me think about 
  the trade-offs:

  1. Existing tools we could use:
  - Grafana + Prometheus for metrics
  - pgAdmin for PostgreSQL
  - RedisInsight for Redis
  - Jaeger for distributed tracing
  - ELK stack for logs
  - Datadog/New Relic for APM

  2. Custom implementation benefits:
  - Tailored to our specific use case
  - Unified view across all backends
  - Researcher-friendly (not ops-focused)
  - Integrated with our existing UI
  - Good learning experience
  - Shows full-stack capabilities

  3. Trade-offs to consider:
  - Time investment
  - Maintenance burden
  - Reinventing the wheel
  - Security considerations
  - Production readiness

  I should present a balanced view that considers both the 
  learning/demonstration value for METR and practical considerations.

⏺ Excellent question! Let me break down the trade-offs:

  Existing Tools/Solutions

  What's Available:

  1. Grafana + Prometheus - Beautiful dashboards, time-series data
  2. RedisInsight - Official Redis GUI with full visibility
  3. pgAdmin/DBeaver - Database exploration tools
  4. Jaeger - Distributed tracing across services
  5. Datadog/New Relic - Full APM with storage insights

  Pros of Using Existing Tools:

  - Production-tested - Handles scale, edge cases
  - Feature-rich - Charts, alerts, history, exports
  - Industry standard - What teams actually use
  - Time-efficient - Hours vs days to set up
  - Best practices - Built-in security, performance

  Cons for Our Use Case:

  - Ops-focused - Not researcher-friendly
  - Fragmented - 5+ different UIs to check
  - Generic - Not tailored to AI evaluation workflows
  - Learning curve - Researchers need to learn each tool
  - Less impressive - Doesn't show custom development skills

  Custom Implementation Value

  For METR Specifically:

  1. Demonstrates full-stack capability - Shows you can build monitoring
  2. Unified experience - One place for researchers to see everything
  3. Domain-specific - Tailored to evaluation artifacts
  4. Learning opportunity - Understand monitoring internals
  5. Portfolio piece - Unique, memorable feature

  My Recommendation: Hybrid Approach

  Phase 1 (What we build): Custom Storage Explorer
  - Unified dashboard showing all backends
  - Researcher-friendly evaluation browser
  - Click-through to evaluation details
  - Basic metrics and counts

  Phase 2 (What we integrate): Production Monitoring
  - Embed Grafana dashboards in our UI
  - Add "Open in RedisInsight" buttons
  - Link to Jaeger traces
  - Export Prometheus metrics

  Implementation Strategy:

  // Custom overview page
  /storage -> Our unified view with cards for each backend

  // Embedded tools where helpful
  /storage/metrics -> Embedded Grafana dashboard
  /storage/redis -> Our view + "Open in RedisInsight" button
  /storage/traces -> Embedded Jaeger UI

  // Our custom evaluation page
  /evaluation/{id} -> Complete view with all artifacts

  Specific Benefits for METR:

  1. Shows architectural thinking - "We built custom views for researchers
  but integrate standard tools for ops"
  2. Demonstrates pragmatism - Not reinventing everything
  3. Highlights domain knowledge - Understanding what researchers need vs
  ops teams
  4. Time-boxed effort - 1-2 days for basic custom UI
  5. Future-ready - Easy to swap in production tools later

  Code Example of Hybrid:

  // Custom storage overview
  export default function StorageOverview() {
    return (
      <div>
        {/* Our custom cards */}
        <StorageBackendCard backend="database" />
        <StorageBackendCard backend="redis" />

        {/* Integrated tools section */}
        <section className="mt-8">
          <h2>Advanced Monitoring</h2>
          <div className="grid grid-cols-2 gap-4">
            <GrafanaEmbed 
              url="/grafana/d/storage/overview"
              height={400}
            />
            <Button onClick={() => window.open('http://redis:8001')}>
              Open RedisInsight →
            </Button>
          </div>
        </section>
      </div>
    )
  }

  Bottom line: Build a simple custom storage explorer for the researcher
  experience (1-2 days), but also show you know how to integrate
  industry-standard tools. This demonstrates both technical capability and
  practical judgment.

  What do you think - should we start with the custom unified view and then
  add integration points for existing tools?

> Okay, another thing to deeply consider is we've talked about this 
  cross-cutting monitoring component, which arguably all of this storage 
  information is part of or overlaps with. How do you think that affects 
  this. We talked in moderate depth about our monitoring in the beginning 
  but not recently as much

✻ Thinking…

  The user makes an excellent point. We did discuss monitoring architecture 
  early on, and now we're talking about storage visualization which is 
  really a subset of monitoring. Let me think about how these relate:

  1. Early monitoring discussions included:
  - Metrics collection (Prometheus)
  - Logging pipeline
  - Distributed tracing
  - Observability stack
  - Dashboards

  2. Current storage visualization is really about:
  - Data lineage tracking
  - Artifact visibility
  - Storage backend monitoring
  - Researcher-focused views

  These definitely overlap. The storage visualization we're discussing is 
  essentially the "researcher-facing monitoring" while the earlier 
  monitoring discussion was more "ops-facing monitoring". 

  I should frame this in the context of our broader monitoring strategy and 
  show how they complement each other.

⏺ You're absolutely right - this storage visualization is really part of the
   broader monitoring/observability picture we discussed earlier. Let me
  reconnect these concepts:

  Our Original Monitoring Vision

  From our early discussions, we planned:
  Monitoring Layer
  ├── Metrics (Prometheus)
  ├── Logging (ELK/Loki)
  ├── Tracing (Jaeger/OpenTelemetry)
  ├── Dashboards (Grafana)
  └── Alerting (AlertManager)

  How Storage Viz Fits In

  What we're discussing now is essentially Domain-Specific Observability:

  Observability Stack
  ├── Infrastructure Monitoring (Ops Team)
  │   ├── System metrics (CPU, memory, disk)
  │   ├── Service health (uptime, latency)
  │   └── Traditional dashboards
  │
  └── Research Monitoring (Our Focus)
      ├── Evaluation lifecycle tracking
      ├── Storage artifact visibility  <-- What we're building
      ├── Data lineage visualization
      └── Research-specific metrics

  Unified Monitoring Architecture

⏺ Write(docs/architecture/unified-monitoring-strategy.md)
  ⎿  Wrote 140 lines to docs/architecture/unified-monitoring-strategy.md    
     # Unified Monitoring Strategy
     ## Overview
     This document outlines how storage visualization fits into our broader
     monitoring architecture.
     ## Two-Layer Monitoring Approach
     ### Layer 1: Infrastructure Observability (Ops-Focused)
     Traditional monitoring stack for platform health:
     … +130 lines (ctrl+r to expand)

✻ Thinking…

  The user is asking me to think about how the storage visualization we're 
  discussing fits into the broader monitoring component we discussed 
  earlier. This is a great observation - we did talk about monitoring 
  architecture in depth early on, and now I should connect these concepts 
  properly.

  Let me create a clear explanation of how these fit together, showing that 
  the storage visualization is really the "researcher-facing" part of our 
  monitoring strategy, while the traditional monitoring stack (Prometheus, 
  Grafana, etc.) is the "ops-facing" part.

⏺ Key Insights

  The storage visualization we're discussing is actually the
  researcher-facing layer of our monitoring strategy. Here's how I see it
  fitting together:

  1. Two Distinct User Personas

  Ops Team Needs:                    Researcher Needs:
  - Is the service up?               - Where is my evaluation data?
  - How's the latency?              - What outputs were produced?
  - Are we running out of disk?      - Can I see the full history?
  - Alert me if something breaks     - What's in the queue?

  2. Complementary, Not Competing

  - Traditional Monitoring: Health of the platform
  - Storage Explorer: Health of the research workflow

  3. Shared Infrastructure

  Both use the same data sources but present different views:
  # Same data, different perspectives
  database.evaluations ->
    ├── Grafana: "Queries per second" chart
    └── Storage Explorer: "Your 50 evaluations" table

  redis.keys() ->
    ├── Grafana: "Cache hit rate" metric
    └── Storage Explorer: "15 cached results" list

  4. Progressive Implementation

  Week 3: Build Storage Explorer (researcher monitoring)
  Week 4: Add Prometheus/Grafana (ops monitoring)
  Week 5: Integrate them (unified platform)

  5. METR Value Proposition

  This shows you understand:
  - Different stakeholder needs
  - Monitoring isn't one-size-fits-all
  - How to build domain-specific tools
  - When to use existing solutions
  - System design thinking

  Should we build the Storage Explorer as the first piece of our "Research 
  Monitoring Layer" and design it to later integrate with the ops monitoring
   stack?

## Custom solution
hy Storage Explorer Benefits from Custom Implementation

  1. Domain-Specific Requirements

  - Researchers care about evaluations, not database rows
  - They need to see code → output relationships, not table schemas
  - The mental model is experiment artifacts, not storage backends

  2. Unified Cross-Backend View

  No existing tool shows:
  "Your evaluation eval_123 has:
  - Metadata in PostgreSQL
  - Output file at /data/outputs/eval_123.txt (2.3MB)
  - Cached result in Redis (expires in 5 min)
  - 6 events tracking its lifecycle"

  3. Researcher Workflow Integration

  - Click an evaluation card → see all its data
  - Navigate from output → back to code
  - Timeline view of execution events
  - Batch evaluation grouping

  4. Educational Value

  Shows researchers:
  - Why outputs >100KB go to files (performance)
  - How caching speeds up re-runs
  - Where their data persists
  - System design in action

  5. METR-Specific Benefits

  Demonstrates:
  - Understanding user needs - Researchers ≠ DBAs
  - Full-stack capability - Backend aggregation + frontend UX
  - System thinking - How distributed storage works
  - Practical judgment - Custom where it adds value

  6. Foundation for Future Integration

  Our custom Storage Explorer can later:
  - Embed Grafana charts for trends
  - Link to pgAdmin for deep SQL debugging
  - Export to standard monitoring formats
  - Feed into cost analysis tools

  The Storage Explorer is where custom implementation shines because it's
  translating technical storage details into researcher-friendly concepts.
  Standard tools show "Redis has 45 keys" - we show "You have 45 cached
  evaluation results."

  Shall we start building it?