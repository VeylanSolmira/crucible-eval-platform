# The SSL Certificate Debugging Journey: A Tale of Infrastructure, Persistence, and Hidden State

## The Beginning: A Simple HSTS Error

It started innocuously enough. A browser error message:

```
Did Not Connect: Potential Security Issue
Firefox detected a potential security threat and did not continue to green.crucible.veylan.dev 
because this website requires a secure connection.
```

What seemed like a simple SSL certificate issue would turn into a deep exploration of infrastructure-as-code principles, the boundaries between application and infrastructure concerns, and the subtle ways that state can hide in our systems.

## Chapter 1: The Initial Diagnosis

The symptoms were clear:
- HTTPS wasn't working for `green.crucible.veylan.dev`
- The browser showed an HSTS (HTTP Strict Transport Security) error
- This suggested the domain had previously worked with HTTPS but now couldn't establish a secure connection

The initial assumption was straightforward: nginx wasn't serving SSL properly. But as we'd soon discover, the rabbit hole went much deeper.

## Chapter 2: The Architecture Revelation

Our investigation revealed a carefully designed architecture:

### The Original Design
```
┌─────────────────────────┐
│   EC2 Host (Ubuntu)     │
│                         │
│  ┌─────────────────┐    │
│  │ /etc/nginx/ssl/ │    │
│  │  - cert.pem     │    │
│  │  - key.pem      │    │
│  └─────────────────┘    │
│           │              │
│      Bind Mount         │
│           ↓              │
│  ┌─────────────────┐    │
│  │ Nginx Container │    │
│  │                 │    │
│  └─────────────────┘    │
└─────────────────────────┘
```

The design philosophy was clear: **SSL certificates are infrastructure, not application concerns**. The host would manage certificates, and containers would simply consume them.

## Chapter 3: The First Red Herring

The nginx container logs revealed:
```
WARNING: Production mode but no SSM certificates available
Using existing SSL certificates
chmod: /etc/nginx/ssl/cert.pem: Read-only file system
```

This led us down the first wrong path. The container was trying to modify permissions on read-only mounted certificates. We spent time refactoring the nginx entrypoint script to only set permissions when creating certificates, not when reading them.

### Engineering Principle: Separation of Concerns
This reinforced an important principle: containers should not modify infrastructure-provided resources. The nginx container's job is to serve traffic, not manage certificates.

## Chapter 4: The Docker Volume Revelation

The real issue emerged when we discovered that docker-compose was using a Docker-managed volume for SSL certificates, not a bind mount from the host:

```yaml
# What we had (wrong)
volumes:
  - ssl-certs:/etc/nginx/ssl  # Docker volume

# What we needed (correct)
volumes:
  - /etc/nginx/ssl:/etc/nginx/ssl:ro  # Bind mount from host
```

This explained everything. The host was writing certificates to `/etc/nginx/ssl/`, but the container was looking in a completely different Docker volume.

### The Psychological Moment
This is where frustration peaks. The architecture is sound, the code is correct, but a single configuration line breaks everything. It's a reminder that in distributed systems, the devil is often in the configuration details.

## Chapter 5: Environment-Specific Configurations

We then faced a design decision: how should SSL mounts differ between development and production?

```yaml
# docker-compose.yml (base) - No SSL mount specified

# docker-compose.dev.yml
nginx:
  volumes:
    - ssl-certs:/etc/nginx/ssl  # Docker volume for self-signed certs

# docker-compose.prod.yml  
nginx:
  volumes:
    - /etc/nginx/ssl:/etc/nginx/ssl:ro  # Bind mount from host
```

This pattern elegantly solved multiple problems:
- Development can generate self-signed certificates
- Production uses infrastructure-managed certificates
- The base configuration makes no assumptions

### Engineering Principle: Configuration as Documentation
The environment-specific compose files document the architectural decision: development owns its certificates, production receives them from infrastructure.

## Chapter 6: The Wildcard Certificate Mystery

Even after fixing the mount, HTTPS still didn't work. The certificate investigation revealed:

```
Subject: CN = crucible.veylan.dev
DNS: crucible.veylan.dev, www.crucible.veylan.dev
```

But we were accessing `green.crucible.veylan.dev`! The certificate didn't cover subdomains.

### The Infrastructure State Problem
Checking AWS SSM Parameter Store revealed the correct wildcard certificate existed:
```
Subject: CN=*.crucible.veylan.dev
DNS:*.crucible.veylan.dev, DNS:crucible.veylan.dev
```

But the EC2 instance had an older, non-wildcard certificate. This revealed a fundamental challenge: **certificate rotation in production systems**.

