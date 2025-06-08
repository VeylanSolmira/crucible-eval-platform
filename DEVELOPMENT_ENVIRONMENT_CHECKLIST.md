# Development Environment Checklist for METR Eval Platform

## Prerequisites

### Core Development Tools
- [x] **Python 3.13+** installed
  ```bash
  python --version  # Should show 3.11 or higher
  ```
- [x] **Node.js 18+** and npm/yarn for TypeScript frontend
  ```bash
  node --version  # Should show v18 or higher
  npm --version
  ```
- [x] **Git** configured with your credentials
  ```bash
  git config --global user.name
  git config --global user.email
  ```

### Container & Orchestration Tools
- [ ] **Docker Desktop** installed and running
  - [ ] Allocated at least 4GB RAM in Docker settings
  - [x] Verify with: `docker run hello-world`
- [ ] **kubectl** installed
  ```bash
  kubectl version --client
  ```
- [ ] **Local Kubernetes** (choose one):
  - [ ] minikube: `minikube start`
  - [ ] kind: `kind create cluster`
  - [ ] Docker Desktop Kubernetes enabled
- [ ] **Helm** (for K8s package management)
  ```bash
  helm version
  ```

## Project Setup

### Backend (Python/FastAPI)
- [ ] Create and activate virtual environment
  ```bash
  python -m venv venv
  source venv/bin/activate  # On Windows: venv\Scripts\activate
  ```
- [ ] Install Python dependencies
  ```bash
  pip install -r requirements.txt
  pip install -r requirements-dev.txt
  ```
- [ ] Set up pre-commit hooks
  ```bash
  pre-commit install
  ```

### Frontend (TypeScript/React)
- [ ] Install frontend dependencies
  ```bash
  cd frontend
  npm install  # or yarn install
  cd ..
  ```

### Database
- [ ] PostgreSQL running (choose one):
  - [ ] Local PostgreSQL installation
  - [ ] Docker container: `docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=password postgres:15`
- [ ] Redis running (for caching/queues):
  ```bash
  docker run -d -p 6379:6379 redis:7-alpine
  ```

## Configuration

### Environment Variables
- [ ] Copy `.env.example` to `.env`
- [ ] Configure required variables:
  ```bash
  DATABASE_URL=postgresql://user:password@localhost:5432/metr_eval
  REDIS_URL=redis://localhost:6379
  SECRET_KEY=<generate-a-secret-key>
  ```

### AWS Configuration (if applicable)
- [ ] AWS CLI installed
- [ ] AWS credentials configured:
  ```bash
  aws configure
  aws sts get-caller-identity  # Verify access
  ```

## Verification Steps

### 1. Linting & Type Checking
- [ ] Python linting passes
  ```bash
  ruff check .
  mypy src/
  ```
- [ ] Frontend linting passes
  ```bash
  cd frontend && npm run lint
  ```

### 2. Unit Tests
- [ ] Backend tests pass
  ```bash
  pytest tests/unit -v
  ```
- [ ] Frontend tests pass
  ```bash
  cd frontend && npm test
  ```

### 3. Local Services
- [ ] Start all services with docker-compose
  ```bash
  docker-compose up -d
  ```
- [ ] Verify services are running
  ```bash
  docker-compose ps  # All should be "Up"
  ```
- [ ] API accessible at http://localhost:8000
- [ ] Frontend accessible at http://localhost:3000
- [ ] Database migrations applied
  ```bash
  alembic upgrade head
  ```

### 4. Kubernetes Local Testing
- [ ] Deploy to local cluster
  ```bash
  kubectl apply -f k8s/local/
  ```
- [ ] Verify pods are running
  ```bash
  kubectl get pods
  ```

## IDE Setup

### VS Code Extensions (Recommended)
- [ ] Python
- [ ] Pylance
- [ ] Docker
- [ ] Kubernetes
- [ ] ESLint
- [ ] Prettier
- [ ] GitLens

### IDE Configuration
- [ ] Python interpreter set to virtual environment
- [ ] Linting enabled for Python and TypeScript
- [ ] Format on save configured

## Troubleshooting

### Common Issues
1. **Port conflicts**: Check if ports 3000, 5432, 6379, 8000 are available
2. **Docker resources**: Increase Docker Desktop memory if builds fail
3. **Python version**: Use pyenv to manage multiple Python versions
4. **Node version**: Use nvm to manage Node.js versions

### Useful Commands
```bash
# Clean Docker resources
docker system prune -a

# Reset local Kubernetes
minikube delete && minikube start

# Check what's using a port (macOS/Linux)
lsof -i :8000

# Rebuild from scratch
docker-compose down -v
docker-compose build --no-cache
docker-compose up
```

## Next Steps
Once everything is checked:
1. Run a full integration test: `pytest tests/integration`
2. Try submitting a test evaluation through the API
3. Monitor the evaluation in the frontend dashboard
4. Check logs: `docker-compose logs -f`