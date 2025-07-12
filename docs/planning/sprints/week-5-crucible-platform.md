# Week 5 - Crucible Platform Sprint Plan

## Overview
With 5 days remaining in Week 5, this plan focuses on high-priority items organized by success probability tiers. Our main goals are Kubernetes migration, getting tests to 100%, creating tiered demo scenarios, and documentation polish.

## Tier 1: Must Complete (90% success rate) - Days 1-2

### 1. Test Suite Completion ✅ COMPLETED
- [x] Get all current tests in run_tests.py to 100%
  - [x] Fix failing tests (went from 63% to 100% passing)
  - [x] Update tests to match current architecture
  - [x] Remove tests for deprecated features
  - [ ] Add missing test coverage for new features
- [x] Document test results and coverage metrics

**Final Results: 87 tests passed, 0 failed, 2 skipped = 100% of runnable tests passing!**

**Issues Fixed:**
- Fixed JSONB compatibility between PostgreSQL and SQLite
- Fixed SQLite connection pooling parameter issues
- Added missing `code_hash` fields to all test data
- Fixed async/sync mismatch in flexible manager tests
- Updated database backend to handle SQLite vs PostgreSQL differences

**Test Breakdown:**
- ✅ API Evaluation Request Validation - 6/6 passed
- ✅ Celery Retry Configuration - 6/6 passed
- ✅ Storage - Memory Backend - 19/19 passed
- ✅ Storage - File Backend - 24/24 passed
- ✅ Storage - Database Backend - 24/24 passed
- ✅ Storage - Flexible Manager - 8/8 passed
- ⚠️ PostgreSQL Operations - 2 skipped (need PostgreSQL test DB)

### 2. Basic Demo Scenarios ✅ COMPLETED
- [x] **Basic Flow**: Submit code, see results
  - [x] Create simple "Hello World" demo
  - [x] Show step-by-step evaluation process
  - [x] Document expected outputs
- [x] **Error Handling**: Show graceful failures
  - [x] Invalid syntax demo
  - [x] Timeout demo (see [Timeout Demo Workaround](../../demos/timeout-workaround.md))
  - [x] Resource exhaustion demo
- [x] **Monitoring**: Flower dashboard tour (see [Monitoring Demo](../../demos/monitoring-demo.md))
  - [x] Show queue status (via API)
  - [ ] Display active workers (requires full integration - deferred)
  - [x] Demonstrate task history (via API)
    - [ ] Check via web once fully integrated - deferred
  - [x] Note: Web UI has 404s, but API endpoints work
- [x] Pre-populate demo data
  - [x] Example evaluations with various statuses - via run-demo-suite.py

**Demo Suite Results (Successfully Tested):**
- Automated demo runner at `/demos/run-demo-suite.py`
- Successfully submitted 8 different demo scenarios to production
- Covers: basic success, syntax errors, runtime errors, timeouts, CPU/memory exhaustion, large output, stress testing
- All demos can be viewed and filtered in the frontend for story-driven presentations
- Future enhancement: Add tagging system for better demo organization (see Stretch Goals)
- [x] Error cases for demonstration
- [x] Test all demos end-to-end

### 3. Core Documentation
- [ ] Write compelling README
  - [ ] Clear value proposition
  - [ ] Architecture overview
  - [ ] Quick start (< 5 minutes)
  - [ ] Key features showcase
- [ ] Create getting-started.md
  - [ ] Prerequisites
  - [ ] Installation steps
  - [ ] First evaluation walkthrough
  - [ ] Common troubleshooting
- [ ] Repository cleanup
  - [ ] Remove sensitive information
  - [ ] Organize directory structure
  - [ ] Add .gitignore for generated files

## Tier 2: Moderate Chance (50% success rate) - Days 3-4

### 1. Exit Code Messaging (Quick Win) ✅ COMPLETED
- [x] Add user-friendly messages for container exit codes
  - [x] Detect OOM kills (exit code 137) - Shows "Memory Limit Exceeded"
  - [x] Show "Process killed due to exceeding 512MB memory limit (OOM)" message
  - [x] Handle timeout terminations (exit code 143) - Shows "Terminated"
  - [x] Added comprehensive exit code interpretation utility
  - [x] Updated UI to show friendly badges and tooltips
  - [x] Added exit status card in ExecutionMonitor for completed evaluations
- [ ] First attempt in codebase: test

### 2. Fix Resource Metrics Display
- [ ] Either hide or implement CPU/Memory metrics
  - [ ] Currently showing 0/0 for all executions
  - [ ] See [Resource Metrics Issue](../../improvements/resource-metrics.md)
  - [ ] Quick fix: Hide the broken display (~10 minutes)
  - [ ] Proper fix: Wait for Kubernetes

### 3. Complete Flower Integration (~1 hour)
- [ ] Replace generic Flower image with custom build
  - [ ] Update docker-compose.yml to use monitoring/flower/Dockerfile
  - [ ] Rebuild and test Flower with task definitions
  - [ ] Verify Workers tab displays active workers
  - [ ] Confirm Tasks tab shows full task details in UI
  - [ ] Test Broker tab functionality
