# Crucible Platform Glossary

A comprehensive glossary of terms used throughout the Crucible documentation. Each term links to relevant documentation.

## A

### Adversarial Testing
Testing AI models that may attempt to subvert, escape, or cause harm to the [[Evaluation]] environment. See [[Security/Adversarial Testing Requirements]].

### AI Safety
The field of research focused on ensuring advanced AI systems are aligned with human values and don't cause unintended harm. Core mission of [[METR]].

### Alembic
Database migration tool used for [[PostgreSQL]] schema management. See [[Database/Migrations]].

### API Gateway
Service that routes incoming API requests to appropriate microservices. Part of the [[Architecture/Microservices]] design.

### Autonomous Replication
A key risk where an AI model attempts to copy itself or persist beyond its evaluation. Prevented through [[Container Isolation]] and [[Network Isolation]].

### AWS (Amazon Web Services)
Primary cloud provider for [[Crucible]] infrastructure. Key services include [[EC2]], [[S3]], [[IAM]], and [[SQS]].

## C

### Container Escape
Security vulnerability where code breaks out of [[Container Isolation]]. Mitigated by [[gVisor]] and [[Defense in Depth]].

### Container Isolation
Core security mechanism using [[Docker]] containers with multiple layers of isolation. See [[Security/Container Isolation]].

### Crucible
The evaluation platform for safely testing potentially dangerous AI models. Main documentation at [[Architecture/Platform Overview]].

### CI/CD
Continuous Integration/Continuous Deployment pipeline using [[GitHub Actions]]. See [[Development/CI-CD]].

## D

### Defense in Depth
Security strategy using multiple layers of protection. See [[Security/Defense in Depth]].

### Docker
Container runtime providing process isolation. Enhanced with [[gVisor]] for additional security. See [[Security/Docker Security]].

### Docker Compose
Tool for defining and running multi-container [[Docker]] applications. Used for local development. See [[Development/Local Setup]].

## E

### EC2 (Elastic Compute Cloud)
[[AWS]] virtual server instances used for deploying [[Crucible]]. See [[Deployment/EC2]].

### Evaluation
A test run of an AI model in an isolated environment. Core functionality of [[Crucible]].

### Evaluator
Component responsible for scoring and analyzing model outputs. Part of [[Executor Service]].

### Event-Driven Architecture
Architectural pattern using asynchronous message passing between services. See [[Architecture/Events]].

### Executor Service
Microservice responsible for running evaluations in isolated containers. See [[Architecture/Microservices]].

## F

### FastAPI
[[Python]] web framework used for backend services. Provides automatic [[OpenAPI]] documentation. See [[API/Framework]].

## G

### gVisor
Google's userspace kernel providing additional [[Container Isolation]] through system call interception. See [[Security/gVisor Setup]].

### Grafana
Metrics visualization platform (planned). Part of [[Monitoring Service]] and alerting.

## I

### IAM (Identity and Access Management)
[[AWS]] service for managing permissions and access control. See [[AWS/IAM Configuration]].

### Infrastructure as Code
Managing infrastructure through version-controlled definition files using [[Terraform]].

## K

### Kubernetes (K8s)
Container orchestration platform planned for future scaling. See [[Deployment/Kubernetes]].

## M

### METR (Model Evaluation for Transformative Research)
Organization focused on evaluating potentially transformative AI systems for safety.

### Microservices
Architectural pattern dividing the platform into small, independent services. See [[Architecture/Microservices]].

### Monitoring Service
Real-time tracking of [[Evaluation]] status and resource usage. See [[Architecture/Monitoring]].

## N

### Network Isolation
Security measure preventing evaluated models from accessing the internet. See [[Security/Network Policies]].

### Next.js
[[React]] framework used for the frontend application. See [[Frontend/Framework]].

### Non-root Execution
Security practice of running processes without root privileges. Standard in all [[Container Isolation]].

## O

### OpenAPI
Specification for describing REST APIs. Used for [[API/Documentation]] and [[Type Generation]].

### OpenTelemetry
Observability framework for metrics, logs, and traces (planned). See [[Monitoring/OpenTelemetry]].

### OpenTofu
Open-source [[Terraform]] fork used for infrastructure management. See [[Infrastructure/OpenTofu]].

## P

### PostgreSQL
Primary database for storing evaluation metadata and results. See [[Database/PostgreSQL]].

### Prometheus
Metrics collection system (planned). Part of [[Monitoring Service]] and alerting.

### Python
Primary backend programming language. Used with [[FastAPI]] for services.

## Q

### Queue/Worker Pattern
Architectural pattern for processing [[Evaluation]] jobs asynchronously. Uses [[Redis]] as message broker.

## R

### React
JavaScript library for building user interfaces. Used with [[Next.js]] for frontend.

### Redis
In-memory data store used as message broker and cache. Central to [[Queue/Worker Pattern]].

### runsc
Runtime component of [[gVisor]] that intercepts system calls for additional [[Container Isolation]].

## S

### S3 (Simple Storage Service)
[[AWS]] object storage for [[Evaluation]] artifacts and results. See [[Storage/S3]].

### Sandboxing
Isolation technique preventing code from affecting the host system. Implemented through [[Container Isolation]] and [[gVisor]].

### Security Groups
[[AWS]] firewall rules controlling network access. Part of [[Network Isolation]].

### Service Discovery
Mechanism for services to find and communicate with each other dynamically.

### SQS (Simple Queue Service)
[[AWS]] managed message queue service. Alternative to [[Redis]] for production.

### Storage Service
Microservice handling file persistence and retrieval. See [[Architecture/Storage]].

## T

### Terraform
[[Infrastructure as Code]] tool for managing cloud resources. Being replaced by [[OpenTofu]].

### Threat Model
Security analysis identifying potential risks and mitigations. See [[Security/Threat Model]].

### TypeScript
Typed superset of JavaScript used for frontend development. Ensures [[Type Safety]].

### Type Safety
Practice of using static typing to catch errors at compile time. Applied in both [[TypeScript]] and [[Python]].

## V

### VPC (Virtual Private Cloud)
[[AWS]] network isolation for resources. Part of [[Network Isolation]] strategy.

## W

### WebSocket
Protocol for real-time bidirectional communication. Used for real-time updates in [[Monitoring Service]].

## Z

### Zero Trust
Security principle assuming no implicit trust. Every request must be verified. See [[Security/Zero Trust]].