# Frontend Sprint: Making Crucible Usable for AI Safety Researchers

## Goal: Create a Frontend That Researchers Will Actually Use

### Current State
- Basic code submission form
- Real-time status updates
- Simple output display

### Target Users: AI Safety Researchers Need To
1. Submit complex Python code for evaluation
2. Monitor execution in real-time
3. See resource usage (CPU, memory, time)
4. Debug failures effectively
5. Compare multiple runs
6. Export results for papers/reports

## Day 1: Enhanced Code Editor & Submission Experience

### Morning (4 hours): Professional Code Editor
- [x] Replace textarea with Monaco Editor (VS Code's editor)
  - [x] Python syntax highlighting
  - [x] Auto-indentation and bracket matching
  - [x] Code folding and minimap
  - [x] Find/replace functionality
  - [x] Multiple cursor support
- [x] Add code templates dropdown
  - [x] "Hello World" example
  - [x] "Network request example"
  - [x] "File I/O example"
  - [x] "Resource-intensive computation" (CPU-intensive task)
- [-] Implement code persistence
  - [x] Auto-save to localStorage
  - [x] "Recent submissions" dropdown
  - [ ] Named templates users can save
  - [ ] Import/export code snippets

### Afternoon (4 hours): Submission Configuration
- [-] Add execution configuration panel
  - [x] Timeout slider (30s - 5min)
  - [x] Memory limit selector (256MB - 2GB)
  - [ ] CPU limit selector (0.5 - 2 cores)
  - [x] Python version selector (3.9, 3.10, 3.11)
- [ ] Pre-submission validation
  - [ ] Basic syntax checking
  - [ ] Import analysis (show which packages are available)
  - [ ] Estimated resource usage
  - [ ] Warning for potentially dangerous operations
- [ ] Batch submission support
  - [ ] Submit multiple variations
  - [ ] Parameter sweeps
  - [ ] A/B testing different approaches

## Day 2: Real-Time Monitoring & Debugging

### Morning (4 hours): Live Execution Dashboard
- [x] Real-time execution viewer
  - [ ] Live stdout/stderr streaming
  - [ ] Execution timeline visualization
  - [ ] Current line indicator (if possible)
  - [x] Elapsed time counter
- [x] Resource usage monitoring
  - [x] CPU usage graph (live) # verify
  - [x] Memory usage graph (live) # verify
  - [ ] Network I/O indicators
  - [ ] Disk I/O indicators
- [x] Execution controls
  - [ ] Pause/resume (if supported)
  - [x] Kill execution button
  - [ ] Extend timeout while running
  - [ ] Download partial results

### Afternoon (4 hours): Enhanced Error Handling
- [x] Intelligent error display
  - [x] Stack trace with code context
  - [x] Link errors to code editor line
  - [x] Common error explanations
  - [x] Suggested fixes
- [x] Debug information panel
  - [x] Environment variables
  - [ ] Installed packages list
  - [x] System information
  - [x] Container constraints
- [ ] Error history and patterns
  - [ ] Track common failure types
  - [ ] Suggest solutions based on history
  - [ ] Link to similar errors

## Day 3: Results Management & Analysis

### Morning (4 hours): Evaluation History & Comparison
- [x] Advanced history view
  - [x] Filterable table (date, status, code hash, duration)
  - [x] Quick preview on hover
  - [ ] Bulk operations (delete, export, re-run)
  - [ ] Tagging and categorization
- [ ] Side-by-side comparison
  - [ ] Compare two evaluations
  - [ ] Diff of code changes
  - [ ] Output differences
  - [ ] Performance comparison
- [ ] Evaluation groups
  - [ ] Group related runs
  - [ ] Aggregate statistics
  - [ ] Experiment tracking

### Afternoon (4 hours): Export & Reporting
- [ ] Export functionality
  - [ ] PDF report generation
  - [ ] CSV data export
  - [ ] JSON for programmatic access
  - [ ] LaTeX tables for papers
- [ ] Shareable links
  - [ ] Public link generation (with expiry)
  - [ ] Embed widget for blogs/papers
  - [ ] QR codes for presentations
  - [ ] Access control (view-only, can-fork)
- [ ] API integration guide
  - [ ] Generate API tokens
  - [ ] Code examples in multiple languages
  - [ ] Webhook configuration
  - [ ] Rate limit dashboard

## Day 4: Safety & Collaboration Features

### Morning (4 hours): Safety Analysis
- [ ] Code safety analyzer
  - [ ] Highlight potentially dangerous operations
  - [ ] Network access attempts
  - [ ] File system access patterns
  - [ ] Resource exhaustion risks
- [ ] Execution sandbox info
  - [ ] Clear display of restrictions
  - [ ] What's allowed/blocked
  - [ ] How to work within limits
  - [ ] Request elevated permissions workflow
- [ ] Safety reports
  - [ ] Automatic safety assessment
  - [ ] Risk score calculation
  - [ ] Detailed behavior analysis
  - [ ] Anomaly detection

### Afternoon (4 hours): Collaboration Tools
- [ ] Comments and annotations
  - [ ] Comment on code lines
  - [ ] Annotate outputs
  - [ ] Discussion threads
  - [ ] @mentions and notifications
- [ ] Workspace sharing
  - [ ] Team workspaces
  - [ ] Role-based permissions
  - [ ] Shared templates library
  - [ ] Collaborative debugging
- [ ] Version control integration
  - [ ] Git-style history
  - [ ] Branching and merging
  - [ ] Revert capabilities
  - [ ] Blame/annotation view

## Day 5: Polish & Performance

### Morning (4 hours): UI/UX Polish
- [ ] Dark mode support
  - [ ] Toggle with system preference detection
  - [ ] Syntax highlighting themes
  - [ ] Persist preference
- [ ] Keyboard shortcuts
  - [ ] Cmd/Ctrl+Enter to submit
  - [ ] Cmd/Ctrl+S to save
  - [ ] Vim/Emacs key bindings
  - [ ] Customizable shortcuts
- [ ] Mobile responsive design
  - [ ] Touch-friendly controls
  - [ ] Swipe gestures
  - [ ] Optimized layouts
  - [ ] Progressive web app

### Afternoon (4 hours): Performance & Testing
- [ ] Performance optimizations
  - [ ] Virtual scrolling for long outputs
  - [ ] Lazy loading of history
  - [ ] Efficient WebSocket handling
  - [ ] Code splitting
- [ ] End-to-end tests
  - [ ] Critical user journeys
  - [ ] Cross-browser testing
  - [ ] Accessibility testing
  - [ ] Load testing
- [ ] Documentation
  - [ ] In-app help system
  - [ ] Video tutorials
  - [ ] API documentation
  - [ ] Troubleshooting guide

## Technical Implementation Notes

### Monaco Editor Integration
```typescript
import Editor from '@monaco-editor/react';

function CodeEditor() {
  return (
    <Editor
      height="400px"
      defaultLanguage="python"
      theme="vs-dark"
      options={{
        minimap: { enabled: true },
        fontSize: 14,
        wordWrap: 'on',
        automaticLayout: true,
      }}
      onChange={handleCodeChange}
    />
  );
}
```

### Real-time Resource Monitoring
```typescript
// Use recharts for live graphs
import { LineChart, Line, XAxis, YAxis, CartesianGrid } from 'recharts';

function ResourceMonitor({ data }) {
  return (
    <LineChart width={400} height={200} data={data}>
      <CartesianGrid strokeDasharray="3 3" />
      <XAxis dataKey="time" />
      <YAxis />
      <Line type="monotone" dataKey="cpu" stroke="#8884d8" />
      <Line type="monotone" dataKey="memory" stroke="#82ca9d" />
    </LineChart>
  );
}
```

### Export Functionality
```typescript
// Generate PDF reports
import { jsPDF } from 'jspdf';

function exportToPDF(evaluation) {
  const doc = new jsPDF();
  doc.text('Evaluation Report', 10, 10);
  doc.text(`ID: ${evaluation.id}`, 10, 20);
  doc.text(`Status: ${evaluation.status}`, 10, 30);
  // ... add code, output, graphs
  doc.save(`evaluation-${evaluation.id}.pdf`);
}
```

## Success Metrics

1. **User Engagement**
   - Time spent in editor before submission
   - Number of template uses
   - Repeat usage rate

2. **Researcher Productivity**
   - Time from code to results
   - Error resolution time
   - Successful completion rate

3. **Platform Reliability**
   - Frontend error rate < 0.1%
   - Real-time updates < 100ms latency
   - 99.9% uptime

## MVP for Researcher Testing (2 days)

If we want something usable quickly:

### Day 1: Core Improvements
- [ ] Monaco editor with Python syntax
- [ ] Basic templates
- [ ] Live output streaming
- [ ] Resource usage display

### Day 2: Essential Features  
- [ ] Evaluation history with search
- [ ] Error display with stack traces
- [ ] Export to JSON/CSV
- [ ] Basic sharing links

This would give researchers a professional tool they can start using immediately, with the full feature set as follow-up iterations based on their feedback.