- [ ] Update monitoring demo documentation
  - [ ] Remove 404 warnings once fixed
  - [ ] Add screenshots of working UI
  - [ ] Document what each tab shows
- [ ] Implementation already prepared in `/monitoring/flower/`

### 4. GitHub Actions Test Integration
- [ ] Create test workflow for pull requests
  - [ ] Set up Python environment
  - [ ] Install dependencies
  - [ ] Run unit tests with pytest
  - [ ] Generate test coverage report
  - [ ] Fail PR if tests don't pass
- [ ] Configure test matrix
  - [ ] Multiple Python versions (3.9, 3.10, 3.11)
  - [ ] Different OS environments (Ubuntu, macOS)
- [ ] Add test badges to README
  - [ ] Test status badge
  - [ ] Coverage percentage badge
- [ ] Set up branch protection rules
  - [ ] Require tests to pass before merge
  - [ ] Require PR reviews
  - [ ] Prevent direct pushes to main
- [ ] Create separate workflows
  - [ ] Quick unit tests on every push
  - [ ] Full test suite on PR to main
  - [ ] Integration tests (manual trigger)

### 5. Kubernetes Basic Migration
- [ ] Follow incremental migration approach (see [Kubernetes Migration Guide](../../kubernetes/migration-guide.md))
- [ ] Phase 1: Frontend Service Only
  - [ ] Create frontend deployment and service
  - [ ] Test with minikube/kind locally
  - [x] Understand basic K8s concepts (Pods, Deployments, Services)
  - [ ] Practice kubectl commands
- [ ] Phase 2: Add API Service
  - [ ] Create API deployment and service
  - [ ] Test inter-service communication
  - [ ] Learn Kubernetes DNS and service discovery
- [ ] Phase 3: Add Stateful Services
  - [ ] ConfigMaps and Secrets
  - [ ] Redis deployment
  - [ ] Storage service with database connection
- [ ] Phase 4: Complete Migration
  - [ ] Migrate remaining services
  - [ ] Handle complex cases (executors, Docker-in-Docker)
  - [ ] Full system test
- [ ] Document learnings and issues encountered

### 6. Advanced Demo Scenarios
- [ ] **Concurrent Load**: 10+ evaluations at once
  - [ ] Create batch submission script
  - [ ] Show scaling behavior
  - [ ] Monitor resource usage
- [ ] **Improve Stress Test Demo**
  - [ ] Update stress-test.py to be an actual stress test
  - [ ] Add CPU-intensive calculations or memory allocation patterns
  - [ ] Make it demonstrate platform limits/capabilities
  - [ ] Current version just sleeps for 1-3 seconds (not stressful)
- [ ] **Storage Explorer**: Show distributed storage
  - [ ] Database entries
  - [ ] File storage
  - [ ] Redis cache
- [ ] **Wiki Docs**: Navigate documentation
  - [ ] Show cross-references
  - [ ] Demonstrate search
  - [ ] Display backlinks
- [ ] Create automated demo suite
  - [ ] Script demo scenarios
  - [ ] Add timing between steps
  - [ ] Include error recovery
  - [ ] See [Demo Philosophy](../../demo-philosophy.md) for design principles
- [ ] Record 5-minute platform walkthrough video
  - [ ] Introduction to platform
  - [ ] Live demo execution
  - [ ] Architecture explanation

### 7. Documentation Polish
- [ ] Finalize ARCHITECTURE.md
  - [ ] System design decisions
  - [ ] Trade-offs made
  - [ ] Scaling considerations
  - [ ] Technology choices rationale
- [ ] Create SECURITY.md (Design Only)
  - [ ] Authentication architecture (JWT flow diagram)
  - [ ] Authorization model (RBAC design)
  - [ ] API key management strategy
  - [ ] Note: "Implementation planned for Phase 2"
- [ ] Complete API documentation
  - [ ] All endpoints with examples
  - [ ] Request/response formats
  - [ ] Error codes and meanings
- [ ] Polish presentation slides
  - [ ] Review content accuracy
  - [ ] Ensure consistent formatting
  - [ ] Update with latest features
- [ ] Ensure all /docs visible in wiki
  - [ ] Audit documentation files
  - [ ] Add missing to index
  - [ ] Verify navigation

## Tier 3: Stretch Goals (10% success rate) - Day 5

### 1. Production Kubernetes
- [ ] Advanced Kubernetes features:
  - [ ] Network policies for isolation
  - [ ] Pod security policies
  - [ ] RBAC configuration
  - [ ] Resource quotas and limits
  - [ ] Horizontal Pod Autoscaling
- [ ] Create Helm charts
  - [ ] Configurable values.yaml
  - [ ] Environment-specific overrides
- [ ] GitOps with ArgoCD
  - [ ] Application definitions
  - [ ] Automated sync policies

