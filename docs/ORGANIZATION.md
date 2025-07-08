# Documentation Organization

This document describes the organization of the documentation directory.

## Directory Structure

```
docs/
├── README.md                    # Main documentation readme
├── architecture.md              # High-level system architecture
├── index.md                     # Documentation landing page
├── ORGANIZATION.md              # This file
│
├── api/                         # API documentation
├── architecture/                # Detailed architecture docs
│   ├── celery/                  # Celery-specific architecture
│   ├── core/                    # Core system architecture
│   ├── deployment/              # Deployment architecture
│   ├── docker/                  # Docker architecture
│   ├── microservices/           # Microservices patterns
│   └── monitoring/              # Monitoring architecture
├── collaboration/               # Human-AI collaboration docs
├── database/                    # Database documentation
├── debugging/                   # Debugging guides
├── deployment/                  # Deployment procedures
├── design/                      # Design documents
├── development/                 # Development guides
├── docker/                      # Docker-specific docs
├── extreme-mvp/                 # Original MVP documentation
├── features/                    # Feature documentation
├── fixes/                       # Bug fixes and solutions
├── getting-started/             # Getting started guides
├── guides/                      # How-to guides
├── implementation/              # Implementation details
├── knowledge/                   # Knowledge base
├── metr/                        # METR-specific docs
├── models/                      # Model documentation
├── narrative/                   # Narrative documentation
├── papers/                      # Research papers
├── planning/                    # Planning documents
│   └── sprints/                 # Sprint planning
├── presentation/                # Presentation materials
├── proposals/                   # Feature proposals
├── questions/                   # FAQ and questions
├── security/                    # Security documentation
├── setup/                       # Setup guides
├── tasks/                       # Task documentation
├── testing/                     # Testing documentation
├── troubleshooting/             # Troubleshooting guides
└── wiki/                        # Wiki system docs
```

## Recent Reorganization (Week 5)

Files that were moved from the root directory:
- Docker-related files → `/docker/`
- Wiki system files → `/wiki/`
- Setup files → `/setup/`
- Various implementation docs → appropriate subdirectories

## Key Entry Points

1. **New developers**: Start with `/getting-started/`
2. **Architecture overview**: `/architecture.md` then `/architecture/`
3. **API documentation**: `/api/`
4. **Docker setup**: `/docker/README.md`
5. **Security**: `/security/`
6. **Planning/Roadmap**: `/planning/sprints/`

## Documentation Standards

- Use Markdown for all documentation
- Include diagrams where helpful (Mermaid supported)
- Cross-reference with relative links
- Keep files focused on a single topic
- Update this file when adding new directories