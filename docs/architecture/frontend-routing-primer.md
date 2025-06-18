# Frontend Routing & Container Networking Primer

## Overview
When you have a React frontend and Python backend in separate containers, routing becomes important to understand. Here's how it all works.

## The Two Types of Routes

### 1. Frontend Routes (Handled by Next.js)
These are routes that serve your React application:
- `/` - Homepage
- `/about` - About page  
- `/dashboard` - Dashboard page
- `/assets/*` - Static files (CSS, JS, images)

**How it works**: 
- User visits `http://localhost:3000/`
- nginx (or Next.js server) serves the React app
- React takes over and handles client-side routing

### 2. API Routes (Handled by Python Backend)
These are data endpoints your React app calls:
- `/api/eval` - Submit evaluation
- `/api/status` - Get platform status
- `/api/queue-status` - Get queue info

**How it works**:
- React app makes request to `/api/eval`
- This gets proxied to the Python backend
- Python processes and returns JSON

## Container Networking Explained

### Local Development
```
Your Browser
    |
    ├── http://localhost:3000 ──→ Next.js Dev Server (frontend container)
    |                                    |
    |                                    ├── / → React pages
    |                                    ├── /api/* → Proxy to backend
    |                                    |
    └── http://localhost:8080 ──→ Python API (backend container)
```

### Production with Docker Compose
```
Your Browser
    |
    └── http://localhost:3000 ──→ nginx (frontend container)
                                         |
                                         ├── / → Static React files
                                         ├── /api/* → Proxy to backend
                                         |
                    ┌────────────────────┘
                    ↓
            crucible-platform:8080 (backend container)
```

## How Docker Compose Networks Work

When you run `docker-compose up`, Docker creates a network where containers can talk to each other by name:

```yaml
services:
  crucible-platform:      # This becomes the hostname
    ports:
      - "8080:8080"       # External:Internal port

  crucible-frontend:
    environment:
      - API_URL=http://crucible-platform:8080  # Container-to-container
```

Inside the network:
- Frontend can reach backend at `http://crucible-platform:8080`
- Backend can reach frontend at `http://crucible-frontend:3000`
- Containers use service names as hostnames

From outside (your browser):
- Frontend is at `http://localhost:3000`
- Backend is at `http://localhost:8080`

## The Proxy Magic

In `next.config.js`:
```javascript
async rewrites() {
  return [
    {
      source: '/api/:path*',           // When user visits /api/anything
      destination: 'http://crucible-platform:8080/api/:path*'  // Forward to backend
    },
  ]
}
```

This means:
1. User visits `http://localhost:3000/api/eval`
2. Next.js sees it matches `/api/*`
3. Proxies request to `http://crucible-platform:8080/api/eval`
4. Returns response to user

## Why This Architecture?

### Separation of Concerns
- Frontend handles UI/UX
- Backend handles business logic
- Each can scale independently

### Security
- Backend never exposed directly to internet
- Frontend can add security headers
- API authentication happens at backend

### Development
- Frontend devs can work without Python
- Backend devs can work without React
- Hot reload works for both

## Common Patterns

### 1. API Calls from React
```typescript
// This goes to /api/eval, which proxies to backend
const response = await fetch('/api/eval', {
  method: 'POST',
  body: JSON.stringify({ code })
})
```

### 2. Environment-Specific URLs
```typescript
// Development: http://localhost:8080
// Production: http://crucible-platform:8080
const apiUrl = process.env.API_URL || 'http://localhost:8080'
```

### 3. CORS (Cross-Origin Resource Sharing)
Not needed with proxy! The browser thinks all requests go to same origin (localhost:3000).

## Debugging Tips

1. **Check container names**: `docker ps`
2. **Test internal networking**: `docker exec crucible-frontend ping crucible-platform`
3. **View proxy logs**: Check Next.js console output
4. **Inspect network**: `docker network ls` and `docker network inspect <network>`

## Real-World Production

In production, you'd typically have:
```
Internet
    |
    └── Load Balancer (AWS ALB)
            |
            ├── /api/* → Backend Service (ECS/K8s)
            └── /* → Frontend Service (CloudFront/nginx)
```

But our Docker Compose setup mimics this locally!