### 2. Comprehensive Demo Suite
- [ ] Full automated demo runner
  - [ ] Execute all scenarios in sequence
  - [ ] Generate performance metrics
  - [ ] Create demo report
- [ ] Interactive and automated modes
  - [ ] CLI interface for demos
  - [ ] Web-based demo player
- [ ] Additional demo scenarios
  - [ ] ML model evaluation
  - [ ] Security attack scenarios
  - [ ] Performance benchmarking
- [ ] Professional demo videos
  - [ ] Multiple scenario videos
  - [ ] Edited with transitions
  - [ ] Voice-over narration

### 3. Evaluation Tagging System
- [ ] Backend tagging support
  - [ ] Add `tags` field to EvaluationRequest in `/shared/types/evaluation-request.yaml`
  - [ ] Update generated Python and TypeScript types
  - [ ] Store tags in existing metadata field (quick approach)
  - [ ] Pass tags through API to storage layer
- [ ] API enhancements
  - [ ] Accept tags in evaluation submission endpoint
  - [ ] Add tag filtering to `/api/evaluations` endpoint
  - [ ] Support query like `?tags=demo:ml-training,category:capability`
- [ ] Storage considerations
  - [ ] For MVP: Store as `{"tags": ["tag1", "tag2"]}` in metadata
  - [ ] Future: Consider dedicated tags column with indexes

### 4. Frontend Tag Filtering
- [ ] UI components for tagging
  - [ ] Tag input field in code submission form
  - [ ] Tag display badges in evaluation list
  - [ ] Tag filter dropdown/search in recent executions
- [ ] Filtering implementation
  - [ ] Add tag filter state to recent executions view
  - [ ] Update API calls to include tag filter parameters
  - [ ] Show active filters with clear/remove buttons
- [ ] Demo integration
  - [ ] Pre-populate demo tags in run-demo-suite.py
  - [ ] Filter by demo tags to show specific scenarios
  - [ ] Enable story-driven demo presentations

### 5. Complete Documentation System
- [ ] Architecture diagrams
  - [ ] System overview
  - [ ] Request flow
  - [ ] Security layers
- [ ] Performance benchmarks
  - [ ] Load test results
  - [ ] Resource usage metrics
  - [ ] Scaling characteristics
- [ ] Interview preparation package
  - [ ] Key talking points
  - [ ] Architecture decisions
  - [ ] Trade-offs explained
- [ ] Community files
  - [ ] Code of conduct
  - [ ] Contributing guidelines
  - [ ] Issue templates

## Daily Schedule

### Day 1 (Monday)
**Morning (4 hours)**
- Fix failing tests in run_tests.py
- Update tests for current architecture

**Afternoon (4 hours)**
- Create basic demo scenarios
- Pre-populate demo data

### Day 2 (Tuesday)
**Morning (4 hours)**
- Write README and getting-started.md
- Repository cleanup

**Afternoon (4 hours)**
- Complete test suite to 100%
- Test all basic demos end-to-end

### Day 3 (Wednesday)
**Morning (4 hours)**
- Create Kubernetes manifests
- Test with minikube/kind

**Afternoon (4 hours)**
- Create advanced demo scenarios
- Start automated demo suite

### Day 4 (Thursday)
**Morning (4 hours)**
- Polish documentation (ARCHITECTURE.md, SECURITY.md)
- Complete API documentation

**Afternoon (4 hours)**
- Record platform walkthrough video
- Polish slides and wiki

### Day 5 (Friday)
**Morning (4 hours)**
- Attempt production Kubernetes features
- Work on comprehensive demos

**Afternoon (4 hours)**
- Final polish and review
- Prepare for next week

## Success Criteria

### Tier 1 Success (Must Have)
- All tests passing (100%)
- Basic demos working and documented
- Core documentation complete
- Repository clean and organized

### Tier 2 Success (Should Have)
- Kubernetes deployment working locally
- Advanced demos recorded
- Documentation polished and complete
- All docs visible in wiki

### Tier 3 Success (Nice to Have)
- Production-ready Kubernetes configs
- Fully automated demo suite
- Professional videos and diagrams
- Complete documentation system

## Risk Mitigation

1. **Test Failures**: If tests are too broken, focus on critical path tests only
2. **Kubernetes Complexity**: Start with simplest possible configs, add features incrementally
3. **Demo Issues**: Always have manual fallback for each automated demo
4. **Time Constraints**: Strictly timeboxed - move to next tier even if current isn't perfect

## Next Steps

### Logging Improvements (Post-Kubernetes)
- [Timeout Demo Workaround](../../demos/timeout-workaround.md) - Current limitations and demo scripts
- [Logging Improvements for Kubernetes](../../architecture/logging-improvements-kubernetes.md) - Future architecture

## Notes
- Focus on demonstrable progress over perfection
- Document what doesn't work as "known issues"
- Keep a running list of "future improvements" for items we can't complete
- Daily standups to assess progress and adjust priorities