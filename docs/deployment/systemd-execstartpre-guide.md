# SystemD ExecStartPre: When to Use Pre-Checks

## What is ExecStartPre?

`ExecStartPre` runs commands before starting your main service. If any command fails (non-zero exit code), the service won't start.

```ini
[Service]
ExecStartPre=/bin/command1
ExecStartPre=/bin/command2
ExecStart=/usr/bin/myapp
```

Commands run in order. All must succeed for the service to start.

## When ExecStartPre IS Valuable

### 1. Database Migrations
```ini
# Ensure database schema is current before starting app
ExecStartPre=/app/venv/bin/python manage.py migrate --no-input
ExecStart=/app/venv/bin/python app.py
```
**Why it's good**: Prevents version mismatches between code and database

### 2. Directory & Permission Setup
```ini
# Create required directories with correct ownership
ExecStartPre=/bin/mkdir -p /var/log/myapp /var/run/myapp
ExecStartPre=/bin/chown -R appuser:appuser /var/log/myapp /var/run/myapp
ExecStart=/usr/bin/myapp
```
**Why it's good**: Ensures runtime environment is ready

### 3. Configuration Validation
```ini
# Validate config before starting
ExecStartPre=/app/bin/validate-config /etc/myapp/config.yml
ExecStartPre=/app/bin/check-secrets
ExecStart=/app/bin/server
```
**Why it's good**: Catches config errors early with clear messages

### 4. Certificate Management
```ini
# Check if certificates are valid and not expiring soon
ExecStartPre=/bin/sh -c 'openssl x509 -checkend 86400 -in /etc/ssl/cert.pem'
ExecStartPre=/app/bin/refresh-certs-if-needed
ExecStart=/app/bin/https-server
```
**Why it's good**: Prevents service from starting with expired certs

### 5. Dependency Waiting
```ini
# Wait for database to be ready
ExecStartPre=/bin/sh -c 'until nc -z localhost 5432; do echo "Waiting for PostgreSQL..."; sleep 1; done'
ExecStart=/usr/bin/webapp
```
**Why it's good**: Handles service start order dependencies

### 6. Resource Preparation
```ini
# Download required files
ExecStartPre=/usr/bin/aws s3 sync s3://bucket/configs /etc/myapp/
ExecStartPre=/app/bin/compile-assets
ExecStart=/app/bin/server
```
**Why it's good**: Ensures all resources are available

### 7. Environment Setup
```ini
# Set up Python virtual environment if missing
ExecStartPre=/bin/sh -c 'test -d /app/venv || python3 -m venv /app/venv'
ExecStartPre=/app/venv/bin/pip install -r /app/requirements.txt
ExecStart=/app/venv/bin/python app.py
```
**Why it's good**: Self-healing service that sets up its own environment

## When to AVOID ExecStartPre

### 1. Simple Version Checks
```ini
# BAD: Just checking versions
ExecStartPre=/usr/bin/docker --version
ExecStartPre=/usr/bin/python --version
```
**Why it's bad**: Doesn't fix anything, just adds failure points

### 2. Checking Optional Dependencies
```ini
# BAD: App handles missing Redis gracefully
ExecStartPre=/usr/bin/redis-cli ping
```
**Why it's bad**: Prevents start even when app would work without it

### 3. With Strict Security Settings
```ini
# BAD: Conflicts with ProtectSystem=strict
ProtectSystem=strict
ExecStartPre=/usr/bin/docker info
```
**Why it's bad**: Security settings block the pre-check

### 4. Redundant Health Checks
```ini
# BAD: App already checks database on startup
ExecStartPre=/app/bin/check-database
ExecStart=/app/bin/server --check-db-on-start
```
**Why it's bad**: Duplicates what app already does

### 5. Non-Actionable Checks
```ini
# BAD: Can't fix low memory from here
ExecStartPre=/bin/sh -c 'free -m | grep Mem | awk "{if (\$4 < 1000) exit 1}"'
```
**Why it's bad**: Fails without ability to fix the problem

## Best Practices

### ✅ DO Use ExecStartPre When:
- Setting up the environment
- Validating configuration
- Waiting for dependencies
- Performing corrective actions
- Ensuring security requirements

### ❌ DON'T Use ExecStartPre For:
- Simple existence checks
- Version verification
- Optional features
- Things the app checks anyway
- Non-fixable problems

## The Golden Rule

> **ExecStartPre should PREPARE, not just CHECK**

Good pre-checks actively fix or set up. Bad pre-checks just verify and fail.

## Common Patterns

### Pattern 1: Create and Validate
```ini
# Create directory, set permissions, validate config
ExecStartPre=/bin/mkdir -p /var/lib/myapp
ExecStartPre=/bin/chown appuser:appuser /var/lib/myapp
ExecStartPre=/app/bin/validate-config
ExecStart=/app/bin/server
```

### Pattern 2: Wait and Prepare
```ini
# Wait for dependency, then prepare environment
ExecStartPre=/bin/sh -c 'until curl -s http://configserver/ready; do sleep 1; done'
ExecStartPre=/app/bin/fetch-config
ExecStartPre=/app/bin/compile-config
ExecStart=/app/bin/server
```

### Pattern 3: Conditional Setup
```ini
# Only run expensive setup if needed
ExecStartPre=/bin/sh -c 'test -f /app/.initialized || /app/bin/first-time-setup'
ExecStart=/app/bin/server
```

## Debugging Failed Pre-Checks

```bash
# See which pre-check failed
sudo journalctl -u myservice -n 50

# Test pre-check commands manually
sudo -u serviceuser /path/to/command

# Skip pre-checks temporarily
sudo systemctl edit myservice
# Add:
[Service]
ExecStartPre=
```

## Our Crucible Platform Case

The Docker version check in our service:
```ini
ExecStartPre=/usr/bin/docker --version
```

**Why it's problematic:**
1. Doesn't prepare anything
2. App handles missing Docker gracefully
3. Conflicts with security settings
4. Adds unnecessary failure point

**Better approach:**
- Remove the check
- Let app detect and handle Docker availability
- Or check and CREATE docker networks/volumes if needed

## Conclusion

ExecStartPre is powerful when used to PREPARE the environment, not just validate it. If your pre-check doesn't actively improve the situation, it's probably not needed.