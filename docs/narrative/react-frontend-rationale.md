# React Frontend Implementation Rationale

## Why We're Building a React Frontend Now

### Current State
- Working backend API with evaluation execution
- Basic HTML/JS interface embedded in Python strings
- Functional but not scalable or maintainable
- TypeScript is a key requirement for METR role

### Strategic Goals

#### 1. Demonstrate TypeScript/React Expertise
METR's job description emphasizes TypeScript and modern frontend skills. Building a production-ready React app shows:
- Component architecture design
- TypeScript type safety
- Modern build tooling (Vite)
- Container-based frontend deployment
- API integration patterns

#### 2. Create a Professional Demo Platform
- Visual interface makes the platform more impressive
- Easier to demonstrate capabilities to METR
- Shows full-stack engineering skills
- Real-time updates demonstrate WebSocket knowledge

#### 3. Architecture Evolution
Moving from embedded HTML to separate frontend:
- **Separation of concerns** - Backend focuses on API
- **Independent scaling** - Frontend can scale separately
- **Modern development** - Hot reload, component testing
- **Container networking** - Multi-container orchestration

### Implementation Approach

#### Phase 1: Mirror Current Functionality (Current)
- Extract existing HTML/JS into React components
- Maintain same features: submit code, view status, see results
- Containerize from the start
- Set up development workflow

#### Phase 2: Enhanced Features (Next)
- Monaco code editor
- Real-time execution status
- Resource usage visualization
- Multiple evaluation history

#### Phase 3: Production Features (Future)
- Authentication/authorization
- Team workspaces
- Evaluation templates
- Export capabilities

### Container Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  nginx:alpine   │────▶│  crucible-api   │────▶│ executor pools  │
│   (frontend)    │     │   (backend)     │     │  (sandboxed)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
       :80                    :8080                  isolated
```

### Why Containerize the Frontend?
1. **Consistency** - Same nginx config in dev/prod
2. **Security** - Static files served by nginx, not Python
3. **Performance** - nginx handles static assets efficiently
4. **Deployment** - Single docker-compose for entire stack
5. **Development** - Hot reload via volume mounts

### Development Workflow
1. `frontend/` runs on Vite dev server (port 5173)
2. Proxies API calls to backend (port 8080)
3. Production build creates static files
4. nginx serves static files and proxies API

### Key Decisions

#### Vite over Create React App
- Faster build times
- Better TypeScript support
- Modern ESM handling
- Growing ecosystem

#### Tailwind CSS
- Rapid prototyping
- Consistent design system
- Small bundle size
- Industry standard

#### No Component Library (Initially)
- Show ability to build from scratch
- Avoid dependency bloat
- Can add later if needed

### Success Metrics
- [ ] Replace embedded HTML completely
- [ ] Sub-second page loads
- [ ] Real-time status updates
- [ ] Mobile responsive
- [ ] Accessibility compliant
- [ ] 90+ Lighthouse score