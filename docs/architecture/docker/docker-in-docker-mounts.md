# Docker-in-Docker Mount Path Translation

## How Common Is This Issue?

This Docker-in-Docker (DinD) mount path issue is **extremely common** and well-documented across the industry:

### Where You'll Encounter This

1. **CI/CD Systems**
   - Jenkins Docker agents
   - GitLab CI Docker executors
   - GitHub Actions Docker containers
   - CircleCI Docker executors

2. **Development Tools**
   - Testcontainers for integration testing
   - Docker-based development environments
   - VS Code Dev Containers

3. **Container Orchestration**
   - Docker Swarm mode
   - Local Kubernetes development (kind, minikube)
   - Container-based testing frameworks

### Industry Solutions

- **Path Translation** - What we implemented, used by Jenkins and others
- **Docker Volumes** - Kubernetes approach, avoids bind mounts entirely
- **Privileged Mode** - GitLab Runner's DinD approach (security trade-off)
- **Socket Mounting** - Docker-out-of-Docker, technically what we're doing
- **Remote Docker** - Separate Docker daemon (Docker Context)

### Official Recognition

- Docker's official documentation warns about this
- It's why Kubernetes doesn't support Docker-in-Docker
- Major CI/CD platforms have built-in workarounds
- It's a FAQ in Docker forums and Stack Overflow

## The Problem

When running Docker inside a Docker container (Docker-in-Docker or DinD), we encounter a path translation issue that prevents volume mounts from working correctly.

### The Three-Layer Challenge

1. **Host Machine** (e.g., macOS): 
   - Project location: `/Users/infinitespire/ai_dev/applications/metr-eval-platform/`
   - Docker daemon runs here

2. **Container 1** (crucible-platform): 
   - Storage mounted at: `/app/storage/` (from host's `./storage`)
   - Creates temp files at: `/app/storage/tmp/file.py`

3. **Container 2** (Python executor): 
   - Needs to mount the temp file from Container 1
   - But Docker daemon only knows host paths!

### Why It Fails

When Container 1 executes:
```bash
docker run -v /app/storage/tmp/file.py:/code.py python:3.11
```

The Docker daemon (on host) looks for `/app/storage/tmp/file.py` on the HOST filesystem, not inside Container 1. This path doesn't exist on the host, causing:
```
docker: Error response from daemon: Mounts denied: 
The path /app/storage/tmp/file.py is not shared from the host
```

## The Solution: Path Translation

We translate container paths back to host paths before mounting:

```python
# Container path: /app/storage/tmp/file.py
# Host path:     $PWD/storage/tmp/file.py

if temp_file.startswith('/app/storage/'):
    relative_path = temp_file.replace('/app/storage/', '')
    mount_path = os.path.join(host_pwd, 'storage', relative_path)
```

### Visual Representation

#### Simplified View
```
HOST FILESYSTEM                          CONTAINER 1                    CONTAINER 2
├── /Users/.../metr-eval-platform/      ├── /app/                     ├── /
│   └── storage/                        │   └── storage/              │   └── code.py
│       └── tmp/                        │       └── tmp/              │
│           └── file.py                 │           └── file.py       │

Volume Mount Flow:
1. docker-compose: ./storage → /app/storage ✅
2. Container creates: /app/storage/tmp/file.py ✅
3. Container mounts: -v /app/storage/tmp/file.py:/code.py ❌ (host doesn't know this path)
4. With translation: -v $PWD/storage/tmp/file.py:/code.py ✅ (host knows this path)
```

#### Detailed View

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                   HOST MACHINE (macOS)                              │
│                                                                                     │
│  /Users/infinitespire/ai_dev/applications/metr-eval-platform/                     │
│  ├── docker-compose.yml                                                            │
│  ├── app.py                                                                        │
│  └── storage/                                                                      │
│      └── tmp/                                                                      │
│          └── tempfile.py  ←────────────────────────────────────┐                  │
│                                                                 │                  │
│  Docker Daemon runs here ←──────────────┐                      │                  │
└─────────────────────────────────────────┼──────────────────────┼──────────────────┘
                                          │                      │
                                          │ Docker API           │ Bind Mount
                                          │                      │
┌─────────────────────────────────────────┼──────────────────────┼──────────────────┐
│                              CONTAINER 1 │ (crucible-platform)  │                  │
│                                          ↓                      ↓                  │
│  /app/                          docker run -v /app/storage/tmp/tempfile.py        │
│  ├── app.py                              ↑                                        │
│  └── storage/ ←──[mounted from ./storage]┘                                        │
│      └── tmp/                                                                      │
│          └── tempfile.py                                                           │
│                    ↑                                                               │
│                    │ Creates temp file here                                        │
│                    │                                                               │
│  Python code: ─────┘                                                               │
│  with tempfile.NamedTemporaryFile(dir='/app/storage/tmp') as f:                  │
│      docker run -v {f.name}:/code.py ...                                          │
│                    └─── This is /app/storage/tmp/tempfile.py                      │
│                                                                                    │
└────────────────────────────────────────────────────────────────────────────────────┘

❌ PROBLEM: Docker daemon tries to find /app/storage/tmp/tempfile.py on HOST
           But this path only exists inside Container 1!

✅ SOLUTION: Translate the path before calling docker run:

┌────────────────────────────────────────────────────────────────────────────────────┐
│                              PATH TRANSLATION LOGIC                                │
│                                                                                    │
│  Container Path:  /app/storage/tmp/tempfile.py                                    │
│                   ↓                                                                │
│  1. Detect:       Starts with /app/storage/ ✓                                     │
│  2. Extract:      relative = "tmp/tempfile.py"                                    │
│  3. Rebuild:      host_path = $PWD + "/storage/" + relative                       │
│                   ↓                                                                │
│  Host Path:       /Users/.../metr-eval-platform/storage/tmp/tempfile.py          │
│                                                                                    │
│  Docker Command:  docker run -v {host_path}:/code.py python:3.11                 │
└────────────────────────────────────────────────────────────────────────────────────┘

                                          │
                                          │ Docker creates Container 2
                                          ↓
┌────────────────────────────────────────────────────────────────────────────────────┐
│                              CONTAINER 2 (python:3.11)                             │
│                                                                                    │
│  /                                                                                 │
│  └── code.py ←──[mounted from host's storage/tmp/tempfile.py]                    │
│                                                                                    │
│  Executes: python /code.py                                                        │
└────────────────────────────────────────────────────────────────────────────────────┘
```

## Implementation Details

### 1. Pass Host Working Directory
```yaml
# docker-compose.yml
environment:
  - HOST_PWD=${PWD}  # Pass host working directory
```

### 2. Translate Paths in Docker Engine
```python
def _build_docker_command(self, temp_file: str) -> list:
    mount_path = temp_file
    
    # Detect container environment
    if temp_file.startswith('/app/storage/') and os.environ.get('STORAGE_BASE') == '/app/storage':
        host_pwd = os.environ.get('HOST_PWD', os.getcwd())
        relative_path = temp_file.replace('/app/storage/', '')
        mount_path = os.path.join(host_pwd, 'storage', relative_path)
```

## Alternative Solutions

### 1. Docker Volumes (Instead of Bind Mounts)
```bash
# Create a named volume
docker volume create crucible-temp

# Mount in both containers
docker run -v crucible-temp:/tmp ...
```
**Pros**: No path translation needed  
**Cons**: Harder to debug, files not easily accessible

### 2. Docker Socket Proxy
Use a proxy that intercepts Docker API calls and translates paths automatically.
**Pros**: Transparent to application  
**Cons**: Additional complexity, security considerations

### 3. Separate Execution Service
Run execution in a dedicated service that manages its own storage.
**Pros**: Clean separation, no DinD issues  
**Cons**: More complex architecture

### 4. Kubernetes Jobs
Use Kubernetes which handles these abstractions better.
**Pros**: Production-ready, handles storage properly  
**Cons**: Heavier infrastructure requirement

## Current Status

For our MVP/demo, we're using the path translation approach because:
1. **Simple**: Just a few lines of code
2. **Transparent**: Easy to understand and debug
3. **No new dependencies**: Works with existing Docker setup
4. **Temporary**: Can migrate to better solution later

## Security Considerations

- Ensure HOST_PWD is properly sanitized
- Only translate paths within expected directories
- Consider using read-only mounts where possible
- Be aware of potential path traversal attacks

## Future Improvements

When moving to production, consider:
1. Kubernetes for proper orchestration
2. Dedicated execution nodes
3. Shared storage solutions (NFS, S3, etc.)
4. Avoiding Docker-in-Docker entirely