## Chapter 7: The Systemd Solution

We designed an elegant solution using systemd timers:

```bash
# Systemd timer runs hourly
OnActiveSec=0        # Run immediately on start
OnUnitActiveSec=1h   # Then every hour

# Refresh script:
1. Fetch from AWS SSM
2. Compare with existing
3. Update only if changed
4. Reload nginx gracefully
```

### Engineering Principles Applied:
1. **Idempotency**: Only update when certificates actually change
2. **Graceful Updates**: Reload nginx without dropping connections
3. **Observability**: Log all operations for debugging
4. **Fail-Safe**: Continue using existing certs if update fails

## Chapter 8: The Kubernetes Future

This entire journey illuminated how certificate management would work in Kubernetes:

### Docker Compose Approach (Current)
- Host fetches certificates
- Bind mounts to containers
- Systemd manages refresh

### Kubernetes Approach (Future)
- Cert-Manager automates certificate lifecycle
- Certificates stored as Kubernetes Secrets
- Ingress controller handles SSL termination

The principle remains the same: **infrastructure manages certificates, applications consume them**.

## Chapter 9: The Hidden State Revelation

The final twist came when Terraform wouldn't update the instance. Despite changed userdata, no replacement was triggered. The investigation revealed:

```
user_data_replace_on_change = false
```

This single line of configuration, likely set months ago for testing, prevented all our infrastructure updates from taking effect.

### The Psychological Challenge
This is perhaps the most frustrating type of bug:
- The code is correct
- The new infrastructure is properly designed
- But hidden state prevents the changes from applying

It's a reminder that in infrastructure-as-code, state management is as important as the code itself.

## Chapter 10: Lessons Learned

### Technical Lessons
1. **Explicit is better than implicit**: Always specify critical behaviors like `user_data_replace_on_change`
2. **State can hide anywhere**: Terraform state, instance metadata, even browser HSTS caches
3. **Configuration is code**: A single line in docker-compose.yml can break an entire architecture
4. **Separation of concerns scales**: Clear boundaries between infrastructure and application pay dividends

### Psychological Lessons
1. **Frustration is a signal**: When you're "SO CLOSE," hidden state is often the culprit
2. **Question assumptions**: "It should work" means checking what "it" actually is
3. **Small details matter**: Read-only mounts, volume types, boolean flags - details matter
4. **Persistence pays**: Complex bugs often have simple causes, but finding them takes patience

### Architectural Lessons
1. **Design for observability**: Logs at every decision point saved debugging time
2. **Make invalid states impossible**: Read-only mounts prevent containers from doing the wrong thing
3. **Environment parity has limits**: Dev and prod can differ, but document why
4. **Automate the toil**: Manual certificate updates → systemd timers → Kubernetes operators

## Chapter 11: The Broader Implications

This debugging journey revealed several broader themes:

### The Evolution of Infrastructure
From manual server management to infrastructure-as-code to Kubernetes operators, we see a progression toward declarative, self-healing systems. Each step reduces operational burden but increases conceptual complexity.

### The Challenge of Distributed State
In modern systems, state exists at multiple levels:
- Cloud provider (AWS SSM)
- Infrastructure tooling (Terraform state)
- Operating system (systemd timers)
- Container runtime (Docker volumes)
- Application (nginx configuration)

Debugging requires understanding all these layers and their interactions.

### The Value of Principled Design
Throughout this journey, returning to first principles guided solutions:
- Is this an infrastructure or application concern?
- Should this be mutable or immutable?
- Where should this state live?
- How do we make this observable?

## Epilogue: The Success

After identifying and fixing each issue:
- Docker volumes → bind mounts
- localhost certificates → wildcard certificates  
- Missing automation → systemd timers
- Hidden state → explicit configuration

The system now works beautifully. HTTPS is served correctly, certificates refresh automatically, and the architecture is prepared for its Kubernetes future.

But more importantly, we've documented not just the solution, but the journey. Future engineers (or future us) will understand not just what we built, but why we built it this way.

## The Human Element

Perhaps the most important lesson is about the human element in engineering. The moments of frustration ("we are SO CLOSE"), the satisfaction of understanding ("that's why Terraform isn't detecting changes!"), and the importance of clear communication ("no, no, no" about command formatting) are all part of the engineering experience.

Great systems are built not just with great code, but with patience, persistence, and the ability to step back and see the bigger picture when the details become overwhelming.

In the end, this wasn't just about fixing SSL certificates. It was about understanding systems, managing complexity, and the very human journey of debugging in a world of distributed state and hidden assumptions.