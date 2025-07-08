Virtual environments
  (venv) inside containers are actually debated in the
  Docker community. Let me explain the trade-offs:

  Virtual Environments in Docker - Pros and Cons

  Why venv might NOT be needed in containers:

  1. Containers already provide isolation - The
  container itself is isolated
  2. Single purpose - Each container typically runs one
  application
  3. Added complexity - Extra activation steps and PATH
  management
  4. Slightly larger - venv adds some overhead
  (~10-20MB)

  Why venv CAN still be useful:

  1. Multi-stage builds - Easy to copy just the venv
  between stages
  2. Cleaner separation - System Python vs app Python
  3. Consistent with local development - Same structure
  everywhere
  4. Easier dependency management - All deps in one
  directory

  The Real Benefit for Multi-Stage:

  # Without venv - harder to identify what to copy
  FROM python:3.11-slim as builder
  RUN pip install --user package1 package2
  # Files scattered in ~/.local, /usr/local, etc

  # With venv - clean copy
  FROM python:3.11-slim as builder
  RUN python -m venv /opt/venv
  RUN /opt/venv/bin/pip install package1 package2
  # Everything in /opt/venv, easy to COPY --from=builder

  Better Approach for Our Use Case

  Since we're already using a shared base image
  strategy, let's skip venv and optimize differently: